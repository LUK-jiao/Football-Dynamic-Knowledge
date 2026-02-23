"""
Query Analyzer for Football Knowledge Graph RAG System

Parses natural language queries into structured constraints for graph retrieval.
"""

from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime, timedelta
from extractor_v1.ollama_backend import OllamaBackend


class QueryAnalyzer:
    """
    Analyzes natural language queries and extracts structured information.
    
    Parses entities, time ranges, constraint types, and query intent.
    """
    
    def __init__(self, model: str = "llama3:latest", fallback_to_rules: bool = True):
        """
        Initialize QueryAnalyzer.
        
        Args:
            model: LLM model name for parsing
            fallback_to_rules: Whether to use rule-based fallback on LLM failure
        """
        self.llm = OllamaBackend(model=model)
        self.fallback_to_rules = fallback_to_rules
        
        # Constraint type keyword mappings
        self.constraint_keywords = {
            "MATCH_ACTION": ["进球", "助攻", "射门", "传球", "犯规", "红牌", "黄牌", "点球", "任意球", "角球"],
            "MATCH_OUTCOME": ["胜", "负", "平", "赢", "输", "比分", "结果", "战绩"],
            "MATCH_CONTEXT": ["比赛", "对阵", "vs", "对战"],
            "PLAYER_MOVEMENT": ["转会", "加盟", "签约", "租借", "交易", "转投"],
            "CONTRACT_EVENT": ["合同", "续约", "签约", "协议"],
            "AVAILABILITY_EVENT": ["伤病", "停赛", "禁赛", "复出", "缺阵"],
            "APPOINTMENT_EVENT": ["任命", "上任", "下课", "解雇", "执教", "教练"],
            "PERFORMANCE_EVENT": ["表现", "评价", "评分", "发挥"],
            "ADMINISTRATIVE_EVENT": ["管理", "行政", "决策"]
        }
        
        # Intent keywords
        self.summary_keywords = ["总结", "概括", "表现如何", "状态", "情况", "怎么样"]
        self.analysis_keywords = ["为什么", "原因", "影响", "分析", "如何", "关系"]
    
    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured format.
        
        Args:
            query: Natural language question
            
        Returns:
            Structured query dictionary with entities, time_range, constraint_types, intent, limit
        """
        # Try LLM-based parsing first
        try:
            result = self._parse_with_llm(query)
            if self._validate_parsed_result(result):
                return result
        except Exception as e:
            print(f"LLM parsing failed: {e}")
        
        # Retry once
        try:
            result = self._parse_with_llm(query)
            if self._validate_parsed_result(result):
                return result
        except Exception as e:
            print(f"LLM parsing retry failed: {e}")
        
        # Fallback to rule-based parsing
        if self.fallback_to_rules:
            print("Falling back to rule-based parsing")
            return self._parse_with_rules(query)
        
        # Return empty structure
        return self._get_empty_structure()
    
    def _parse_with_llm(self, query: str) -> Dict[str, Any]:
        """Parse query using LLM."""
        
        prompt = f"""You are a query parser for a football knowledge graph system.

Parse the following natural language question into a structured JSON format.

Question: {query}

Extract:
1. entities: List of person names, club names mentioned (use original names, not nicknames)
2. time_range: {{start: YYYY-MM-DD or null, end: YYYY-MM-DD or null}}
   - "2025年" → {{"start": "2025-01-01", "end": "2025-12-31"}}
   - "最近" → last 30 days
   - "上个月" → previous month
   - "执教期间" / "转会窗口期" → null (cannot determine specific dates)
3. constraint_types: List from [MATCH_ACTION, MATCH_OUTCOME, MATCH_CONTEXT, PLAYER_MOVEMENT, CONTRACT_EVENT, AVAILABILITY_EVENT, APPOINTMENT_EVENT, PERFORMANCE_EVENT, ADMINISTRATIVE_EVENT]
   - "进球" → MATCH_ACTION
   - "转会" → PLAYER_MOVEMENT
   - "任命" → APPOINTMENT_EVENT
4. intent: "fact" (specific events) / "summary" (overview) / "analysis" (why/how)
   - "总结", "表现如何" → summary
   - "为什么", "影响" → analysis
   - otherwise → fact
5. limit: default 20, increase to 50 if summary/analysis

Output ONLY valid JSON in this exact format:
{{
    "entities": ["Entity1", "Entity2"],
    "time_range": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
    "constraint_types": ["TYPE1", "TYPE2"],
    "intent": "fact",
    "limit": 20
}}

