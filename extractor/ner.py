"""
Named Entity Recognition (NER) for football domain.
Extracts entities like players, teams, tournaments, etc.

专注于从语义分块中抽取四类锚点：
1. 事实参与者锚点（Participant Anchors）
2. 时间锚点（Temporal Anchors）
3. 来源锚点（Source Anchors）
4. 事实约束锚点（Constraint Anchors）
"""

import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import spacy

# 导入分离出的模块
from extractor.time_expression_extractor import TimeExpressionExtractor, TimeGranularity
from extractor.event_candidate_extractor import EventCandidateExtractor


class EntityType(str, Enum):
    """实体类型枚举"""
    PLAYER = "Player"
    CLUB = "Club"
    COACH = "Coach"
    TEAM = "Team"
    REFEREE = "Referee"
    STADIUM = "Stadium"
    TOURNAMENT = "Tournament"
    OTHER = "Other"


class SourceType(str, Enum): #todo 这里来源类型枚举怎么用的
    """来源类型枚举"""
    MEDIA = "Media"
    OFFICIAL = "Official"
    SOCIAL = "Social"
    OTHER = "Other"


class ConstraintType(str, Enum):
    """约束类型枚举"""
    TRANSFER_STATUS = "TRANSFER_STATUS"
    SCORE_STATUS = "SCORE_STATUS"
    CONTRACT_STATUS = "CONTRACT_STATUS"
    MATCH_STATUS = "MATCH_STATUS"
    INJURY_STATUS = "INJURY_STATUS"
    SUSPENSION_STATUS = "SUSPENSION_STATUS"


# TimeGranularity 已从 time_expression_extractor 导入


