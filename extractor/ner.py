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
    
    def _extract_temporal_anchors(self, text: str, publish_date: str) -> List[Dict[str, Any]]:
        """
        提取时间锚点（严格遵守时间语义分类）
        
        时间锚点的五种语义：
        T1. EXPLICIT - 显式时间点（文本直接出现的具体日期）
        T2. RELATIVE - 相对时间（基于 publish_date 可安全解析的）
        T3. VALID_FROM - 时间区间起点（明确声明"从某时开始"）
        T4. VALID_TO - 时间区间终点（明确声明"到某时为止"）
        T5. FALLBACK - 事件默认时间（完全无时间信息时使用 publish_date）
        
        Args:
            text: 输入文本
            publish_date: 发布日期 (YYYY-MM-DD)
            
        Returns:
            时间锚点列表，格式：[{
                "event_date": "YYYY-MM-DD | YYYY-MM | null",
                "valid_from": "YYYY-MM-DD | YYYY-MM | null",
                "valid_to": "YYYY-MM-DD | YYYY-MM | null",
                "time_type": "EXPLICIT | RELATIVE | VALID_FROM | VALID_TO | FALLBACK",
                "evidence": "原始文本片段"
            }, ...]
        """
        temporal_anchors = []
        seen_evidence = set()  # 避免重复提取同一时间表达
        
        # ====================================================================
        # T1. 显式时间点（Explicit Date）
        # ====================================================================
        explicit_anchors = self._extract_explicit_dates(text, seen_evidence)
        temporal_anchors.extend(explicit_anchors)
        
        # ====================================================================
        # T2. 相对时间（Relative Date）
        # ====================================================================
        if publish_date:
            relative_anchors = self._parse_relative_dates(text, publish_date, seen_evidence)
            temporal_anchors.extend(relative_anchors)
        
        # ====================================================================
        # T3. 时间区间起点（Validity Start）
        # ====================================================================
        valid_from_anchors = self._extract_valid_from(text, publish_date, seen_evidence)
        temporal_anchors.extend(valid_from_anchors)
        
        # ====================================================================
        # T4. 时间区间终点（Validity End）
        # ====================================================================
        valid_to_anchors = self._extract_valid_to(text, publish_date, seen_evidence)
        temporal_anchors.extend(valid_to_anchors)
        
        # ====================================================================
        # T5. 事件默认时间（Fallback Event Date）
        # ====================================================================
        # 仅当完全没有任何时间表达时，才使用 publish_date 作为兜底
        if not temporal_anchors and publish_date:
            temporal_anchors.append({
                "event_date": publish_date,
                "valid_from": None,
                "valid_to": None,
                "time_type": "FALLBACK",
                "evidence": f"[无显式时间，使用发布日期: {publish_date}]"
            })
        
        return temporal_anchors
    
    def _extract_explicit_dates(self, text: str, seen_evidence: set) -> List[Dict[str, Any]]:
        """
        提取显式时间点（T1）
        
        支持格式：
        - 完整日期: 2025-09-01, 1 September 2025, September 1, 2025
        - 年月: in September 2025, during March 2023
        - 年份/赛季: in 2021, the 2021 season
        """
        anchors = []
        
        # 1. 完整日期格式
        date_patterns = [
            (r'\b(\d{4})-(\d{2})-(\d{2})\b', "full_date"),  # 2025-09-01
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', "full_date"),  # 01/09/2025
            (r'\bon\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b', "full_date"),  # on 14 January
            (r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b', "full_date"),  # September 1, 2025
        ]
        
        for pattern, date_type in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(0).strip()
                if evidence in seen_evidence:
                    continue
                
                date_str = self._normalize_date(evidence)
                if date_str:
                    anchors.append({
                        "event_date": date_str,
                        "valid_from": None,
                        "valid_to": None,
                        "time_type": "EXPLICIT",
                        "evidence": evidence
                    })
                    seen_evidence.add(evidence)
        
        # 2. 年月格式（in September 2025, during March 2023）
        month_year_pattern = r'\b(?:in|during)\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b'
        matches = re.finditer(month_year_pattern, text, re.IGNORECASE)
        for match in matches:
            evidence = match.group(0).strip()
            if evidence in seen_evidence:
                continue
            
            month_year = match.group(1)
            date_str = self._normalize_date(month_year + " 01")  # 转为月初
            if date_str:
                # 只保留年月
                year_month = date_str[:7]  # YYYY-MM
                anchors.append({
                    "event_date": year_month,
                    "valid_from": None,
                    "valid_to": None,
                    "time_type": "EXPLICIT",
                    "evidence": evidence
                })
                seen_evidence.add(evidence)
        
        # 3. 赛季格式（the 2021 season, 2021/22 season）
        season_patterns = [
            r'\bthe\s+(\d{4})\s+season\b',
            r'\b(\d{4})/\d{2}\s+season\b',
        ]
        for pattern in season_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(0).strip()
                if evidence in seen_evidence:
                    continue
                
                year = match.group(1)
                anchors.append({
                    "event_date": year,  # 只保留年份
                    "valid_from": None,
                    "valid_to": None,
                    "time_type": "EXPLICIT",
                    "evidence": evidence
                })
                seen_evidence.add(evidence)
        
        return anchors
    
    def _extract_valid_from(self, text: str, publish_date: str, seen_evidence: set) -> List[Dict[str, Any]]:
        """
        提取时间区间起点（T3）
        
        只有文本明确声明"从某时开始"时才提取
        关键词：from, starting, beginning, since
        """
        anchors = []
        
        # 匹配模式：from/starting/beginning + 时间表达
        patterns = [
            r'\b(?:from|starting|beginning)\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            r'\b(?:from|starting|beginning)\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            r'\b(?:from|since)\s+(next\s+(?:week|month|season|year))\b',
            r'\b(?:from|since)\s+(today|tomorrow|yesterday)\b',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(0).strip()
                if evidence in seen_evidence:
                    continue
                
                time_expr = match.group(1).strip()
                
                # 尝试解析为具体日期
                date_str = self._normalize_date(time_expr)
                if not date_str and publish_date:
                    # 尝试作为相对时间解析
                    date_str = self._resolve_relative_time(time_expr, publish_date)
                
                if date_str:
                    anchors.append({
                        "event_date": None,
                        "valid_from": date_str,
                        "valid_to": None,
                        "time_type": "VALID_FROM",
                        "evidence": evidence
                    })
                    seen_evidence.add(evidence)
        
        return anchors
    
    def _extract_valid_to(self, text: str, publish_date: str, seen_evidence: set) -> List[Dict[str, Any]]:
        """
        提取时间区间终点（T4）
        
        只有文本明确声明"到某时为止"时才提取
        关键词：until, till, through, by, to
        """
        anchors = []
        
        # 匹配模式：until/till/through + 时间表达
        patterns = [
            r'\b(?:until|till|through)\s+(\d{4})\b',  # until 2028
            r'\b(?:until|till|through)\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            r'\b(?:until|till|through)\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            r'\b(?:until|till|through)\s+the\s+end\s+of\s+(?:the\s+)?(\d{4})\s+season\b',
            r'\b(?:by|to)\s+(next\s+(?:week|month|season|year))\b',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(0).strip()
                if evidence in seen_evidence:
                    continue
                
                time_expr = match.group(1).strip()
                
                # 尝试解析为具体日期
                date_str = self._normalize_date(time_expr)
                if not date_str:
                    # 可能只是年份
                    if re.match(r'^\d{4}$', time_expr):
                        date_str = time_expr
                    elif publish_date:
                        # 尝试作为相对时间解析
                        date_str = self._resolve_relative_time(time_expr, publish_date)
                
                if date_str:
                    anchors.append({
                        "event_date": None,
                        "valid_from": None,
                        "valid_to": date_str,
                        "time_type": "VALID_TO",
                        "evidence": evidence
                    })
                    seen_evidence.add(evidence)
        
        return anchors
    
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
    
    def _parse_relative_dates(self, text: str, publish_date: str, seen_evidence: set) -> List[Dict[str, Any]]:
        """
        解析相对时间（T2）
        
        只解析可以安全转换为具体日期的相对时间表达
        不可解析的（如 "recently", "soon"）直接忽略
        
        Args:
            text: 输入文本
            publish_date: 发布日期 (YYYY-MM-DD)
            seen_evidence: 已提取的证据集合
            
        Returns:
            相对时间锚点列表
        """
        temporal_anchors = []
        
        try:
            base_date = datetime.strptime(publish_date, "%Y-%m-%d")
        except Exception:
            return temporal_anchors
        
        # 相对日期模式（天数偏移）
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
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(0).strip()
                if evidence in seen_evidence:
                    continue
                
                event_date = base_date + timedelta(days=days_offset)
                date_str = event_date.strftime("%Y-%m-%d")
                
                temporal_anchors.append({
                    "event_date": date_str,
                    "valid_from": None,
                    "valid_to": None,
                    "time_type": "RELATIVE",
                    "evidence": evidence
                })
                seen_evidence.add(evidence)
        
        # 相对赛季（需要上下文判断，目前仅支持明确的）
        season_patterns = {
            r'\bthis season\b': 0,
            r'\blast season\b': -1,
            r'\bnext season\b': 1,
        }
        
        for pattern, season_offset in season_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(0).strip()
                if evidence in seen_evidence:
                    continue
                
                # 假设赛季从当年开始（简化处理）
                current_year = base_date.year
                season_year = current_year + season_offset
                
                temporal_anchors.append({
                    "event_date": str(season_year),  # 只保留年份
                    "valid_from": None,
                    "valid_to": None,
                    "time_type": "RELATIVE",
                    "evidence": evidence
                })
                seen_evidence.add(evidence)
        
        return temporal_anchors
    
    def _resolve_relative_time(self, time_expr: str, publish_date: str) -> Optional[str]:
        """
        辅助方法：将相对时间表达解析为具体日期
        
        Args:
            time_expr: 相对时间表达（如 "next week", "tomorrow"）
            publish_date: 发布日期 (YYYY-MM-DD)
            
        Returns:
            解析后的日期字符串，或 None
        """
        try:
            base_date = datetime.strptime(publish_date, "%Y-%m-%d")
        except Exception:
            return None
        
        time_expr_lower = time_expr.lower()
        
        # 简单的相对时间映射
        offset_map = {
            "today": 0,
            "tomorrow": 1,
            "yesterday": -1,
            "next week": 7,
            "last week": -7,
            "next month": 30,
            "last month": -30,
            "next year": 365,
            "last year": -365,
        }
        
        if time_expr_lower in offset_map:
            result_date = base_date + timedelta(days=offset_map[time_expr_lower])
            return result_date.strftime("%Y-%m-%d")
        
        # 赛季表达
        if "season" in time_expr_lower:
            if "next" in time_expr_lower:
                return str(base_date.year + 1)
            elif "last" in time_expr_lower:
                return str(base_date.year - 1)
            elif "this" in time_expr_lower:
                return str(base_date.year)
        
        return None
    
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
