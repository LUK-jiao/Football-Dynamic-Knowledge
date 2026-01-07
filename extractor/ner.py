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


class SourceType(str, Enum):
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
        
        # 知名足球俱乐部列表
        self.known_clubs = {
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
        
        Args:
            chunk: 语义分块，包含 block_id, text, source, publish_date
            
        Returns:
            完整的分块数据，添加了 anchors 属性
        """
        text = chunk.get("text", "")
        source = chunk.get("source", "")
        publish_date = chunk.get("publish_date", "")
        
        # 提取四类锚点
        participants = self._extract_participants(text)
        temporal_anchors = self._extract_temporal_anchors(text, publish_date)
        sources = self._extract_sources(text, source)
        constraints = self._extract_constraints(text, participants)
        
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
            }
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
    
    def _extract_temporal_anchors(self, text: str, publish_date: str) -> List[Dict[str, str]]:
        """
        提取时间锚点
        
        Args:
            text: 输入文本
            publish_date: 发布日期 (YYYY-MM-DD)
            
        Returns:
            时间锚点列表，格式：[{"event_date": "2025-09-01", "valid_from": "...", "valid_to": "..."}, ...]
        """
        temporal_anchors = []
        
        # 1. 提取明确日期（YYYY-MM-DD, DD/MM/YYYY, Month DD, YYYY等）
        date_patterns = [
            r'\b(\d{4})-(\d{2})-(\d{2})\b',  # 2025-09-01
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',  # 01/09/2025
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',  # September 1, 2025
            r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',  # 1 September 2025
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    date_str = self._normalize_date(match.group(0))
                    if date_str:
                        temporal_anchors.append({
                            "event_date": date_str,
                            "valid_from": date_str,
                            "valid_to": date_str
                        })
                except Exception:
                    pass
        
        # 2. 处理相对日期（today, tomorrow, yesterday, next week等）
        if publish_date:
            relative_dates = self._parse_relative_dates(text, publish_date)
            temporal_anchors.extend(relative_dates)
        
        # 3. 如果没有提取到任何日期，使用发布日期
        if not temporal_anchors and publish_date:
            temporal_anchors.append({
                "event_date": publish_date,
                "valid_from": publish_date,
                "valid_to": publish_date
            })
        
        return temporal_anchors
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        标准化日期为 YYYY-MM-DD 格式
        
        Args:
            date_str: 原始日期字符串
            
        Returns:
            标准化后的日期字符串，或 None
        """
        # 尝试多种日期格式
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%d %b %Y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
    
    def _parse_relative_dates(self, text: str, publish_date: str) -> List[Dict[str, str]]:
        """
        解析相对日期（today, tomorrow, next week等）
        
        Args:
            text: 输入文本
            publish_date: 发布日期
            
        Returns:
            时间锚点列表
        """
        temporal_anchors = []
        
        try:
            base_date = datetime.strptime(publish_date, "%Y-%m-%d")
        except Exception:
            return temporal_anchors
        
        # 相对日期模式
        relative_patterns = {
            r'\btoday\b': 0,
            r'\btomorrow\b': 1,
            r'\byesterday\b': -1,
            r'\bnext week\b': 7,
            r'\blast week\b': -7,
            r'\bnext month\b': 30,
            r'\blast month\b': -30,
        }
        
        for pattern, days_offset in relative_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                event_date = base_date + timedelta(days=days_offset)
                date_str = event_date.strftime("%Y-%m-%d")
                temporal_anchors.append({
                    "event_date": date_str,
                    "valid_from": date_str,
                    "valid_to": date_str
                })
        
        return temporal_anchors
    
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


# 保留旧的 FootballNER 类以保持向后兼容
class FootballNER:
    """
    Football-specific Named Entity Recognition.
    
    已弃用：请使用 FootballAnchorExtractor 进行锚点抽取。
    该类保留仅用于向后兼容。
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize NER model.
        
        Args:
            model_name: Optional model identifier
        """
        self.model_name = model_name
        self.extractor = FootballAnchorExtractor()
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted entities with type and position
        """
        # 使用新的锚点抽取器
        chunk = {
            "block_id": "legacy",
            "text": text,
            "source": "",
            "publish_date": ""
        }
        result = self.extractor.extract_anchors(chunk)
        return result["anchors"]["participants"]