If no entities found, use empty list [].
If no time constraint, use {{"start": null, "end": null}}.
If no constraint types, use empty list [].
"""
        
        response = self.llm.chat(prompt, temperature=0.1)
        
        # Extract JSON from response
        json_str = self._extract_json(response)
        result = json.loads(json_str)
        
        return result
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON string from LLM response."""
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group(0)
        return text.strip()
    
    def _validate_parsed_result(self, result: Dict[str, Any]) -> bool:
        """Validate parsed result structure."""
        required_keys = ["entities", "time_range", "constraint_types", "intent", "limit"]
        
        if not all(key in result for key in required_keys):
            return False
        
        if not isinstance(result["entities"], list):
            return False
        
        if not isinstance(result["time_range"], dict):
            return False
        
        if not isinstance(result["constraint_types"], list):
            return False
        
        if result["intent"] not in ["fact", "summary", "analysis"]:
            return False
        
        if not isinstance(result["limit"], int):
            return False
        
        return True
    
    def _parse_with_rules(self, query: str) -> Dict[str, Any]:
        """Rule-based parsing fallback."""
        
        result = self._get_empty_structure()
        
        # Extract entities (simple pattern matching)
        result["entities"] = self._extract_entities_rules(query)
        
        # Extract time range
        result["time_range"] = self._extract_time_range_rules(query)
        
        # Extract constraint types
        result["constraint_types"] = self._extract_constraint_types_rules(query)
        
        # Determine intent
        result["intent"] = self._determine_intent_rules(query)
        
        # Set limit
        if result["intent"] in ["summary", "analysis"]:
            result["limit"] = 50
        else:
            result["limit"] = 20
        
        return result
    
    def _extract_entities_rules(self, query: str) -> List[str]:
        """Extract entities using rules."""
        entities = []
        
        # Common club names
        clubs = ["Arsenal", "Manchester United", "Chelsea", "Liverpool", "Manchester City", 
                 "Tottenham", "Barcelona", "Real Madrid", "Bayern Munich", "PSG",
                 "阿森纳", "曼联", "切尔西", "利物浦", "曼城", "热刺", "巴萨", "皇马", "拜仁"]
        
        for club in clubs:
            if club in query:
                entities.append(club)
        
        # Extract potential person names (capitalized words)
        words = query.split()
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2:
                # Check if next word is also capitalized (full name)
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    entities.append(f"{word} {words[i + 1]}")
                elif word not in clubs:
                    entities.append(word)
        
        return list(set(entities))
    
    def _extract_time_range_rules(self, query: str) -> Dict[str, Optional[str]]:
        """Extract time range using rules."""
        time_range = {"start": None, "end": None}
        
        today = datetime.now().date()
        
        # Check for year patterns
        year_match = re.search(r'(\d{4})年', query)
        if year_match:
            year = year_match.group(1)
            time_range["start"] = f"{year}-01-01"
            time_range["end"] = f"{year}-12-31"
            return time_range
        
        # Check for "最近" (recent)
        if "最近" in query:
            time_range["start"] = (today - timedelta(days=30)).isoformat()
            time_range["end"] = today.isoformat()
            return time_range
        
        # Check for "上个月" (last month)
        if "上个月" in query:
            last_month = today.replace(day=1) - timedelta(days=1)
            time_range["start"] = last_month.replace(day=1).isoformat()
            time_range["end"] = last_month.isoformat()
            return time_range
        
        # Check for specific dates
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', query)
        if date_match:
            date_str = date_match.group(0)
            time_range["start"] = date_str
            time_range["end"] = date_str
            return time_range
        
        return time_range
    
    def _extract_constraint_types_rules(self, query: str) -> List[str]:
        """Extract constraint types using keyword matching."""
        constraint_types = []
        
        for constraint_type, keywords in self.constraint_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    constraint_types.append(constraint_type)
                    break
        
        return list(set(constraint_types))
    
    def _determine_intent_rules(self, query: str) -> str:
        """Determine query intent using keywords."""
        
        # Check for analysis intent
        for keyword in self.analysis_keywords:
            if keyword in query:
                return "analysis"
        
        # Check for summary intent
        for keyword in self.summary_keywords:
            if keyword in query:
                return "summary"
        
        # Default to fact
        return "fact"
    
    def _get_empty_structure(self) -> Dict[str, Any]:
        """Return empty query structure."""
        return {
            "entities": [],
            "time_range": {"start": None, "end": None},
            "constraint_types": [],
            "intent": "fact",
            "limit": 20
        }
