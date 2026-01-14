"""
事件候选提取器

基于 spaCy 依存句法分析提取事件候选。

架构原则：
- 高召回、结构受控的事件候选生成
- 不使用正则、不使用动词白名单
- 事件边界基于句法结构（dependency subtree）
- 在生成阶段就完成去重，不允许生成后再做去噪
"""

import spacy
from typing import List, Dict, Any


class EventCandidateExtractor:
    """事件候选提取器"""
    
    def __init__(self):
        """初始化提取器，加载 spaCy 模型"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy 英文模型未安装。请运行: python -m spacy download en_core_web_sm"
            )
    
    def extract_event_candidates(self, text: str) -> List[Dict[str, Any]]:
        """
        提取事件候选（基于 spaCy 依存句法分析）
        
        Trigger 选择规则（三类）：
        1. 动词事件：token.pos_ == VERB AND token.dep_ NOT IN {"aux", "auxpass"}
        2. 形容词事件：token.pos_ == ADJ AND (存在 xcomp 或 prep 子节点)
        3. 名词事件：token.pos_ == NOUN AND (存在 prep 或 of-结构)
        
        Span 构建方式：
        - 使用 trigger token 的 dependency subtree（最小闭包）
        - span 起点 = subtree 中最小 token.idx
        - span 终点 = subtree 中最大 token.idx + len(token)
        - span_text 直接来自原始文本切片
        
        重复控制（生成期内完成）：
        - 若两个事件的 span 完全相同，仅保留一个
        - 若一个事件的 span 完全包含于另一个，保留依存树深度更大的
        
        Args:
            text: 输入文本
        
        Returns:
            [{
                "event_id": "E1",
                "trigger": "...",
                "span_text": "...",
                "span": (start, end)
            }, ...]
        """
        # 使用 spaCy 解析文本
        doc = self.nlp(text)
        
        events = []
        event_id_counter = 1
        seen_events = {}  # {span: (trigger, depth, event_dict)}
        
        # 辅助函数：计算 token 在依存树中的深度
        def _get_depth(token):
            """计算 token 在依存树中的深度（root=0）"""
            depth = 0
            current = token
            while current.head != current:
                depth += 1
                current = current.head
            return depth
        
        # 辅助函数：从 subtree 提取 span
        def _get_span_from_subtree(token):
            """从 token 的 subtree 提取 span"""
            subtree_tokens = list(token.subtree)
            if not subtree_tokens:
                return None
            
            # 特殊处理：对于 xcomp 关系的动词，排除 "to" 标记
            if token.dep_ == "xcomp" and token.pos_ == "VERB":
                subtree_tokens = [t for t in subtree_tokens if not (t.dep_ == "aux" and t.text.lower() == "to")]
            
            if not subtree_tokens:
                return None
            
            # 计算 span 起点和终点
            start_idx = min(t.idx for t in subtree_tokens)
            end_idx = max(t.idx + len(t.text) for t in subtree_tokens)
            
            # 从原始文本提取 span_text
            span_text = text[start_idx:end_idx].strip()
            span = (start_idx, end_idx)
            
            return span, span_text
        
        # 辅助函数：检查是否有特定依存关系的子节点
        def _has_child_with_dep(token, dep_labels):
            """检查 token 是否有指定依存标签的子节点"""
            for child in token.children:
                if child.dep_ in dep_labels:
                    return True
            return False
        
        # 辅助函数：检查是否有 prep 子节点，且 prep 为 "of"
        def _has_of_prep(token):
            """检查是否有 of-结构"""
            for child in token.children:
                if child.dep_ == "prep" and child.text.lower() == "of":
                    return True
            return False
        
        # 遍历所有 token，识别 trigger
        for token in doc:
            trigger_text = token.text
            trigger_valid = False
            trigger_type = None
            
            # 规则1: 动词事件（主要来源）
            if token.pos_ == "VERB" and token.dep_ not in {"aux", "auxpass"}:
                trigger_valid = True
                trigger_type = "VERB"
            
            # 规则2: 形容词事件（受限）
            elif token.pos_ == "ADJ":
                # 检查是否有 xcomp 或 prep 子节点
                has_xcomp = _has_child_with_dep(token, {"xcomp"})
                has_prep = _has_child_with_dep(token, {"prep"})
                
                if has_xcomp or has_prep:
                    # 特殊规则：如果 xcomp 子节点是动词，则不将形容词作为触发点
                    # （因为动词事件会单独提取，形容词只是引导作用）
                    if has_xcomp:
                        xcomp_is_verb = any(child.pos_ == "VERB" for child in token.children if child.dep_ == "xcomp")
                        if xcomp_is_verb:
                            continue  # 跳过此形容词，让动词自己作为触发点
                    
                    trigger_valid = True
                    trigger_type = "ADJ"
            
            # 规则3: 名词事件（受限）
            elif token.pos_ == "NOUN":
                if _has_child_with_dep(token, {"prep"}) or _has_of_prep(token):
                    trigger_valid = True
                    trigger_type = "NOUN"
            
            # 如果不是有效 trigger，跳过
            if not trigger_valid:
                continue
            
            # 从 subtree 提取 span
            result = _get_span_from_subtree(token)
            if not result:
                continue
            
            span, span_text = result
            
            # 去重和重叠控制
            if span in seen_events:
                # 如果 span 完全相同，保留依存树层次更高的（depth 更小，更接近 ROOT）
                existing_trigger, existing_depth, existing_event = seen_events[span]
                current_depth = _get_depth(token)
                
                if current_depth < existing_depth:
                    # 当前事件层次更高，替换
                    seen_events[span] = (trigger_text, current_depth, {
                        "event_id": existing_event["event_id"],  # 保持原 ID
                        "trigger": trigger_text,
                        "span_text": span_text,
                        "span": span
                    })
            else:
                # 检查是否被其他事件完全包含，或包含其他事件
                is_contained = False
                spans_to_remove = []
                
                for existing_span in list(seen_events.keys()):
                    # 如果当前 span 被包含在已有 span 中
                    if existing_span[0] <= span[0] and span[1] <= existing_span[1] and span != existing_span:
                        existing_trigger, existing_depth, existing_event = seen_events[existing_span]
                        current_depth = _get_depth(token)
                        
                        # 特殊规则：并列结构（conj）始终保留，不被包含关系过滤
                        if token.dep_ == "conj":
                            # 并列事件，不检查包含关系
                            break
                        
                        if current_depth < existing_depth:
                            # 当前事件层次更高，删除已有事件，添加当前事件
                            spans_to_remove.append(existing_span)
                        else:
                            # 已有事件层次更高，跳过当前事件
                            is_contained = True
                            break
                    
                    # 如果当前 span 包含已有 span
                    elif span[0] <= existing_span[0] and existing_span[1] <= span[1] and span != existing_span:
                        existing_trigger, existing_depth, existing_event = seen_events[existing_span]
                        current_depth = _get_depth(token)
                        
                        # 检查已有事件是否为并列结构
                        # 需要找到对应的 token（通过 span 位置）
                        existing_token = None
                        for t in doc:
                            t_start = min(st.idx for st in t.subtree)
                            t_end = max(st.idx + len(st.text) for st in t.subtree)
                            if (t_start, t_end) == existing_span:
                                existing_token = t
                                break
                        
                        # 如果已有事件是并列结构，保留它
                        if existing_token and existing_token.dep_ == "conj":
                            continue
                        
                        if current_depth < existing_depth:
                            # 当前事件层次更高，删除已有事件
                            spans_to_remove.append(existing_span)
                        else:
                            # 已有事件层次更高，跳过当前事件
                            is_contained = True
                            break
                
                # 删除需要移除的 spans
                for span_to_remove in spans_to_remove:
                    del seen_events[span_to_remove]
                
                if not is_contained:
                    # 添加新事件
                    event = {
                        "event_id": f"E{event_id_counter}",
                        "trigger": trigger_text,
                        "span_text": span_text,
                        "span": span
                    }
                    seen_events[span] = (trigger_text, _get_depth(token), event)
                    event_id_counter += 1
        
        # 从 seen_events 提取最终事件列表
        events = [event for _, _, event in seen_events.values()]
        
        # 按 span 起点排序
        events.sort(key=lambda e: e["span"][0])
        
        # 重新分配 event_id（保证连续）
        for i, event in enumerate(events, 1):
            event["event_id"] = f"E{i}"
        
        # 如果没有识别到事件，整个文本作为一个隐式事件
        if not events:
            events.append({
                "event_id": "E1",
                "trigger": "implicit",
                "span_text": text,
                "span": (0, len(text))
            })
        
        return events
