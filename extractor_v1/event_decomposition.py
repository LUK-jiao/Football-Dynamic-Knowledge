"""
Event Decomposition Module - 事件分解层

将语义块拆分为1-N个事件单元，为后续结构化抽取提供稳定的事件索引。

职责：
1. 事件拆分：一个 block 可以生成多个 event
2. 父子关系标注：主事件 vs 子事件
3. 事件语义压缩：用一句话概括"发生了什么"

禁止：
- 时间抽取或标准化
- 状态判断
- 约束生成
- 事实补全或常识推断
- 改写、裁剪、总结 block_text
"""

import time
from typing import Dict, Any, List
from extractor_v1.ollama_backend import OllamaBackend


class EventDecomposer:
    """
    事件分解器（Event Decomposition Layer）
    
    职责：
    1. 调用 ollama_backend 进行事件分解
    2. 验证输入格式
    3. 直接透传 backend 输出，不做任何修改
    """
    
    def __init__(
        self,
        model: str = "gemma3:12b",
        host: str = "http://localhost:11434"
    ):
        """
        初始化事件分解器
        
        Args:
            model: Ollama 模型名称
            host: Ollama 服务地址
        """
        self.backend = OllamaBackend(model=model, host=host)
    
    def decompose(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        将单个语义块分解为事件单元
        
        Args:
            block: 输入的语义块，必须包含：
                - chunk_id: 唯一标识（兼容 block_id）
                - text: 原始文本
                - source_name: 信息来源名称
                - source_type: 信息来源类型
                - publish_date: 发布日期
                - author: 作者（可选）
        
        Returns:
            包含事件列表的结果 dict：
            {
                "events": [
                    {
                        "event_id": "...",
                        "doc_id": "...",
                        "chunk_id": "...",
                        "event_index": 1,
                        "parent_event_id": "..." | null,
                        "is_sub_event": true | false,
                        "event_description": "...",
                        "block_text": "...",
                        "source_name": "...",
                        "source_type": "...",
                        "publish_date": "...",
                        "author": "...",
                        "inference_time": 1.234  # LLM 推理时间（秒）
                    }
                ]
            }
        
        Raises:
            ValueError: 输入格式不正确
        """
        # 验证输入
        self._validate_input(block)
        
        # 记录开始时间
        start_time = time.time()
        
        # 调用 backend（直接透传，不做任何修改）
        result = self.backend.decompose_events(block)
        
        # 记录结束时间并计算推理时间
        end_time = time.time()
        inference_time = end_time - start_time
        
        # 为每个 event 添加推理时间（平均分配）
        if "events" in result and result["events"]:
            avg_time = inference_time / len(result["events"])
            chunk_id = block.get("chunk_id") or block.get("block_id")
            doc_id = block.get("doc_id")
            for idx, event in enumerate(result["events"], start=1):
                if chunk_id:
                    event["chunk_id"] = chunk_id
                    # 系统后处理统一覆盖 event_id，避免依赖模型自由生成。
                    event["event_id"] = f"{chunk_id}:e{idx:03d}"
                if doc_id:
                    event["doc_id"] = doc_id
                event["event_index"] = idx
                if not event.get("block_text"):
                    event["block_text"] = block.get("text", "")
                if not event.get("source_name"):
                    event["source_name"] = block.get("source_name") or block.get("source", "")
                if not event.get("source_type"):
                    event["source_type"] = block.get("source_type", "UNKNOWN")
                if not event.get("publish_date"):
                    event["publish_date"] = block.get("publish_date", "")
                if event.get("author") is None:
                    event["author"] = block.get("author", "")
                event["inference_time"] = round(avg_time, 3)
        
        return result
    
    def decompose_batch(
        self,
        blocks: List[Dict[str, Any]],
        max_workers: int = 3
    ) -> List[Dict[str, Any]]:
        """
        批量分解多个语义块
        
        Args:
            blocks: 语义块列表
            max_workers: 并发线程数
        
        Returns:
            事件列表的列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_block = {
                executor.submit(self.decompose, block): block 
                for block in blocks
            }
            
            # 收集结果（按完成顺序）
            for future in as_completed(future_to_block):
                block = future_to_block[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"✗ Block {block.get('block_id')} decomposition failed: {e}")
                    # 失败时返回空事件列表
                    results.append({
                        "events": [],
                        "error": str(e),
                        "block_id": block.get("block_id")
                    })
        
        return results
    
    def _validate_input(self, block: Dict[str, Any]):
        """验证输入 block 的格式"""
        required_fields = ["text", "publish_date"]
        
        for field in required_fields:
            if field not in block:
                raise ValueError(
                    f"Block 缺少必填字段: {field}. "
                    f"当前字段: {list(block.keys())}"
                )

        if "chunk_id" not in block and "block_id" not in block:
            raise ValueError(
                f"Block 缺少必填字段: chunk_id(兼容 block_id). 当前字段: {list(block.keys())}"
            )

        if "source_name" not in block and "source" not in block:
            raise ValueError(
                f"Block 缺少必填字段: source_name. 当前字段: {list(block.keys())}"
            )
        
        if not isinstance(block["text"], str) or not block["text"].strip():
            raise ValueError("Block text 必须是非空字符串")


# ============================================================================
# 便捷函数
# ============================================================================

def decompose_block(
    block: Dict[str, Any],
    model: str = "gemma3:12b",
    host: str = "http://localhost:11434"
) -> Dict[str, Any]:
    """
    将单个语义块分解为事件单元（便捷函数）
    
    Args:
        block: 输入的语义块
        model: Ollama 模型名称
        host: Ollama 服务地址
        
    Returns:
        包含事件列表的结果 dict
    """
    decomposer = EventDecomposer(model=model, host=host)
    return decomposer.decompose(block)
