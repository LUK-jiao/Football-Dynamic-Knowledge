"""
Query Analyzer for Football Knowledge Graph RAG System

Parses natural language queries into structured constraints for graph retrieval.
"""

from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime, timedelta
from rag.llm_backend import RAGLLMBackend


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
        self.llm = RAGLLMBackend(model=model, default_temperature=0.1)
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
        
        prompt = f"""You are a structured query parser for a football knowledge graph system.

                    Your task is to convert a natural language question into a structured JSON object.

                    You MUST strictly follow the schema below.
                    You MUST return valid JSON only.
                    Do NOT include explanations.
                    Do NOT wrap the output in markdown.
                    Do NOT include any extra text.

                    Convert the following user question into a structured query.

                    Knowledge Graph Schema:

                    1) Event node:
                    - event_id
                    - event_description
                    - fact_type: EVENT | RELATION | STATE
                    - event_date
                    - valid_from
                    - valid_to

                    2) Entity node:
                    - name
                    - type: Person | Club | NationalTeam | Competition | Stadium

                    3) ConstraintAnchor types (ONLY choose from these 9):
                    - MATCH_ACTION
                    - MATCH_OUTCOME
                    - MATCH_CONTEXT
                    - PLAYER_MOVEMENT
                    - CONTRACT_EVENT
                    - AVAILABILITY_EVENT
                    - APPOINTMENT_EVENT
                    - PERFORMANCE_EVENT
                    - ADMINISTRATIVE_EVENT

                    ---

                    Output JSON schema (strictly follow this):

                    {{
                    "entities": [
                        {{
                        "name": string,
                        "entity_type": "Person" | "Club" | "NationalTeam" | "Competition" | "Stadium" | null
                        }}
                    ],

                    "constraint_types": [
                        "MATCH_ACTION" |
                        "MATCH_OUTCOME" |
                        "MATCH_CONTEXT" |
                        "PLAYER_MOVEMENT" |
                        "CONTRACT_EVENT" |
                        "AVAILABILITY_EVENT" |
                        "APPOINTMENT_EVENT" |
                        "PERFORMANCE_EVENT" |
                        "ADMINISTRATIVE_EVENT"
                    ],

                    "fact_types": [
                        "EVENT" | "RELATION" | "STATE"
                    ],

                    "time_filter": {{
                        "mode": "event_date" | "valid_range" | null,
                        "start": "YYYY-MM-DD" | null,
                        "end": "YYYY-MM-DD" | null
                    }},

                    "intent": "fact" | "summary" | "analysis"
                    }}

                    ---

                    Parsing Rules:

                    1. Extract only football-related entities.
                    2. Do NOT extract dates as entities.
                    3. constraint_types must be chosen ONLY from the allowed list.
                    4. If no constraint type is clearly implied, return empty list [].
                    5. fact_types:
                    - Use "EVENT" for match results, goals, transfers, appointments.
                    - Use "STATE" for roles or statuses.
                    - If unclear, default to ["EVENT"].
                    6. time_filter:
                    - If a specific year is mentioned, convert to:
                        start = YYYY-01-01
                        end   = YYYY-12-31
                    - If a specific month is mentioned:
                        convert to first and last day of that month.
                    - If no time expression is present:
                        set mode=null, start=null, end=null.
                    7. intent:
                    - If the question asks to list specific facts → "fact"
                    - If it asks to summarize performance or period → "summary"
                    - If it asks why / impact / analysis → "analysis"

                    If something is unknown, use null or empty list.
                    Do NOT invent data.
                    Return valid JSON only.

                    User Question:
                    "{query}" """
        
        response = self.llm.generate_structured(prompt, temperature=0.1)
        
        # Extract JSON from response
        json_str = self._extract_json(response)
        result = json.loads(json_str)
        
        # Print raw LLM output for debugging
        print(f"\n📄 Raw LLM JSON Output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # Add default limit if not present
        if "limit" not in result:
            intent = result.get("intent", "fact")
            if intent in ["summary", "analysis"]:
                result["limit"] = 50
            else:
                result["limit"] = 20
        
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
        required_keys = ["entities", "constraint_types", "intent"]
        
        if not all(key in result for key in required_keys):
            return False
        
        if not isinstance(result["entities"], list):
            return False
        
        # Validate entities structure
        for entity in result["entities"]:
            if isinstance(entity, dict):
                if "name" not in entity:
                    return False
        
        # Validate time_filter if present
        if "time_filter" in result:
            if not isinstance(result["time_filter"], dict):
                return False
        
        if not isinstance(result["constraint_types"], list):
            return False
        
        if result["intent"] not in ["fact", "summary", "analysis"]:
            return False
        
        return True
    
    def _parse_with_rules(self, query: str) -> Dict[str, Any]:
        """Rule-based parsing fallback."""
        
        result = self._get_empty_structure()
        
        # Extract entities (simple pattern matching) - return as objects
        entity_names = self._extract_entities_rules(query)
        result["entities"] = [{"name": name, "entity_type": None} for name in entity_names]
        
        # Extract time range
        result["time_filter"] = self._extract_time_range_rules(query)
        
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
        time_filter = {"mode": None, "start": None, "end": None}
        
        today = datetime.now().date()
        
        # Check for year patterns
        year_match = re.search(r'(\d{4})年', query)
        if year_match:
            year = year_match.group(1)
            time_filter["mode"] = "event_date"
            time_filter["start"] = f"{year}-01-01"
            time_filter["end"] = f"{year}-12-31"
            return time_filter
        
        # Check for "最近" (recent)
        if "最近" in query or "recent" in query.lower():
            time_filter["mode"] = "event_date"
            time_filter["start"] = (today - timedelta(days=30)).isoformat()
            time_filter["end"] = today.isoformat()
            return time_filter
        
        # Check for "上个月" (last month)
        if "上个月" in query:
            last_month = today.replace(day=1) - timedelta(days=1)
            time_filter["mode"] = "event_date"
            time_filter["start"] = last_month.replace(day=1).isoformat()
            time_filter["end"] = last_month.isoformat()
            return time_filter
        
        # Check for specific dates
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', query)
        if date_match:
            date_str = date_match.group(0)
            time_filter["mode"] = "event_date"
            time_filter["start"] = date_str
            time_filter["end"] = date_str
            return time_filter
        
        return time_filter
    
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
            "time_filter": {"mode": None, "start": None, "end": None},
            "constraint_types": [],
            "fact_types": [],
            "intent": "fact",
            "limit": 20
        }
