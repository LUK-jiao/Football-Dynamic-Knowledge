"""
Entity Extractor for Football Domain

Extracts participant entities including:
- Players
- Clubs
- Coaches
- Teams
- Referees
- Stadiums
- Tournaments
"""

import re
from typing import List, Dict
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


class EntityExtractor:
    """
    足球领域实体抽取器
    
    从文本中提取参与者实体（球员、球队、教练等）
    """
    
    def __init__(self):
        """初始化实体抽取器"""
        # 知名足球俱乐部列表 #todo 还要加上球员和教练的名单
        self.known_clubs = { #todo 拓展一下俱乐部，起码全部英超俱乐部要有，并且还需要转换一下昵称，比如曼城->City，曼联->Utd，阿森纳->Gunners
            "Manchester United", "Bayern Munich", "Real Madrid", "Barcelona", 
            "Liverpool", "Chelsea", "Arsenal", "Manchester City", "Tottenham",
            "Paris Saint-Germain", "PSG", "Juventus", "AC Milan", "Inter Milan",
            "Borussia Dortmund", "Ajax", "Porto", "Benfica"
        }
    
    def extract_participants(self, text: str) -> List[Dict[str, str]]:
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
