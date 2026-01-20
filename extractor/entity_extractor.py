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
        """
        初始化词典（Layer 2）
        
        每个词典条目包含：
        - canonical: 规范名称
        - aliases: 别名列表
        - id: 稳定的实体ID
        - type: 实体类型
        """
        
        # Player Dictionary
        self.player_dict = {
            "Kepa Arrizabalaga": {
                "canonical": "Kepa Arrizabalaga",
                "aliases": ["Kepa"],
                "id": "player_kepa_arrizabalaga",
                "type": EntityType.PLAYER
            },
            "Maxence Lacroix": {
                "canonical": "Maxence Lacroix",
                "aliases": ["Lacroix"],
                "id": "player_maxence_lacroix",
                "type": EntityType.PLAYER
            },
            "Harry Kane": {
                "canonical": "Harry Kane",
                "aliases": ["Kane"],
                "id": "player_harry_kane",
                "type": EntityType.PLAYER
            },
            "Mohamed Salah": {
                "canonical": "Mohamed Salah",
                "aliases": ["Salah", "Mo Salah"],
                "id": "player_mohamed_salah",
                "type": EntityType.PLAYER
            },
            "Erling Haaland": {
                "canonical": "Erling Haaland",
                "aliases": ["Haaland"],
                "id": "player_erling_haaland",
                "type": EntityType.PLAYER
            },
            "Bukayo Saka": {
                "canonical": "Bukayo Saka",
                "aliases": ["Saka"],
                "id": "player_bukayo_saka",
                "type": EntityType.PLAYER
            },
            "Gabriel Jesus": {
                "canonical": "Gabriel Jesus",
                "aliases": ["Jesus"],
                "id": "player_gabriel_jesus",
                "type": EntityType.PLAYER
            },
        }
        
        # Coach Dictionary
        self.coach_dict = {
            "Mikel Arteta": {
                "canonical": "Mikel Arteta",
                "aliases": ["Arteta"],
                "id": "coach_mikel_arteta",
                "type": EntityType.COACH
            },
            "Pep Guardiola": {
                "canonical": "Pep Guardiola",
                "aliases": ["Guardiola"],
                "id": "coach_pep_guardiola",
                "type": EntityType.COACH
            },
            "Carlo Ancelotti": {
                "canonical": "Carlo Ancelotti",
                "aliases": ["Ancelotti"],
                "id": "coach_carlo_ancelotti",
                "type": EntityType.COACH
            },
            "Jürgen Klopp": {
                "canonical": "Jürgen Klopp",
                "aliases": ["Klopp", "Jurgen Klopp"],
                "id": "coach_jurgen_klopp",
                "type": EntityType.COACH
            },
            "Mauricio Pochettino": {
                "canonical": "Mauricio Pochettino",
                "aliases": ["Pochettino"],
                "id": "coach_mauricio_pochettino",
                "type": EntityType.COACH
            },
        }
        
        # Club Dictionary
        self.club_dict = {
            "Arsenal": {
                "canonical": "Arsenal",
                "aliases": ["Gunners", "the Gunners", "Arsenal FC"],
                "id": "club_arsenal",
                "type": EntityType.CLUB
            },
            "Manchester United": {
                "canonical": "Manchester United",
                "aliases": ["Man Utd", "United", "Man United", "MUFC"],
                "id": "club_manchester_united",
                "type": EntityType.CLUB
            },
            "Manchester City": {
                "canonical": "Manchester City",
                "aliases": ["Man City", "City", "MCFC"],
                "id": "club_manchester_city",
                "type": EntityType.CLUB
            },
            "Chelsea": {
                "canonical": "Chelsea",
                "aliases": ["the Blues", "Chelsea FC"],
                "id": "club_chelsea",
                "type": EntityType.CLUB
            },
            "Liverpool": {
                "canonical": "Liverpool",
                "aliases": ["the Reds", "Liverpool FC", "LFC"],
                "id": "club_liverpool",
                "type": EntityType.CLUB
            },
            "Tottenham Hotspur": {
                "canonical": "Tottenham Hotspur",
                "aliases": ["Spurs", "Tottenham", "Hotspur"],
                "id": "club_tottenham",
                "type": EntityType.CLUB
            },
            "Crystal Palace": {
                "canonical": "Crystal Palace",
                "aliases": ["Palace", "the Eagles"],
                "id": "club_crystal_palace",
                "type": EntityType.CLUB
            },
            "West Ham United": {
                "canonical": "West Ham United",
                "aliases": ["West Ham", "the Hammers", "WHUFC"],
                "id": "club_west_ham",
                "type": EntityType.CLUB
            },
            "Bayern Munich": {
                "canonical": "Bayern Munich",
                "aliases": ["Bayern", "FC Bayern"],
                "id": "club_bayern_munich",
                "type": EntityType.CLUB
            },
            "Real Madrid": {
                "canonical": "Real Madrid",
                "aliases": ["Madrid", "Los Blancos"],
                "id": "club_real_madrid",
                "type": EntityType.CLUB
            },
            "Barcelona": {
                "canonical": "Barcelona",
                "aliases": ["Barça", "Barca", "FC Barcelona"],
                "id": "club_barcelona",
                "type": EntityType.CLUB
            },
            "Paris Saint-Germain": {
                "canonical": "Paris Saint-Germain",
                "aliases": ["PSG", "Paris SG"],
                "id": "club_psg",
                "type": EntityType.CLUB
            },
        }
        
        # Competition Dictionary
        self.competition_dict = {
            "EFL Cup": {
                "canonical": "EFL Cup",
                "aliases": ["Carabao Cup", "League Cup"],
                "id": "competition_efl_cup",
                "type": EntityType.TOURNAMENT
            },
            "FA Cup": {
                "canonical": "FA Cup",
                "aliases": ["The FA Cup"],
                "id": "competition_fa_cup",
                "type": EntityType.TOURNAMENT
            },
            "Premier League": {
                "canonical": "Premier League",
                "aliases": ["EPL", "English Premier League"],
                "id": "competition_premier_league",
                "type": EntityType.TOURNAMENT
            },
            "Champions League": {
                "canonical": "UEFA Champions League",
                "aliases": ["Champions League", "UCL", "European Cup"],
                "id": "competition_champions_league",
                "type": EntityType.TOURNAMENT
            },
            "Europa League": {
                "canonical": "UEFA Europa League",
                "aliases": ["Europa League", "UEL"],
                "id": "competition_europa_league",
                "type": EntityType.TOURNAMENT
            },
            "World Cup": {
                "canonical": "FIFA World Cup",
                "aliases": ["World Cup", "WC"],
                "id": "competition_world_cup",
                "type": EntityType.TOURNAMENT
            },
        }
        
        # Stadium Dictionary
        self.stadium_dict = {
            "Wembley": {
                "canonical": "Wembley Stadium",
                "aliases": ["Wembley"],
                "id": "stadium_wembley",
                "type": EntityType.STADIUM
            },
            "Stamford Bridge": {
                "canonical": "Stamford Bridge",
                "aliases": ["the Bridge"],
                "id": "stadium_stamford_bridge",
                "type": EntityType.STADIUM
            },
            "Old Trafford": {
                "canonical": "Old Trafford",
                "aliases": ["Theatre of Dreams"],
                "id": "stadium_old_trafford",
                "type": EntityType.STADIUM
            },
            "Emirates Stadium": {
                "canonical": "Emirates Stadium",
                "aliases": ["Emirates", "the Emirates"],
                "id": "stadium_emirates",
                "type": EntityType.STADIUM
            },
            "Anfield": {
                "canonical": "Anfield",
                "aliases": [],
                "id": "stadium_anfield",
                "type": EntityType.STADIUM
            },
            "Etihad Stadium": {
                "canonical": "Etihad Stadium",
                "aliases": ["Etihad"],
                "id": "stadium_etihad",
                "type": EntityType.STADIUM
            },
        }
        
        # Build reverse index for fast lookup (canonical + aliases → entry)
        self._build_dictionary_indices()
    
    def _build_dictionary_indices(self):
        """
        构建反向索引以支持快速查找
        
        索引结构：
        {
            "exact": {name_lower → (dict_name, entry)},
            "tokens": {token_lower → [(dict_name, entry, full_name)]},
        }
        """
        self.dict_index = {
            "exact": {},    # 精确匹配（canonical + aliases）
            "tokens": {},   # 单token匹配（用于部分匹配）
        }
        
        # Index all dictionaries
        for dict_name, dictionary in [
            ("player", self.player_dict),
            ("coach", self.coach_dict),
            ("club", self.club_dict),
            ("competition", self.competition_dict),
            ("stadium", self.stadium_dict),
        ]:
            for canonical, entry in dictionary.items():
                # Index canonical name
                self._add_to_index(dict_name, entry, canonical, is_canonical=True)
                
                # Index aliases
                for alias in entry["aliases"]:
                    self._add_to_index(dict_name, entry, alias, is_canonical=False)
    
    def _add_to_index(self, dict_name: str, entry: Dict, name: str, is_canonical: bool):
        """添加一个名称到索引"""
        name_lower = name.lower()
        
        # Exact match index
        if name_lower not in self.dict_index["exact"]:
            self.dict_index["exact"][name_lower] = []
        self.dict_index["exact"][name_lower].append({
            "dict": dict_name,
            "entry": entry,
            "match_name": name,
            "is_canonical": is_canonical
        })
        
        # Token-based index (for partial matching)
        tokens = name_lower.split()
        for token in tokens:
            # Skip very common tokens to reduce ambiguity
            if token in {"the", "of", "fc", "united", "city"}:
                continue
            
            if token not in self.dict_index["tokens"]:
                self.dict_index["tokens"][token] = []
            self.dict_index["tokens"][token].append({
                "dict": dict_name,
                "entry": entry,
                "full_name": name,
                "is_canonical": is_canonical
            })
    
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
    # Layer 2: Dictionary Enrichment & Typing (Validation Layer)
    # ========================================================================
    
    def _enrich_with_dictionary(self, candidates: List[Dict], text: str) -> List[Dict]:
        """
        Layer 2: Dictionary-based validation and typing
        
        约束：
        - 不引入新的 span
        - 不扫描候选 span 之外的原始文本
        - 不删除候选
        - 不进行语法推理
        
        职责：
        - 为候选实体匹配词典
        - 设置 type 和 confidence
        - 附加 dictionary_hit 信息
        
        匹配规则：
        1. 精确匹配 canonical name（最高优先级）
        2. 精确匹配 alias
        3. Token-aligned 部分匹配（需要验证token边界）
        4. 单token匹配惩罚（降低confidence）
        
        Returns:
            Enriched candidates (不修改原列表，返回新列表)
        """
        enriched = []
        
        for candidate in candidates:
            # Create a copy to avoid modifying original
            enriched_candidate = candidate.copy()
            
            # Try dictionary matching
            match_result = self._match_dictionary(enriched_candidate)
            
            if match_result:
                # Set type from dictionary
                enriched_candidate["type"] = match_result["entry"]["type"]
                
                # Increase confidence based on match quality
                confidence_boost = self._calculate_confidence_boost(
                    match_result, enriched_candidate
                )
                enriched_candidate["confidence"] += confidence_boost
                
                # Set dictionary source flag
                enriched_candidate["source"]["dictionary"] = True
                
                # Attach dictionary hit metadata
                enriched_candidate["dictionary_hit"] = {
                    "dict": match_result["dict"],
                    "canonical": match_result["entry"]["canonical"],
                    "id": match_result["entry"]["id"],
                    "match_type": match_result["match_type"],
                    "matched_name": match_result["matched_name"]
                }
            
            enriched.append(enriched_candidate)
        
        return enriched
    
    def _match_dictionary(self, candidate: Dict) -> Optional[Dict]:
        """
        为候选实体匹配词典条目
        
        Returns:
            {
                "dict": str,           # player | coach | club | competition | stadium
                "entry": Dict,         # 完整词典条目
                "match_type": str,     # canonical | alias | partial | single_token
                "matched_name": str,   # 匹配到的名称
            }
            或 None（无匹配）
        """
        entity_text = candidate["text"]
        entity_text_lower = entity_text.lower()
        
        # 1. Exact match (canonical or alias)
        if entity_text_lower in self.dict_index["exact"]:
            matches = self.dict_index["exact"][entity_text_lower]
            
            # Prefer canonical match
            for match in matches:
                if match["is_canonical"]:
                    return {
                        "dict": match["dict"],
                        "entry": match["entry"],
                        "match_type": "canonical",
                        "matched_name": match["match_name"]
                    }
            
            # Fallback to alias match
            if matches:
                match = matches[0]
                return {
                    "dict": match["dict"],
                    "entry": match["entry"],
                    "match_type": "alias",
                    "matched_name": match["match_name"]
                }
        
        # 2. Partial match (token-aligned only)
        tokens = candidate.get("tokens", [])
        if tokens:
            partial_match = self._try_partial_match(entity_text, tokens)
            if partial_match:
                return partial_match
        
        return None
    
    def _try_partial_match(self, entity_text: str, tokens: List) -> Optional[Dict]:
        """
        尝试部分匹配（基于 token 对齐）
        
        约束：只匹配完整的 token 序列，不做子串匹配
        """
        entity_tokens = [t.text.lower() for t in tokens]
        
        # 单token情况：需要更严格的验证
        if len(entity_tokens) == 1:
            token = entity_tokens[0]
            if token in self.dict_index["tokens"]:
                candidates = self.dict_index["tokens"][token]
                
                # 只有当该token是某个条目的唯一标识时才匹配
                # 例如 "Arsenal" 可以单独匹配，但 "United" 太模糊
                valid_candidates = [
                    c for c in candidates
                    if c["full_name"].lower().split() == [token]  # 单token名称
                    or c["is_canonical"]  # 或者是canonical的一部分
                ]
                
                if len(valid_candidates) == 1:
                    match = valid_candidates[0]
                    return {
                        "dict": match["dict"],
                        "entry": match["entry"],
                        "match_type": "single_token",
                        "matched_name": match["full_name"]
                    }
        
        # 多token情况：尝试匹配完整的名称
        # 检查是否有词典条目的所有tokens都在候选中
        for token in entity_tokens:
            if token not in self.dict_index["tokens"]:
                continue
            
            for match_candidate in self.dict_index["tokens"][token]:
                dict_tokens = match_candidate["full_name"].lower().split()
                
                # 检查所有词典tokens是否都在候选tokens中（顺序一致）
                if self._tokens_aligned(entity_tokens, dict_tokens):
                    return {
                        "dict": match_candidate["dict"],
                        "entry": match_candidate["entry"],
                        "match_type": "partial",
                        "matched_name": match_candidate["full_name"]
                    }
        
        return None
    
    def _tokens_aligned(self, candidate_tokens: List[str], dict_tokens: List[str]) -> bool:
        """
        检查词典tokens是否与候选tokens对齐（保持顺序）
        
        Example:
            candidate: ["crystal", "palace"]
            dict: ["palace"]
            → False (不完整)
            
            candidate: ["crystal", "palace"]
            dict: ["crystal", "palace"]
            → True
        """
        # 词典tokens必须是候选tokens的连续子序列
        if len(dict_tokens) > len(candidate_tokens):
            return False
        
        # 尝试找到匹配的起始位置
        for i in range(len(candidate_tokens) - len(dict_tokens) + 1):
            if candidate_tokens[i:i+len(dict_tokens)] == dict_tokens:
                # 必须是完整匹配（不能是候选的一部分）
                return len(dict_tokens) == len(candidate_tokens)
        
        return False
    
    def _calculate_confidence_boost(self, match_result: Dict, candidate: Dict) -> float:
        """
        根据匹配质量计算confidence提升
        
        规则：
        - canonical match: +0.4
        - alias match: +0.3
        - partial match: +0.2
        - single_token ambiguous: +0.1
        """
        match_type = match_result["match_type"]
        
        if match_type == "canonical":
            return 0.4
        elif match_type == "alias":
            return 0.3
        elif match_type == "partial":
            return 0.2
        elif match_type == "single_token":
            # 单token匹配给予较低confidence
            return 0.15
        
        return 0.0
        for club_name, metadata in self.club_dict.items():
            if text in metadata.get("aliases", []):
                return True
        
        return 0.0
    
    # ========================================================================
    # Layer 3: Syntax & Context Reasoning (Role Disambiguation)
    # ========================================================================
    
    def _apply_syntax_reasoning(self, candidates: List[Dict], doc: Doc) -> List[Dict]:
        """
        Layer 3: 使用语法和上下文推理最终角色
        
        职责：基于依存句法做角色消歧
        优先级：Dictionary > Syntax > NER Label
        
        核心规则：
        1. 如果 Layer 2 已通过词典确定类型，直接采纳（除非语法有强否定）
        2. Coach 识别：PERSON + poss → team-like noun
        3. Player 识别：PERSON + match action verb (nsubj/agent/pobj)
        4. Tournament 识别：结构化模式（Cup/League + 修饰语）
        """
        final_entities = []
        
        for candidate in candidates:
            # Dictionary已确定类型，直接采纳
            if candidate.get("dictionary_hit"):
                dict_type = candidate["dictionary_hit"]["dict"]
                
                # 特殊情况：如果词典说是 player，但语法强烈指示 coach，则覆盖
                if dict_type == "player" and candidate["ner_label"] == "PERSON":
                    tokens = candidate.get("tokens", [])
                    if tokens:
                        head_token = tokens[-1]
                        if self._is_coach_by_possession(head_token):
                            # 语法覆盖词典
                            candidate["type"] = EntityType.COACH
                            candidate["confidence"] += 0.2  # 额外奖励
                            candidate["source"]["syntax"] = True
                            final_entities.append(candidate)
                            continue
                
                # 其他情况：直接使用词典类型
                final_entities.append(candidate)
                continue
            
            # Dictionary未确定类型，使用语法推理
            
            # Skip if already determined (Club/Tournament/Stadium)
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
                    # No syntax rule matched
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
