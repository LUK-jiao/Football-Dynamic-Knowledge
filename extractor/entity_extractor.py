"""
Entity Extractor for Football Domain

Three-layer architecture:
- Layer 1: spaCy NER (high recall entity detection)
- Layer 2: Dictionary/Gazetteer (prior knowledge)
- Layer 3: Syntax & Context Reasoning (role disambiguation)

Principle: Allow missing entities, but DO NOT allow wrong classification.
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import spacy
from spacy.tokens import Doc, Token


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
    Football Domain Entity Extractor
    
    采用三层架构：spaCy NER → Dictionary → Syntax Reasoning
    
    核心原则：
    1. 高精度（不污染下游）
    2. 可解释（每个判定有明确来源）
    3. 可扩展（层次分明，职责清晰）
    """
    
    def __init__(self):
        """初始化实体抽取器"""
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("⚠️  spaCy model 'en_core_web_sm' not found. Installing...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
        
        # Layer 2: Dictionaries (Prior Knowledge)
        self._init_dictionaries()
        
        # Layer 3: Syntax patterns
        self._init_syntax_patterns()
    
    def _init_dictionaries(self):
        """初始化词典（Layer 2）"""
        
        # Person Dictionary: name → possible roles
        self.person_dict = {
            "Mikel Arteta": ["coach", "former_player"],
            "Pep Guardiola": ["coach"],
            "Kepa Arrizabalaga": ["player"],
            "Harry Kane": ["player"],
            "Mohamed Salah": ["player"],
            "Erling Haaland": ["player"],
            "Carlo Ancelotti": ["coach"],
            "Jürgen Klopp": ["coach"],
            "Mauricio Pochettino": ["coach"],
        }
        
        # Club Dictionary: name → metadata
        self.club_dict = {
            "Arsenal": {"type": "Club", "aliases": ["Gunners", "the Gunners"]},
            "Manchester United": {"type": "Club", "aliases": ["Man Utd", "United"]},
            "Manchester City": {"type": "Club", "aliases": ["Man City", "City"]},
            "Chelsea": {"type": "Club", "aliases": ["the Blues"]},
            "Liverpool": {"type": "Club", "aliases": ["the Reds"]},
            "Tottenham": {"type": "Club", "aliases": ["Spurs"]},
            "Bayern Munich": {"type": "Club", "aliases": []},
            "Real Madrid": {"type": "Club", "aliases": []},
            "Barcelona": {"type": "Club", "aliases": ["Barça"]},
            "Paris Saint-Germain": {"type": "Club", "aliases": ["PSG"]},
            "PSG": {"type": "Club", "aliases": []},
            "Juventus": {"type": "Club", "aliases": ["Juve"]},
            "AC Milan": {"type": "Club", "aliases": []},
            "Inter Milan": {"type": "Club", "aliases": ["Inter"]},
            "Borussia Dortmund": {"type": "Club", "aliases": ["Dortmund"]},
            "Ajax": {"type": "Club", "aliases": []},
            "Porto": {"type": "Club", "aliases": []},
            "Benfica": {"type": "Club", "aliases": []},
            "Crystal Palace": {"type": "Club", "aliases": ["Palace"]},
            "West Ham United": {"type": "Club", "aliases": ["West Ham", "the Hammers"]},
            "Lazio": {"type": "Club", "aliases": []},
            "New York City FC": {"type": "Club", "aliases": ["NYCFC"]},
        }
        
        # Tournament Dictionary
        self.tournament_dict = {
            "EFL Cup": "Tournament",
            "FA Cup": "Tournament",
            "Premier League": "Tournament",
            "Champions League": "Tournament",
            "Europa League": "Tournament",
            "World Cup": "Tournament",
            "Bundesliga": "Tournament",
            "La Liga": "Tournament",
            "Serie A": "Tournament",
            "Ligue 1": "Tournament",
            "MLS Cup": "Tournament",
        }
        
        # Stadium Dictionary
        self.stadium_dict = {
            "Old Trafford Stadium": "Stadium",
            "Emirates Stadium": "Stadium",
            "Wembley Stadium": "Stadium",
            "Stamford Bridge": "Stadium",
            "Anfield": "Stadium",
            "Etihad Stadium": "Stadium",
        }
    
    def _init_syntax_patterns(self):
        """初始化语法模式（Layer 3）"""
        
        # Team-like nouns (for possession pattern)
        self.team_nouns = {"side", "team", "squad", "outfit", "men"}
        
        # Coach-related nouns
        self.coach_nouns = {"manager", "coach", "boss", "gaffer"}
        
        # Match action verbs (for player identification)
        self.match_verbs = {
            "score", "save", "miss", "convert", "take", "shoot",
            "assist", "head", "volley", "strike", "pass", "dribble",
            "tackle", "block", "clear", "cross", "chip", "lob",
            "slot", "fire", "net", "bag", "grab", "notch"
        }
        
        # Tournament structure nouns
        self.tournament_structure = {
            "semi-finals", "final", "finals", "quarter-final", 
            "group stage", "knockout", "round", "leg"
        }
    
    def extract_participants(self, text: str) -> List[Dict[str, any]]:
        """
        提取参与者实体（主入口）
        
        三层流程：
        1. spaCy NER 提取候选实体
        2. Dictionary 提供先验知识
        3. Syntax Reasoning 决定最终分类
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表，格式：[{
                "text": str,
                "type": EntityType,
                "confidence": float,
                "source": {"ner": bool, "dictionary": bool, "syntax": bool}
            }, ...]
        """
        # Parse text with spaCy
        doc = self.nlp(text)
        
        print("spacy处理结果：" + str(doc.ents))
        # Layer 1: Extract candidate entities from spaCy NER
        candidates = self._extract_ner_candidates(doc)
        
        # Layer 2: Enrich with dictionary knowledge
        enriched = self._enrich_with_dictionary(candidates, text)
        
        # Layer 3: Apply syntax reasoning for role disambiguation
        final_entities = self._apply_syntax_reasoning(enriched, doc)
        
        # Convert to legacy format for backward compatibility
        return self._convert_to_legacy_format(final_entities)
    
    # ========================================================================
    # Layer 1: Syntax-First Entity Candidate Generation (High Recall)
    # ========================================================================
    
    def _extract_ner_candidates(self, doc: Doc) -> List[Dict]:
        """
        Layer 1: 语法优先的实体候选生成
        
        核心原则：
        - 不判断实体类型
        - 不依赖词典
        - 不以 doc.ents 为唯一来源
        - 只基于语法结构生成候选 span
        
        策略：允许多抽、允许冗余，不允许漏抽
        
        Returns:
            [{
                "text": str,
                "span": (start, end),
                "ner_label": str,  # 保留以兼容后续层
                "tokens": [Token],
                "type": None,
                "confidence": 0.3,
                "source": {"ner": bool, "dictionary": bool, "syntax": bool}
            }]
        """
        # 存储候选实体 span: key = (start_char, end_char)
        candidate_spans = {}
        
        # Rule 1: 连续 PROPN span（核心规则）
        self._extract_continuous_propn_spans(doc, candidate_spans)
        
        # Rule 2: PROPN + NOUN 复合名词
        self._extract_propn_noun_compounds(doc, candidate_spans)
        
        # Rule 3: 所有格结构（poss）
        self._extract_possessive_entities(doc, candidate_spans)
        
        # Rule 4: 介词宾语（pobj）
        self._extract_prepositional_objects(doc, candidate_spans)
        
        # Rule 5: 主语/宾语位置的 PROPN
        self._extract_subject_object_propn(doc, candidate_spans)
        
        # Rule 6: noun_chunk 驱动的 span
        self._extract_noun_chunk_entities(doc, candidate_spans)
        
        # 补充：doc.ents（作为补充，不是核心）
        self._extract_ner_supplement(doc, candidate_spans)
        
        # 转换为标准格式
        return self._convert_spans_to_candidates(doc, candidate_spans)
    
    def _extract_continuous_propn_spans(self, doc: Doc, candidate_spans: Dict):
        """
        Rule 1: 连续 PROPN span
        
        扫描 token 序列，将连续的 PROPN token 合并为一个 span
        单个 PROPN 也要保留
        """
        i = 0
        while i < len(doc):
            if doc[i].pos_ == "PROPN":
                # 找到连续 PROPN 的结束位置
                j = i
                while j < len(doc) and doc[j].pos_ == "PROPN":
                    j += 1
                
                # 生成 span
                start_char = doc[i].idx
                end_char = doc[j-1].idx + len(doc[j-1].text)
                key = (start_char, end_char)
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": list(doc[i:j]),
                        "sources": []
                    }
                candidate_spans[key]["sources"].append("continuous_propn")
                
                i = j
            else:
                i += 1
    
    def _extract_propn_noun_compounds(self, doc: Doc, candidate_spans: Dict):
        """
        Rule 2: PROPN + NOUN 复合名词 (增强版，支持 ADJ amod)
        
        生成满足以下模式的 span:
        - (PROPN)+ (NOUN)+
        - (ADJ with dep_=amod and first letter uppercase) + (NOUN)+
        
        这是为了解决 spaCy 将 "Arsenal" 等专有名词标记为 ADJ 的问题
        """
        i = 0
        while i < len(doc):
            # 情况1: PROPN 开头
            if doc[i].pos_ == "PROPN":
                # 找到连续 PROPN
                j = i
                while j < len(doc) and doc[j].pos_ == "PROPN":
                    j += 1
                
                # 检查后面是否跟着 NOUN
                if j < len(doc) and doc[j].pos_ == "NOUN":
                    # 找到连续 NOUN 的结束
                    k = j
                    while k < len(doc) and doc[k].pos_ == "NOUN":
                        k += 1
                    
                    # 生成 PROPN + NOUN span
                    start_char = doc[i].idx
                    end_char = doc[k-1].idx + len(doc[k-1].text)
                    key = (start_char, end_char)
                    
                    if key not in candidate_spans:
                        candidate_spans[key] = {
                            "tokens": list(doc[i:k]),
                            "sources": []
                        }
                    candidate_spans[key]["sources"].append("propn_noun_compound")
                
                i = j
            
            # 情况2: ADJ (amod) 开头 + 首字母大写 (可能是被误标的专有名词)
            elif (doc[i].pos_ == "ADJ" and 
                  doc[i].dep_ == "amod" and 
                  doc[i].text[0].isupper() and
                  i + 1 < len(doc) and
                  doc[i+1].pos_ == "NOUN"):
                
                # 提取 ADJ
                j = i + 1
                
                # 找到连续 NOUN
                k = j
                while k < len(doc) and doc[k].pos_ == "NOUN":
                    k += 1
                
                # 生成 ADJ + NOUN span
                start_char = doc[i].idx
                end_char = doc[k-1].idx + len(doc[k-1].text)
                key = (start_char, end_char)
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": list(doc[i:k]),
                        "sources": []
                    }
                candidate_spans[key]["sources"].append("propn_noun_compound_amod")
                
                # 同时单独提取 ADJ (可能是被误标的专有名词)
                key_adj = (doc[i].idx, doc[i].idx + len(doc[i].text))
                if key_adj not in candidate_spans:
                    candidate_spans[key_adj] = {
                        "tokens": [doc[i]],
                        "sources": []
                    }
                candidate_spans[key_adj]["sources"].append("amod_capitalized")
                
                i = k
            else:
                i += 1
    
    def _extract_possessive_entities(self, doc: Doc, candidate_spans: Dict):
        """
        Rule 3: 所有格结构（poss）
        
        若 token.dep_ == "poss" 且是 PROPN，抽取完整 PROPN span
        """
        for token in doc:
            if token.dep_ == "poss" and token.pos_ == "PROPN":
                # 找到完整的 PROPN span（向前向后扩展）
                start_idx = token.i
                end_idx = token.i + 1
                
                # 向前扩展
                while start_idx > 0 and doc[start_idx - 1].pos_ == "PROPN":
                    start_idx -= 1
                
                # 向后扩展
                while end_idx < len(doc) and doc[end_idx].pos_ == "PROPN":
                    end_idx += 1
                
                # 生成 span
                start_char = doc[start_idx].idx
                end_char = doc[end_idx-1].idx + len(doc[end_idx-1].text)
                key = (start_char, end_char)
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": list(doc[start_idx:end_idx]),
                        "sources": []
                    }
                candidate_spans[key]["sources"].append("possessive_poss")
    
    def _extract_prepositional_objects(self, doc: Doc, candidate_spans: Dict):
        """
        Rule 4: 介词宾语（pobj）
        
        若 token.dep_ == "pobj" 且介词 ∈ {against, by, with, from, over}
        且 token 或其连续子树为 PROPN span
        """
        target_preps = {"against", "by", "with", "from", "over"}
        
        for token in doc:
            if token.dep_ == "pobj":
                # 检查介词是否在目标集合
                prep = token.head
                if prep.lemma_.lower() in target_preps:
                    # 检查 pobj 是否为 PROPN 或包含 PROPN
                    if token.pos_ == "PROPN":
                        # 找到完整的 PROPN span
                        start_idx = token.i
                        end_idx = token.i + 1
                        
                        # 向前扩展
                        while start_idx > 0 and doc[start_idx - 1].pos_ == "PROPN":
                            start_idx -= 1
                        
                        # 向后扩展
                        while end_idx < len(doc) and doc[end_idx].pos_ == "PROPN":
                            end_idx += 1
                        
                        # 生成 span
                        start_char = doc[start_idx].idx
                        end_char = doc[end_idx-1].idx + len(doc[end_idx-1].text)
                        key = (start_char, end_char)
                        
                        if key not in candidate_spans:
                            candidate_spans[key] = {
                                "tokens": list(doc[start_idx:end_idx]),
                                "sources": []
                            }
                        candidate_spans[key]["sources"].append(f"pobj_{prep.lemma_}")
    
    def _extract_subject_object_propn(self, doc: Doc, candidate_spans: Dict):
        """
        Rule 5: 主语/宾语位置的 PROPN (增强版，支持被误标为 ADJ 的专有名词)
        
        若 token.dep_ ∈ {nsubj, dobj, iobj} 且满足以下之一:
        - token 是 PROPN
        - token 是 ADJ 且首字母大写 (可能被误标的专有名词)
        
        抽取其完整 PROPN span
        """
        target_deps = {"nsubj", "dobj", "iobj", "nsubjpass"}
        
        for token in doc:
            # 情况1: PROPN
            if token.dep_ in target_deps and token.pos_ == "PROPN":
                # 找到完整的 PROPN span
                start_idx = token.i
                end_idx = token.i + 1
                
                # 向前扩展
                while start_idx > 0 and doc[start_idx - 1].pos_ == "PROPN":
                    start_idx -= 1
                
                # 向后扩展
                while end_idx < len(doc) and doc[end_idx].pos_ == "PROPN":
                    end_idx += 1
                
                # 生成 span
                start_char = doc[start_idx].idx
                end_char = doc[end_idx-1].idx + len(doc[end_idx-1].text)
                key = (start_char, end_char)
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": list(doc[start_idx:end_idx]),
                        "sources": []
                    }
                candidate_spans[key]["sources"].append(f"subj_obj_{token.dep_}")
            
            # 情况2: ADJ 且首字母大写 (被误标的专有名词)
            elif (token.dep_ in target_deps and 
                  token.pos_ == "ADJ" and 
                  token.text[0].isupper()):
                
                # 单独提取该 token
                start_char = token.idx
                end_char = token.idx + len(token.text)
                key = (start_char, end_char)
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": [token],
                        "sources": []
                    }
                candidate_spans[key]["sources"].append(f"subj_obj_{token.dep_}_adj")
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": list(doc[start_idx:end_idx]),
                        "sources": []
                    }
                candidate_spans[key]["sources"].append(f"subj_obj_{token.dep_}")
    
    def _extract_noun_chunk_entities(self, doc: Doc, candidate_spans: Dict):
        """
        Rule 6: noun_chunk 驱动的 span
        
        遍历 doc.noun_chunks，若包含 ≥1 PROPN，将整个 chunk 作为候选
        """
        for chunk in doc.noun_chunks:
            # 检查 chunk 是否包含 PROPN
            has_propn = any(token.pos_ == "PROPN" for token in chunk)
            
            if has_propn:
                start_char = chunk.start_char
                end_char = chunk.end_char
                key = (start_char, end_char)
                
                if key not in candidate_spans:
                    candidate_spans[key] = {
                        "tokens": list(chunk),
                        "sources": []
                    }
                candidate_spans[key]["sources"].append("noun_chunk")
    
    def _extract_ner_supplement(self, doc: Doc, candidate_spans: Dict):
        """
        补充：doc.ents（作为补充，不是核心来源）
        
        将 spaCy NER 识别的实体作为补充候选
        """
        for ent in doc.ents:
            # 只关注相关标签
            if ent.label_ not in ["PERSON", "ORG", "EVENT", "GPE", "NORP", "FAC"]:
                continue
            
            key = (ent.start_char, ent.end_char)
            
            if key not in candidate_spans:
                candidate_spans[key] = {
                    "tokens": list(ent),
                    "sources": []
                }
            candidate_spans[key]["sources"].append(f"ner_{ent.label_}")
    
    def _convert_spans_to_candidates(self, doc: Doc, candidate_spans: Dict) -> List[Dict]:
        """
        将 span 字典转换为标准候选格式
        
        去重策略：span 以 (start, end) 作为唯一 key
        """
        candidates = []
        
        for (start_char, end_char), span_info in candidate_spans.items():
            tokens = span_info["tokens"]
            sources = span_info["sources"]
            
            # 提取文本
            text = doc.text[start_char:end_char]
            
            # 推断 NER label
            ner_label = None
            
            # 1. 优先使用 spaCy NER 的标签
            for source in sources:
                if source.startswith("ner_"):
                    ner_label = source.split("_")[1]
                    break
            
            # 2. 如果没有 NER 标签，根据 POS 推断
            if not ner_label and tokens:
                # 如果所有 tokens 都是 PROPN，推断为 PERSON
                if all(t.pos_ == "PROPN" for t in tokens):
                    ner_label = "PERSON"
                # 如果包含 PROPN，可能是 ORG 或 PERSON
                elif any(t.pos_ == "PROPN" for t in tokens):
                    # 保守起见，标记为 PERSON（后续层会校正）
                    ner_label = "PERSON"
            
            candidates.append({
                "text": text,
                "span": (start_char, end_char),
                "ner_label": ner_label,
                "tokens": tokens,
                "type": None,  # To be determined in later layers
                "confidence": 0.3,  # Base confidence
                "source": {
                    "ner": any(s.startswith("ner_") for s in sources),
                    "dictionary": False,
                    "syntax": len(sources) > 0
                },
                "debug_sources": sources  # 便于调试
            })
        
        return candidates
    
    # ========================================================================
    # Layer 2: Dictionary / Gazetteer (Prior Knowledge)
    # ========================================================================
    
    def _enrich_with_dictionary(self, candidates: List[Dict], text: str) -> List[Dict]:
        """
        Layer 2: 使用词典丰富候选实体
        
        职责：提供先验知识，不做最终裁决
        约束：允许多个可能身份共存
        
        Returns:
            Enriched candidates with:
            - possible_types: List[str]  # From dictionary
            - dictionary_confidence: float
        """
        enriched = []
        
        for candidate in candidates:
            entity_text = candidate["text"]
            
            # Check person dictionary
            if entity_text in self.person_dict:
                candidate["possible_types"] = self.person_dict[entity_text]
                candidate["confidence"] += 0.3
                candidate["source"]["dictionary"] = True
            
            # Check club dictionary (exact match or alias)
            elif self._is_club_in_dict(entity_text):
                candidate["type"] = EntityType.CLUB
                candidate["confidence"] += 0.3
                candidate["source"]["dictionary"] = True
            
            # Check tournament dictionary
            elif entity_text in self.tournament_dict:
                candidate["type"] = EntityType.TOURNAMENT
                candidate["confidence"] += 0.3
                candidate["source"]["dictionary"] = True
            
            # Check stadium dictionary
            elif entity_text in self.stadium_dict:
                candidate["type"] = EntityType.STADIUM
                candidate["confidence"] += 0.3
                candidate["source"]["dictionary"] = True
            
            enriched.append(candidate)
        
        # Also add dictionary-only entities not found by NER
        enriched.extend(self._find_dictionary_only_entities(text))
        
        return enriched
    
    def _is_club_in_dict(self, text: str) -> bool:
        """检查是否为已知俱乐部（包括别名）"""
        if text in self.club_dict:
            return True
        
        # Check aliases
        for club_name, metadata in self.club_dict.items():
            if text in metadata.get("aliases", []):
                return True
        
        return False
    
    def _find_dictionary_only_entities(self, text: str) -> List[Dict]:
        """查找词典中但 NER 未发现的实体"""
        entities = []
        
        # Check all clubs
        for club_name in self.club_dict.keys():
            if club_name in text:
                entities.append({
                    "text": club_name,
                    "span": None,
                    "ner_label": None,
                    "tokens": [],
                    "type": EntityType.CLUB,
                    "confidence": 0.3,
                    "source": {
                        "ner": False,
                        "dictionary": True,
                        "syntax": False
                    }
                })
        
        # Check tournaments
        for tournament_name in self.tournament_dict.keys():
            if tournament_name in text:
                entities.append({
                    "text": tournament_name,
                    "span": None,
                    "ner_label": None,
                    "tokens": [],
                    "type": EntityType.TOURNAMENT,
                    "confidence": 0.3,
                    "source": {
                        "ner": False,
                        "dictionary": True,
                        "syntax": False
                    }
                })
        
        return entities
    
    # ========================================================================
    # Layer 3: Syntax & Context Reasoning (Role Disambiguation)
    # ========================================================================
    
    def _apply_syntax_reasoning(self, candidates: List[Dict], doc: Doc) -> List[Dict]:
        """
        Layer 3: 使用语法和上下文推理最终角色
        
        职责：基于依存句法做角色消歧
        优先级：Syntax > Dictionary > NER Label
        
        核心规则：
        1. Coach 识别：PERSON + poss → team-like noun
        2. Player 识别：PERSON + match action verb (nsubj/agent/pobj)
        3. Tournament 识别：结构化模式（Cup/League + 修饰语）
        """
        final_entities = []
        
        for candidate in candidates:
            # Skip if already determined by dictionary
            if candidate["type"] in [EntityType.CLUB, EntityType.TOURNAMENT, EntityType.STADIUM]:
                final_entities.append(candidate)
                continue
            
            # Apply syntax rules for PERSON entities
            if candidate["ner_label"] == "PERSON" and candidate.get("tokens"):
                entity_type, confidence_boost = self._determine_person_role(candidate, doc)
                
                if entity_type:
                    candidate["type"] = entity_type
                    candidate["confidence"] = min(1.0, candidate["confidence"] + confidence_boost)
                    candidate["source"]["syntax"] = True
                else:
                    # Fallback: use dictionary hint if available
                    possible_types = candidate.get("possible_types", [])
                    if "player" in possible_types:
                        candidate["type"] = EntityType.PLAYER
                    elif "coach" in possible_types:
                        candidate["type"] = EntityType.COACH
                    else:
                        candidate["type"] = EntityType.OTHER
            
            # Apply syntax rules for ORG/EVENT (tournament detection)
            elif candidate["ner_label"] in ["ORG", "EVENT"]:
                if self._is_tournament_by_structure(candidate, doc):
                    candidate["type"] = EntityType.TOURNAMENT
                    candidate["confidence"] = min(1.0, candidate["confidence"] + 0.4)
                    candidate["source"]["syntax"] = True
                elif not candidate["type"]:
                    # Default ORG to Club if not determined
                    candidate["type"] = EntityType.CLUB
            
            final_entities.append(candidate)
        
        return final_entities
    
    def _determine_person_role(self, candidate: Dict, doc: Doc) -> Tuple[Optional[EntityType], float]:
        """
        确定 PERSON 的角色（Coach 或 Player）
        
        强规则：
        1. Coach: PERSON —poss→ team-like noun (confidence +0.4)
        2. Player: PERSON 与 match action verb 有语法关系 (confidence +0.4)
        
        Returns:
            (EntityType, confidence_boost)
        """
        tokens = candidate["tokens"]
        if not tokens:
            return None, 0.0
        
        # Get the head token of the entity
        head_token = tokens[-1] if tokens else None
        
        # Rule 1: Coach detection via possession
        # Pattern: "Arteta's Arsenal side"
        if self._is_coach_by_possession(head_token):
            return EntityType.COACH, 0.4
        
        # Rule 2: Coach detection via modification
        # Pattern: "manager Pep Guardiola" or "coach Carlo Ancelotti"
        if self._is_coach_by_modification(tokens, doc):
            return EntityType.COACH, 0.4
        
        # Rule 3: Player detection via match action verbs
        # Pattern: "Kepa saving the spot-kick", "spot-kick taken by Maxence"
        if self._is_player_by_match_action(head_token):
            return EntityType.PLAYER, 0.4
        
        return None, 0.0
    
    def _is_coach_by_possession(self, token: Optional[Token]) -> bool:
        """
        检查是否通过所有格模式识别为 Coach
        
        Pattern: PERSON —poss→ team-like noun
        Example: "Arteta's Arsenal side"
        """
        if not token:
            return False
        
        # Check if token has possessive dependency
        for child in token.children:
            if child.dep_ == "poss":
                # Check if the head is a team-like noun
                if token.head.lemma_.lower() in self.team_nouns:
                    return True
        
        # Reverse check: if this token is the possessive
        if token.dep_ == "poss" and token.head.lemma_.lower() in self.team_nouns:
            return True
        
        return False
    
    def _is_coach_by_modification(self, tokens: List[Token], doc: Doc) -> bool:
        """
        检查是否通过修饰模式识别为 Coach
        
        Pattern: coach-noun + PERSON
        Example: "manager Pep Guardiola"
        """
        for token in tokens:
            # Check left context
            if token.i > 0:
                prev_token = doc[token.i - 1]
                if prev_token.lemma_.lower() in self.coach_nouns:
                    return True
            
            # Check if person is apposition to coach noun
            if token.dep_ == "appos" and token.head.lemma_.lower() in self.coach_nouns:
                return True
        
        return False
    
    def _is_player_by_match_action(self, token: Optional[Token]) -> bool:
        """
        检查是否通过比赛动作动词识别为 Player
        
        Pattern: PERSON + match action verb (nsubj/agent/pobj)
        Example: "Kepa saving", "taken by Maxence"
        """
        if not token:
            return False
        
        # Check if person is subject/agent of match verb
        if token.head.lemma_.lower() in self.match_verbs:
            if token.dep_ in ["nsubj", "agent", "pobj", "nsubjpass"]:
                return True
        
        # Check if person has match verb as child
        for child in token.children:
            if child.lemma_.lower() in self.match_verbs:
                return True
        
        # 特殊处理：被动语态 "taken by Person"
        # 检查是否为 "by" 的宾语，且 "by" 的父节点是 match verb
        if token.dep_ == "pobj":
            # 找到 "by" 介词
            prep = token.head
            if prep.lemma_.lower() == "by":
                # 检查 "by" 的父节点是否为 match verb
                if prep.head.lemma_.lower() in self.match_verbs:
                    return True
        
        return False
    
    def _is_tournament_by_structure(self, candidate: Dict, doc: Doc) -> bool:
        """
        检查是否通过结构模式识别为 Tournament
        
        Patterns:
        1. Contains "Cup" / "League" / "Championship"
        2. Modifies tournament structure nouns (semi-finals, final, etc.)
        """
        text = candidate["text"].lower()
        
        # Pattern 1: Contains tournament keywords
        if any(keyword in text for keyword in ["cup", "league", "championship"]):
            return True
        
        # Pattern 2: Modifies tournament structure
        tokens = candidate.get("tokens", [])
        for token in tokens:
            for child in token.children:
                if child.lemma_.lower() in self.tournament_structure:
                    return True
            
            # Check if token modifies structure noun
            if token.head.lemma_.lower() in self.tournament_structure:
                return True
        
        return False
    
    # ========================================================================
    # Utility: Format Conversion
    # ========================================================================
    
    def _convert_to_legacy_format(self, entities: List[Dict]) -> List[Dict[str, str]]:
        """
        转换为旧格式以保持向后兼容
        
        Legacy format: [{"type": str, "name": str}]
        """
        legacy_entities = []
        seen = set()
        
        for entity in entities:
            name = entity["text"]
            entity_type = entity.get("type", EntityType.OTHER)
            
            # 去重
            if name in seen:
                continue
            seen.add(name)
            
            # 只输出有明确类型的实体
            if entity_type and entity_type != EntityType.OTHER:
                legacy_entities.append({
                    "type": entity_type,
                    "name": name
                })
        
        return legacy_entities