class FootballAnchorExtractor:
    """
    足球领域锚点抽取器
    
    从语义分块中提取四类锚点，用于知识图谱构建：
    - 参与者锚点：球员、球队、教练等实体
    - 时间锚点：事件日期、有效期
    - 来源锚点：信息来源及类型
    - 约束锚点：转会状态、比分、合同等约束条件
    """
    
    def __init__(self, llm_backend=None):
        """
        初始化锚点抽取器
        
        Args:
            llm_backend: 可选的LLM后端，用于智能实体识别
        """
        self.llm_backend = llm_backend
        
        # 初始化时间表达式提取器和事件候选提取器
        self.time_extractor = TimeExpressionExtractor()
        self.event_extractor = EventCandidateExtractor()
        
        # 知名足球俱乐部列表 #todo 还要加上球员和教练的名单
        self.known_clubs = { #todo 拓展一下俱乐部，起码全部英超俱乐部要有，并且还需要转换一下昵称，比如曼城->City，曼联->Utd，阿森纳->Gunners
            "Manchester United", "Bayern Munich", "Real Madrid", "Barcelona", 
            "Liverpool", "Chelsea", "Arsenal", "Manchester City", "Tottenham",
            "Paris Saint-Germain", "PSG", "Juventus", "AC Milan", "Inter Milan",
            "Borussia Dortmund", "Ajax", "Porto", "Benfica"
        }
        
        # 知名媒体来源
        self.known_media = {
            "BBC", "Sky Sports", "ESPN", "The Guardian", "The Athletic",
            "Reuters", "Associated Press", "AFP", "Goal", "Transfermarkt"
        }
        
        # 官方来源关键词
        self.official_keywords = ["official", "confirmed", "announce", "statement"]
        
        # 社交媒体关键词
        self.social_keywords = ["Twitter", "Instagram", "Facebook", "tweet"]
    
    def extract_anchors(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        从语义分块中提取所有锚点
        
        使用 Temporal Aligner 架构：
        1. 时间表达式提取（识别所有时间表达）
        2. 事件候选识别（识别所有潜在事件）
        3. 时间-事件对齐（生成时间锚点）
        
        Args:
            chunk: 语义分块，包含 block_id, text, source, publish_date
            
        Returns:
            完整的分块数据，添加了 anchors、fact_type、need_resolver 属性
        """
        text = chunk.get("text", "")
        source = chunk.get("source", "")
        publish_date = chunk.get("publish_date", "")
        
        # 提取四类锚点
        participants = self._extract_participants(text)
        constraints = self._extract_constraints(text, participants)
        sources = self._extract_sources(text, source)
        
        # 先判定 fact_type（不依赖 temporal_anchors）
        fact_type = self._determine_fact_type(text, constraints)
        
        # 使用 Temporal Aligner 提取时间锚点
        time_expressions = self.time_extractor.extract_time_expressions(text, publish_date)
        event_candidates = self.event_extractor.extract_event_candidates(text)
        temporal_anchors = self._align_temporal_anchors(
            event_candidates, time_expressions, publish_date, fact_type
        )
        
        # 判定是否需要 resolver
        need_resolver = self._determine_need_resolver(fact_type, temporal_anchors)
        
        # 构建输出
        result = {
            "block_id": chunk.get("block_id"),
            "text": text,
            "source": source,
            "publish_date": publish_date,
            "anchors": {
                "participants": participants,
                "temporal_anchors": temporal_anchors,
                "sources": sources,
                "constraints": constraints
            },
            "fact_type": fact_type,
            "need_resolver": need_resolver
        }
        
        return result
    
    def _extract_participants(self, text: str) -> List[Dict[str, str]]:
        """
        提取参与者锚点（球员、球队、教练等）
        
        Args:
            text: 输入文本
            
        Returns:
            参与者列表，格式：[{"type": "Player", "name": "De Ligt"}, ...]
        """
        participants = []
        seen = set()  # 去重
        
        # 1. 提取已知俱乐部
        for club in self.known_clubs:
            if club in text and club not in seen:
                participants.append({"type": EntityType.CLUB, "name": club})
                seen.add(club)
        
        # 2. 提取球员名（大写字母开头的专有名词，通常在动词前后）
        # 匹配模式：[Name] has/had/will/is/agreed/signed/joined...
        player_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:has|had|will|is|was|agreed|signed|joined|scored|assisted|played|left|arrived)',
            r'(?:player|striker|midfielder|defender|goalkeeper|forward)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+to\s+(?:join|sign|leave)',
            r'(?:signed|acquired|bought)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in player_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                # 过滤掉俱乐部名和常见非人名
                if (name not in self.known_clubs and 
                    name not in seen and 
                    len(name.split()) <= 3 and
                    name not in ["The", "A", "An", "This", "That"]):
                    participants.append({"type": EntityType.PLAYER, "name": name})
                    seen.add(name)
        
        # 3. 提取教练
        coach_patterns = [
            r'(?:manager|coach|boss)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:managing|coaching)',
        ]
        
        for pattern in coach_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                if name not in seen and len(name.split()) <= 3:
                    participants.append({"type": EntityType.COACH, "name": name})
                    seen.add(name)
        
        # 4. 提取球队/国家队
        team_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:national team|squad|lineup)',
            r'(?:Team|Squad)\s+([A-Z][a-z]+)',
        ]
        
        for pattern in team_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                if name not in seen:
                    participants.append({"type": EntityType.TEAM, "name": name})
                    seen.add(name)
        
        # 5. 提取赛事/锦标赛
        tournament_patterns = [
            r'\b(Premier League|Champions League|Europa League|World Cup|FA Cup|Bundesliga|La Liga|Serie A|Ligue 1)\b',
        ]
        
        for pattern in tournament_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                if name not in seen:
                    participants.append({"type": EntityType.TOURNAMENT, "name": name})
                    seen.add(name)
        
        # 6. 提取球场
        stadium_patterns = [
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Stadium|Arena|Ground|Park))\b',
        ]
        
        for pattern in stadium_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                if name not in seen:
                    participants.append({"type": EntityType.STADIUM, "name": name})
                    seen.add(name)
        
        return participants
    
    def _extract_sources(self, text: str, source: str) -> List[Dict[str, str]]:
        """
        提取来源锚点
        
        Args:
            text: 输入文本
            source: 原始来源字段
            
        Returns:
            来源列表，格式：[{"name": "BBC", "type": "Media"}, ...]
        """
        sources = []
        seen = set()
        
        # 1. 从 source 字段提取
        if source and source not in seen:
            source_type = self._classify_source(source, text)
            sources.append({"name": source, "type": source_type})
            seen.add(source)
        
        # 2. 从文本中提取引用的来源
        # 匹配 "according to [Source]", "reported by [Source]", "[Source] reports"
        citation_patterns = [
            r'(?:according to|reported by|via|per)\s+([A-Z][A-Za-z\s]+?)(?:\.|,|:|$)',
            r'([A-Z][A-Za-z\s]+?)\s+(?:reports|confirms|announces|states)',
        ]
        
        for pattern in citation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                source_name = match.group(1).strip()
                # 过滤太长的匹配和已存在的
                if len(source_name) <= 30 and source_name not in seen:
                    source_type = self._classify_source(source_name, text)
                    sources.append({"name": source_name, "type": source_type})
                    seen.add(source_name)
        
        # 3. 检查已知媒体
        for media in self.known_media:
            if media in text and media not in seen:
                sources.append({"name": media, "type": SourceType.MEDIA})
                seen.add(media)
        
        return sources
    
    def _classify_source(self, source_name: str, text: str) -> str:
        """
        分类来源类型
        
        Args:
            source_name: 来源名称
            text: 文本上下文
            
        Returns:
            来源类型：Media/Official/Social/Other
        """
        source_lower = source_name.lower()
        text_lower = text.lower()
        
        # 检查是否为社交媒体
        if any(keyword in source_lower or keyword in text_lower 
               for keyword in self.social_keywords):
            return SourceType.SOCIAL
        
        # 检查是否为官方来源
        if any(keyword in source_lower or keyword in text_lower 
               for keyword in self.official_keywords):
            return SourceType.OFFICIAL
        
        # 检查是否为已知媒体
        if source_name in self.known_media:
            return SourceType.MEDIA
        
        # 检查常见媒体后缀
        media_suffixes = ["news", "times", "post", "daily", "sports", "fc", "tv"]
        if any(suffix in source_lower for suffix in media_suffixes):
            return SourceType.MEDIA
        
        return SourceType.OTHER
    
    def _extract_constraints(self, text: str, participants: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        提取约束锚点（转会状态、比分、合同等）
        
        Args:
            text: 输入文本
            participants: 已提取的参与者列表
            
        Returns:
            约束列表，格式：[{"type": "TRANSFER_STATUS", "subject": "De Ligt", "expected_state": "..."}, ...]
        """
        constraints = []
        
        # 提取球员名列表（用作约束主体）
        players = [p["name"] for p in participants if p["type"] == EntityType.PLAYER]
        clubs = [p["name"] for p in participants if p["type"] == EntityType.CLUB]
        
        # 1. 转会状态约束
        transfer_keywords = {
            "transfer_possible": ["agreed", "sign", "join", "move", "transfer", "acquire"],
            "transfer_completed": ["signed", "joined", "completed", "confirmed"],
            "transfer_rumored": ["linked", "interested", "target", "considering", "rumor"],
            "transfer_rejected": ["rejected", "turned down", "refused", "declined"],
        }
        
        for state, keywords in transfer_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    for player in players:
                        # 检查球员是否在关键词附近
                        if player in text:
                            constraints.append({
                                "type": ConstraintType.TRANSFER_STATUS,
                                "subject": player,
                                "expected_state": state
                            })
                            break
        
        # 2. 比分状态约束
        # 匹配 "Team A 2-1 Team B" 或 "won 3-2" 等
        score_pattern = r'(\d+)-(\d+)'
        score_matches = re.finditer(score_pattern, text)
        for match in score_matches:
            score = match.group(0)
            constraints.append({
                "type": ConstraintType.SCORE_STATUS,
                "subject": "Match",
                "expected_state": f"score_{score}"
            })
        
        # 3. 合同状态约束
        contract_keywords = {
            "contract_active": ["contract", "deal", "agreement", "terms"],
            "contract_expired": ["expired", "ended", "finished"],
            "contract_extended": ["extended", "renewed", "new deal"],
        }
        
        for state, keywords in contract_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    for player in players:
                        if player in text:
                            constraints.append({
                                "type": ConstraintType.CONTRACT_STATUS,
                                "subject": player,
                                "expected_state": state
                            })
                            break
        
        # 4. 比赛状态约束
        match_keywords = {
            "match_scheduled": ["will play", "scheduled", "upcoming", "next match"],
            "match_completed": ["played", "finished", "ended", "won", "lost", "drew"],
            "match_postponed": ["postponed", "delayed", "rescheduled"],
            "match_cancelled": ["cancelled", "called off"],
        }
        
        for state, keywords in match_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    constraints.append({
                        "type": ConstraintType.MATCH_STATUS,
                        "subject": "Match",
                        "expected_state": state
                    })
                    break
        
        # 5. 伤病状态约束
        injury_keywords = {
            "injured": ["injured", "injury", "hurt", "sidelined"],
            "recovering": ["recovering", "rehabilitation", "return"],
            "fit": ["fit", "available", "ready", "healthy"],
        }
        
        for state, keywords in injury_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    for player in players:
                        if player in text:
                            constraints.append({
                                "type": ConstraintType.INJURY_STATUS,
                                "subject": player,
                                "expected_state": state
                            })
                            break
        
        # 6. 停赛状态约束
        suspension_keywords = {
            "suspended": ["suspended", "ban", "banned"],
            "available": ["available", "eligible"],
        }
        
        for state, keywords in suspension_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    for player in players:
                        if player in text:
                            constraints.append({
                                "type": ConstraintType.SUSPENSION_STATUS,
                                "subject": player,
                                "expected_state": state
                            })
                            break
        
        return constraints
    
    def _determine_fact_type(self, text: str, constraints: List[Dict[str, str]]) -> str:
        """
        判定事实类型：EVENT（历史事件）或 STATE（状态事实）
        
        判定规则（按优先级）：
        Rule 1: 如果脱离"当前时间 now"，该事实无法判断真假 → STATE，否则 → EVENT
        Rule 2: 明确时间点 + 过去时 → EVENT；无时间点 + 身份/状态描述 → STATE
        Rule 3: 比赛结果/转会完成/历史行为 → EVENT；合同状态/职位/伤病 → STATE
        
        Args:
            text: 输入文本
            constraints: 约束锚点列表
            
        Returns:
            "EVENT" 或 "STATE"
        """
        text_lower = text.lower()
        
        # 优先级 1：比分和比赛结果一定是 EVENT
        for constraint in constraints:
            if constraint.get("type") == ConstraintType.SCORE_STATUS:
                return "EVENT"
            if constraint.get("expected_state") == "match_completed":
                return "EVENT"
        
        # 优先级 2：完成时态 + 动作动词 → EVENT
        completion_patterns = [
            r'\b(?:has|have)\s+(?:agreed|signed|joined|scored|won|completed|announced)\b',
            r'\b(?:agreed|signed|joined)\s+(?:to|a|with)\b',
        ]
        
        for pattern in completion_patterns:
            if re.search(pattern, text_lower):
                if re.search(r'\buntil\s+\d{4}\b', text_lower):
                    if re.search(r'\bsigned.*contract.*until\b', text_lower):
                        return "STATE"
                return "EVENT"
        
        # 优先级 3：STATE 强信号 - 身份/状态描述
        state_patterns = [
            r'\bis\s+(?:the\s+)?(?:head\s+)?coach\b',
            r'\bis\s+(?:a\s+)?(?:player|forward|midfielder|defender|goalkeeper)\b',
            r'\bis\s+under\s+contract\b',
            r'\bserves\s+as\b',
            r'\bremains\s+(?:at|with|a)\b',
            r'\bcurrently\s+(?:is|plays|works)\b',
            r'\bis\s+(?:injured|suspended|available|fit)\b',
            r'\b(?:runs|lasts)\s+(?:from|until)\b',
        ]
        
        for pattern in state_patterns:
            if re.search(pattern, text_lower):
                return "STATE"
        
        # 优先级 4：约束类型判定
        for constraint in constraints:
            constraint_type = constraint.get("type")
            expected_state = constraint.get("expected_state", "")
            
            if constraint_type == ConstraintType.CONTRACT_STATUS:
                if expected_state == "contract_active":
                    if not re.search(r'\b(?:signed|agreed|completed).*(?:deal|contract|transfer)\b', text_lower):
                        return "STATE"
            
            if constraint_type in [ConstraintType.INJURY_STATUS, ConstraintType.SUSPENSION_STATUS]:
                if not re.search(r'\b(?:suffered|underwent|received|announced)\b', text_lower):
                    return "STATE"
            
            if expected_state == "transfer_possible":
                if re.search(r'\b(?:has|have)\s+agreed\b', text_lower):
                    return "EVENT"
        
        # 优先级 5：文本中的时间表达 + 动词时态
        has_explicit_time = bool(re.search(r'\bin\s+\d{4}\b|\bon\s+\d{1,2}\s+\w+\s+\d{4}\b', text_lower))
        
        if has_explicit_time:
            past_verbs = [r'\b(?:scored|won|lost|played|joined|signed|agreed|announced)\b']
            for pattern in past_verbs:
                if re.search(pattern, text_lower):
                    return "EVENT"
        
        # 优先级 6：历史关键词
        historical_patterns = [
            r'\bin\s+\d{4}\b',
            r'\blast\s+season\b',
            r'\bscored.*goals?\b',
            r'\bwon.*(?:cup|trophy|title|award)\b',
            r'\bdefeated|beat|drew\b',
        ]
        
        for pattern in historical_patterns:
            if re.search(pattern, text_lower):
                return "EVENT"
        
        # 默认：STATE
        return "STATE"
    
    def _determine_need_resolver(self, fact_type: str, 
                                 temporal_anchors: List[Dict[str, Any]]) -> bool:
        """
        判定是否需要 resolver 进行有效期推理
        
        规则：
        - EVENT → need_resolver = false（点事实，不需要有效期）
        - STATE + 已有 valid_from & valid_to → need_resolver = false
        - STATE + 缺失有效期 → need_resolver = true
        
        Args:
            fact_type: 事实类型（EVENT 或 STATE）
            temporal_anchors: 时间锚点列表
            
        Returns:
            是否需要 resolver
        """
        # EVENT 类型：天然是点事实，不需要 resolver
        if fact_type == "EVENT":
            return False
        
        # STATE 类型：检查是否已有明确的有效期
        if fact_type == "STATE":
            # 检查是否已通过规则抽取到 valid_from 和 valid_to
            for anchor in temporal_anchors:
                if anchor.get("valid_from") is not None and anchor.get("valid_to") is not None:
                    # 已有有效期，不需要 resolver
                    return False
            
            # 没有有效期信息，需要 resolver 推理
            return True
        
        # 兜底：默认不需要（保守策略）
        return False
    
    
    # _extract_time_expressions 已迁移到 extractor/time_expression_extractor.py
    # _extract_event_candidates 已迁移到 extractor/event_candidate_extractor.py
    # _normalize_date 已迁移到 extractor/time_expression_extractor.py
    
    def _align_temporal_anchors(self, events: List[Dict[str, Any]], 
                                   times: List[Dict[str, Any]], 
                                   publish_date: str,
                                   fact_type: str) -> List[Dict[str, Any]]:
        """
        时间-事件对齐（核心 Aligner）
        
        职责：将时间表达式对齐到事件，生成时间锚点
        
        对齐规则：
        1. Duration → 转换为 valid_from/valid_to (基于 publish_date)
        2. 其他时间 → 距离最小匹配（时间在事件后面优先）
        3. 无时间 → 使用 publish_date 作为 fallback
        
        Returns:
            时间锚点列表（每个事件对应1个锚点）
        """
        anchors = []
        
        # 处理 Duration
        duration_times = [t for t in times if t['granularity'] == TimeGranularity.DURATION]
        if duration_times:
            # Duration 通常对应整个文本的事实（合同、签约等）
            for dur_time in duration_times:
                anchor = self._convert_duration_to_anchor(dur_time, publish_date)
                if anchor:
                    anchors.append(anchor)
            return anchors
        
        # 对齐点时间到事件
        point_times = [t for t in times if t['granularity'] != TimeGranularity.DURATION]
        
        if not point_times:
            # 无时间表达，使用 publish_date 作为 fallback
            anchors.append({
                "event_date": None,
                "valid_from": publish_date,
                "valid_to": None,
                "time_type": "FALLBACK",
                "evidence": f"[无显式时间，使用发布日期: {publish_date}]"
            })
            return anchors
        
        # 为每个事件匹配最近的时间
        for event in events:
            event_pos = event['span'][0]  # 事件起始位置
            
            best_time = None
            best_distance = float('inf')
            
            for time in point_times:
                time_pos = time['span'][0]  # 时间表达起始位置
                
                # 计算距离（时间在事件后面优先）
                if time_pos >= event_pos:
                    # 时间在事件后面（自然语序）
                    distance = time_pos - event_pos
                else:
                    # 时间在事件前面（提前出现）
                    distance = event_pos - time_pos + 1000  # 加权惩罚
                
                if distance < best_distance:
                    best_distance = distance
                    best_time = time
            
            if best_time:
                # 根据 fact_type 决定用 event_date 还是 valid_from
                if fact_type == "EVENT":
                    anchors.append({
                        "event_date": best_time['normalized'],
                        "valid_from": None,
                        "valid_to": None,
                        "time_type": "EXPLICIT",
                        "evidence": best_time['evidence']
                    })
                else:  # STATE
                    anchors.append({
                        "event_date": None,
                        "valid_from": best_time['normalized'],
                        "valid_to": None,
                        "time_type": "EXPLICIT",
                        "evidence": best_time['evidence']
                    })
        
        return anchors
    
    def _convert_duration_to_anchor(self, duration_expr: Dict[str, Any], 
                                       anchor_date: str) -> Optional[Dict[str, Any]]:
        """
        将 Duration 转换为时间锚点
        
        Args:
            duration_expr: Duration 时间表达
            anchor_date: 锚定日期（通常是 publish_date - 5天）
            
        Returns:
            时间锚点，包含 valid_from 和 valid_to
        """
        duration_text = duration_expr['normalized'].lower()
        
        # 解析年份数字
        # 支持：four-and-a-half, five, 3, three
        duration_map = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        
        # 尝试匹配数字
        if duration_text.isdigit():
            years = int(duration_text)
        else:
            # 尝试匹配文字数字
            years = None
            for word, num in duration_map.items():
                if word in duration_text:
                    years = num
                    break
            
            # 处理 "four-and-a-half" 格式
            if 'and-a-half' in duration_text or 'and a half' in duration_text:
                if years:
                    years += 0.5
                elif 'four' in duration_text:
                    years = 4.5
        
        if years is None:
            return None
        
        # 计算起止日期
        # anchor_date 通常是 publish_date - 5天
        try:
            if anchor_date:
                start_date = datetime.strptime(anchor_date, "%Y-%m-%d") - timedelta(days=5)
            else:
                start_date = datetime.now()
            
            # 计算结束日期
            end_date = start_date.replace(year=start_date.year + int(years))
            # 加上剩余月份
            months = int((years - int(years)) * 12)
            if months > 0:
                end_date = end_date + timedelta(days=months * 30)
            
            return {
                "event_date": None,
                "valid_from": start_date.strftime("%Y-%m-%d"),
                "valid_to": end_date.strftime("%Y-%m-%d"),
                "time_type": "DURATION",
                "evidence": duration_expr["evidence"]
            }
        except:
            return None
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        将日期字符串标准化为 YYYY-MM-DD 格式
        
        Args:
            date_str: 日期字符串（多种格式）
            
        Returns:
            标准化的日期字符串 (YYYY-MM-DD)，失败返回 None
        """
        date_str = date_str.strip()
        
        # 尝试多种日期格式
        formats = [
            "%d %B %Y",      # 1 September 2025
            "%B %d, %Y",     # September 1, 2025
            "%B %d %Y",      # September 1 2025
            "%B %Y %d",      # September 2025 01 (用于年月转换)
            "%Y-%m-%d",      # 2025-09-01
            "%d-%m-%Y",      # 01-09-2025
            "%m/%d/%Y",      # 09/01/2025
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
    
