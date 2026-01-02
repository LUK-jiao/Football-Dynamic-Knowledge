"""
Football Event Taxonomy and Trigger Dictionary

This module defines the complete event classification system for football news,
including event types, trigger words, patterns, and detection rules.

Design Principles:
1. Events must be mutually exclusive at the top level
2. Each event must be independently recognizable
3. Triggers are ordered by confidence (specific → general)
4. Patterns use regex for robustness
"""

from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import re


class EventType(Enum):
    """
    Top-level event classification for football news.
    
    Each type represents a distinct, independently modelable event
    that can be directly mapped to knowledge graph entities/relations.
    """
    
    # ==================== Core Match Events ====================
    MATCH_RESULT = "match_result"              # 比赛最终结果
    GOAL = "goal"                              # 进球事件
    ASSIST = "assist"                          # 助攻事件
    PENALTY_SHOOTOUT = "penalty_shootout"      # 点球大战
    PENALTY_AWARD = "penalty_award"            # 点球判罚
    OWN_GOAL = "own_goal"                      # 乌龙球
    SAVE = "save"                              # 扑救
    MISS = "miss"                              # 射失
    
    # ==================== Disciplinary Events ====================
    YELLOW_CARD = "yellow_card"                # 黄牌
    RED_CARD = "red_card"                      # 红牌
    VAR_DECISION = "var_decision"              # VAR判罚
    
    # ==================== Team Events ====================
    SUBSTITUTION = "substitution"              # 换人
    TACTICAL_CHANGE = "tactical_change"        # 战术调整
    FORMATION_CHANGE = "formation_change"      # 阵型变化
    
    # ==================== Player Events ====================
    INJURY = "injury"                          # 伤病
    RETURN_FROM_INJURY = "return_from_injury"  # 伤愈复出
    DEBUT = "debut"                            # 首秀/首发
    MILESTONE = "milestone"                    # 里程碑（百场、百球等）
    
    # ==================== Competition Events ====================
    FIXTURE = "fixture"                        # 赛程安排
    QUALIFICATION = "qualification"            # 晋级/出线
    ELIMINATION = "elimination"                # 淘汰
    DRAW_CEREMONY = "draw_ceremony"            # 抽签
    
    # ==================== Transfer & Contract ====================
    TRANSFER = "transfer"                      # 转会
    CONTRACT_EXTENSION = "contract_extension"  # 续约
    LOAN = "loan"                              # 租借
    
    # ==================== Quotes & Statements ====================
    MANAGER_QUOTE = "manager_quote"            # 主帅发言
    PLAYER_QUOTE = "player_quote"              # 球员发言
    OFFICIAL_STATEMENT = "official_statement"  # 官方声明
    
    # ==================== Statistics & Records ====================
    STATISTIC = "statistic"                    # 统计数据
    RECORD_BREAK = "record_break"              # 破纪录
    HISTORICAL_COMPARISON = "historical_comparison"  # 历史对比
    
    # ==================== Meta Events ====================
    MATCH_PREVIEW = "match_preview"            # 赛前预测
    MATCH_REVIEW = "match_review"              # 赛后总结
    CONTEXT_BACKGROUND = "context_background"  # 背景信息
    GENERAL_NARRATIVE = "general_narrative"    # 一般叙述


@dataclass
class EventTrigger:
    """
    Event detection trigger configuration.
    
    Attributes:
        verbs: Action verbs that strongly indicate this event
        nouns: Key nouns associated with this event
        keywords: Important keywords/phrases
        patterns: Regex patterns for detection
        entity_types: Expected entity types (for validation)
        confidence_boost: Patterns that increase confidence
    """
    verbs: Set[str] = None
    nouns: Set[str] = None
    keywords: Set[str] = None
    patterns: List[str] = None
    entity_types: Set[str] = None
    confidence_boost: List[str] = None
    
    def __post_init__(self):
        """Initialize empty sets for None values."""
        if self.verbs is None:
            self.verbs = set()
        if self.nouns is None:
            self.nouns = set()
        if self.keywords is None:
            self.keywords = set()
        if self.patterns is None:
            self.patterns = []
        if self.entity_types is None:
            self.entity_types = set()
        if self.confidence_boost is None:
            self.confidence_boost = []


# ============================================================================
# Event Trigger Dictionary
# ============================================================================

EVENT_TRIGGERS: Dict[EventType, EventTrigger] = {
    
    # ==================== MATCH_RESULT ====================
    EventType.MATCH_RESULT: EventTrigger(
        verbs={
            'won', 'lost', 'drew', 'beat', 'defeated', 'thrashed', 'hammered',
            'edged', 'cruised', 'triumphed', 'prevailed', 'succumbed',
            'advanced', 'progressed', 'marched on'
        },
        nouns={
            'victory', 'defeat', 'win', 'loss', 'draw', 'triumph', 'result'
        },
        patterns=[
            r'\b\d+-\d+\b',                    # 比分: 3-2, 1-1
            r'\bby \d+-\d+\b',                 # by 3-2
            r'\bon penalties\b',               # 点球大战胜
            r'\bon aggregate\b',               # 总比分
            r'\bafter extra time\b',           # 加时赛后
            r'\b\d+-\d+ on penalties\b',       # 点球比分
            r'\bwon.*\d+-\d+\b',              # won 3-2
        ],
        entity_types={'TEAM', 'SCORE', 'COMPETITION'},
        confidence_boost=[
            r'\bfinal score\b',
            r'\bfull.*time\b',
            r'\bthe (match|game) ended\b'
        ]
    ),
    
    # ==================== GOAL ====================
    EventType.GOAL: EventTrigger(
        verbs={
            'scored', 'netted', 'converted', 'slotted', 'fired', 'struck',
            'tapped', 'headed', 'volleyed', 'curled', 'smashed', 'drilled',
            'found the net', 'put.*away', 'made it'
        },
        nouns={
            'goal', 'strike', 'effort', 'finish', 'header', 'volley',
            'shot', 'equaliser', 'equalizer', 'opener', 'winner', 'brace'
        },
        patterns=[
            r'\bin the \d+th minute\b',        # in the 45th minute
            r'\bto make it \d+-\d+\b',        # to make it 2-1
            r'\bfrom \d+ yards\b',            # from 25 yards
            r'\binto the (net|corner)\b',     # into the net
            r'\bpast the keeper\b',           # past the keeper
            r'\b(first|second|third) goal\b', # first goal
            r'\bopening goal\b',              # opening goal
            r'\bequalising goal\b',           # equalising goal
            r'\bwinning goal\b',              # winning goal
        ],
        entity_types={'PLAYER', 'TEAM', 'TIME', 'SCORE'},
        confidence_boost=[
            r'\bgoal.*scored\b',
            r'\bfound.*back.*net\b',
            r'\bbulged.*net\b'
        ]
    ),
    
    # ==================== ASSIST ====================
    EventType.ASSIST: EventTrigger(
        verbs={
            'assisted', 'set up', 'provided', 'delivered', 'crossed',
            'passed', 'fed', 'squared', 'teed up'
        },
        nouns={
            'assist', 'cross', 'pass', 'delivery', 'ball', 'through-ball'
        },
        patterns=[
            r'\bassist from\b',
            r'\bset up by\b',
            r'\bcross from\b',
            r'\bpass from\b',
            r'\bdelivery (from|by)\b',
            r'\bfound (by|the head of)\b'
        ],
        entity_types={'PLAYER', 'PLAYER'},  # Assister + Scorer
    ),
    
    # ==================== PENALTY_SHOOTOUT ====================
    EventType.PENALTY_SHOOTOUT: EventTrigger(
        verbs={
            'won', 'lost', 'settled', 'decided'
        },
        keywords={
            'penalty shootout', 'penalty shoot-out', 'shootout',
            'spot-kicks', 'from the spot'
        },
        patterns=[
            r'\bpenalty (shootout|shoot-out)\b',
            r'\b\d+-\d+ on penalties\b',
            r'\bwon.*penalties\b',
            r'\bspot.*kicks\b',
            r'\b(converted|missed).*penalty\b',
            r'\bsaved.*penalty\b',
        ],
        entity_types={'TEAM', 'SCORE', 'PLAYER'},
    ),
    
    # ==================== PENALTY_AWARD ====================
    EventType.PENALTY_AWARD: EventTrigger(
        verbs={
            'awarded', 'given', 'conceded', 'won'
        },
        keywords={
            'penalty', 'spot kick', 'from the spot'
        },
        patterns=[
            r'\bawarded.*penalty\b',
            r'\bpenalty.*awarded\b',
            r'\bgiven.*penalty\b',
            r'\bconceded.*penalty\b',
            r'\bwon.*penalty\b',
            r'\bfrom the spot\b',
        ],
        entity_types={'TEAM', 'PLAYER', 'REFEREE'},
    ),
    
    # ==================== OWN_GOAL ====================
    EventType.OWN_GOAL: EventTrigger(
        keywords={
            'own goal', 'own-goal', 'unfortunate', 'deflection'
        },
        patterns=[
            r'\bown goal\b',
            r'\bown-goal\b',
            r'\boff.*own player\b',
            r'\binto.*own net\b',
            r'\bunfortunate.*deflection\b',
        ],
        entity_types={'PLAYER', 'TEAM'},
    ),
    
    # ==================== SAVE ====================
    EventType.SAVE: EventTrigger(
        verbs={
            'saved', 'denied', 'parried', 'tipped', 'kept out',
            'pushed away', 'stopped'
        },
        nouns={
            'save', 'stop', 'intervention', 'reflex'
        },
        patterns=[
            r'\bsaved.*shot\b',
            r'\bkept.*out\b',
            r'\bdenied\b',
            r'\bgreat save\b',
            r'\b(keeper|goalkeeper).*saved\b',
        ],
        entity_types={'PLAYER', 'POSITION'},  # Goalkeeper
    ),
    
    # ==================== SUBSTITUTION ====================
    EventType.SUBSTITUTION: EventTrigger(
        verbs={
            'substituted', 'replaced', 'came on', 'introduced',
            'brought on', 'came off', 'withdrawn'
        },
        keywords={
            'substitution', 'change', 'sub', 'replaced'
        },
        patterns=[
            r'\bcame on for\b',
            r'\breplaced by\b',
            r'\bbrought on\b',
            r'\bintroduced.*for\b',
            r'\bwithdrawn.*replaced\b',
            r'\bin the \d+th minute\b.*\b(on|off)\b',
        ],
        entity_types={'PLAYER', 'PLAYER', 'TIME'},
    ),
    
    # ==================== INJURY ====================
    EventType.INJURY: EventTrigger(
        verbs={
            'injured', 'suffered', 'picked up', 'sustained', 'ruled out',
            'sidelined', 'limped off', 'carried off'
        },
        nouns={
            'injury', 'problem', 'issue', 'concern', 'knock', 'strain',
            'tear', 'hamstring', 'ankle', 'knee', 'muscle'
        },
        patterns=[
            r'\bsuffered.*injury\b',
            r'\bpicked up.*(injury|knock)\b',
            r'\bruled out\b',
            r'\bsidelined\b',
            r'\blimped off\b',
            r'\bcarried off\b',
            r'\b(hamstring|ankle|knee|muscle).*(injury|problem)\b',
        ],
        entity_types={'PLAYER', 'INJURY_TYPE', 'TIME'},
    ),
    
    # ==================== DEBUT ====================
    EventType.DEBUT: EventTrigger(
        keywords={
            'debut', 'first appearance', 'first start', 'first game',
            'bow', 'inaugural'
        },
        patterns=[
            r'\bmade.*debut\b',
            r'\bdebut.*for\b',
            r'\bfirst (appearance|start|game)\b',
            r'\bmade.*first.*appearance\b',
        ],
        entity_types={'PLAYER', 'TEAM', 'COMPETITION'},
    ),
    
    # ==================== MILESTONE ====================
    EventType.MILESTONE: EventTrigger(
        patterns=[
            r'\b\d+(th|st|nd|rd) (appearance|goal|game|cap)\b',  # 100th appearance
            r'\blandmark\b',
            r'\bmilestone\b',
            r'\brecord.*\d+\b',
            r'\bcentury\b',  # century of goals/games
            r'\b\d+ goals? for\b',
        ],
        keywords={
            'milestone', 'landmark', 'century', 'record'
        },
        entity_types={'PLAYER', 'NUMBER', 'ACHIEVEMENT'},
    ),
    
    # ==================== FIXTURE ====================
    EventType.FIXTURE: EventTrigger(
        verbs={
            'will face', 'will play', 'will meet', 'face', 'play',
            'meet', 'host', 'visit', 'travel to', 'take on'
        },
        patterns=[
            r'\bwill (face|play|meet|host)\b',
            r'\bnext (game|match|round|week|month)\b',
            r'\bin the (semi-final|final|quarter-final)\b',
            r'\b(home|away) to\b',
            r'\bat (home|away)\b',
            r'\bscheduled for\b',
            r'\bon \w+day\b',  # on Tuesday
            r'\b\d{1,2} (January|February|March|etc)\b',
        ],
        entity_types={'TEAM', 'TEAM', 'DATE', 'VENUE', 'COMPETITION'},
        confidence_boost=[
            r'\bnext.*opponent\b',
            r'\bfirst leg\b',
            r'\bsecond leg\b'
        ]
    ),
    
    # ==================== QUALIFICATION ====================
    EventType.QUALIFICATION: EventTrigger(
        verbs={
            'qualified', 'advanced', 'progressed', 'reached', 'booked',
            'secured', 'clinched', 'earned'
        },
        keywords={
            'qualification', 'qualify', 'progress', 'advance', 'through'
        },
        patterns=[
            r'\bqualified for\b',
            r'\badvanced to\b',
            r'\bprogressed to\b',
            r'\breached the\b',
            r'\bbooked.*place\b',
            r'\bsecured.*spot\b',
            r'\bclinched.*berth\b',
        ],
        entity_types={'TEAM', 'COMPETITION', 'ROUND'},
    ),
    
    # ==================== ELIMINATION ====================
    EventType.ELIMINATION: EventTrigger(
        verbs={
            'eliminated', 'knocked out', 'crashed out', 'exited',
            'bowed out'
        },
        keywords={
            'elimination', 'exit', 'out of'
        },
        patterns=[
            r'\beliminated (from|by)\b',
            r'\bknocked out\b',
            r'\bcrashed out\b',
            r'\bbowed out\b',
            r'\bout of.*competition\b',
        ],
        entity_types={'TEAM', 'COMPETITION', 'ROUND'},
    ),
    
    # ==================== MANAGER_QUOTE ====================
    EventType.MANAGER_QUOTE: EventTrigger(
        verbs={
            'said', 'told', 'admitted', 'claimed', 'stated', 'insisted',
            'explained', 'revealed', 'confirmed', 'praised', 'criticized'
        },
        patterns=[
            r'\b(manager|boss|coach|gaffer)\b.*\bsaid\b',
            r'\bsaid\b.*\b(after|before).*\b(match|game)\b',
            r':\s*["\']',  # Name: "quote"
            r'\btold.*reporters\b',
            r'\bin.*interview\b',
            r'\bspeaking to\b',
        ],
        entity_types={'PERSON', 'ROLE'},
        confidence_boost=[
            r'\b(Arteta|Guardiola|Klopp|Ancelotti)\b',  # Common managers
        ]
    ),
    
    # ==================== PLAYER_QUOTE ====================
    EventType.PLAYER_QUOTE: EventTrigger(
        verbs={
            'said', 'told', 'admitted', 'claimed', 'stated', 'revealed'
        },
        patterns=[
            r'\bplayer\b.*\bsaid\b',
            r'\bsaid\b.*\bafter.*\b(scoring|game)\b',
            r'\b(striker|midfielder|defender|goalkeeper)\b.*\bsaid\b',
        ],
        entity_types={'PLAYER', 'POSITION'},
    ),
    
    # ==================== STATISTIC ====================
    EventType.STATISTIC: EventTrigger(
        patterns=[
            r'\b\d+(\.\d+)?%\b',               # 48.3%
            r'\b\d+ of \d+\b',                 # 8 of 15
            r'\b\d+ (shots|passes|tackles)\b', # 12 shots
            r'\bpossession.*\d+%\b',           # possession 65%
            r'\bconversion rate\b',
            r'\baccuracy\b',
        ],
        keywords={
            'statistic', 'stats', 'percentage', 'possession',
            'shots', 'passes', 'accuracy', 'rate'
        },
        entity_types={'NUMBER', 'STAT_TYPE'},
    ),
    
    # ==================== RECORD_BREAK ====================
    EventType.RECORD_BREAK: EventTrigger(
        verbs={
            'broke', 'set', 'equalled', 'surpassed', 'overtook'
        },
        keywords={
            'record', 'historic', 'all-time', 'best', 'first time'
        },
        patterns=[
            r'\bbroke.*record\b',
            r'\bset.*record\b',
            r'\b(first|only).*ever\b',
            r'\ball-time\b',
            r'\bhistoric\b',
            r'\bsurpassed\b',
        ],
        entity_types={'PLAYER', 'RECORD_TYPE', 'NUMBER'},
    ),
    
    # ==================== VAR_DECISION ====================
    EventType.VAR_DECISION: EventTrigger(
        keywords={
            'VAR', 'video assistant', 'review', 'overturned', 'checked'
        },
        patterns=[
            r'\bVAR\b',
            r'\bvideo assistant\b',
            r'\bafter.*review\b',
            r'\boverturned\b',
            r'\bVAR check\b',
        ],
        entity_types={'DECISION', 'REFEREE'},
    ),
}


# ============================================================================
# Dependency Markers
# ============================================================================

class DependencyMarkers:
    """
    Markers that indicate a sentence is dependent on previous context.
    """
    
    # Pronouns that signal anaphoric reference
    ANAPHORIC_PRONOUNS = {
        'this', 'that', 'these', 'those',
        'it', 'they', 'them', 'he', 'she', 'his', 'her', 'their'
    }
    
    # Temporal continuations
    TEMPORAL_CONTINUATIONS = {
        'when', 'after', 'before', 'as', 'while', 'since',
        'following', 'subsequently', 'then', 'later'
    }
    
    # Elaboration markers
    ELABORATION_MARKERS = {
        'the', 'a', 'an',  # When sentence lacks strong verb
        'overall', 'in total', 'altogether'
    }
    
    # Causal/result markers (can be both independent and dependent)
    CAUSAL_MARKERS = {
        'because', 'as', 'since', 'therefore', 'thus', 'so'
    }
    
    # Contrast markers (usually start new block)
    CONTRAST_MARKERS = {
        'however', 'but', 'nevertheless', 'nonetheless',
        'on the other hand', 'in contrast', 'conversely'
    }


# ============================================================================
# Event Compatibility Rules
# ============================================================================

# Defines which event types can co-occur in the same semantic block.
# Key principle: Events should be temporally and causally related.
EVENT_COMPATIBILITY: Dict[EventType, Set[EventType]] = {
    EventType.GOAL: {
        EventType.ASSIST,  # Goals often have assists
        EventType.STATISTIC,  # Goal + stats (e.g., "his 10th goal")
        EventType.MILESTONE,  # Goal achieving milestone
    },
    
    EventType.PENALTY_SHOOTOUT: {
        EventType.SAVE,  # Saves in shootout
        EventType.MISS,  # Misses in shootout
        EventType.PENALTY_AWARD,  # How penalties were earned
    },
    
    EventType.MATCH_RESULT: {
        EventType.STATISTIC,  # Result + possession stats
        EventType.GOAL,  # Result + how goals were scored (borderline)
    },
    
    EventType.MANAGER_QUOTE: {
        EventType.MANAGER_QUOTE,  # Multiple quote sentences from same person
    },
    
    EventType.PLAYER_QUOTE: {
        EventType.PLAYER_QUOTE,  # Multiple quote sentences from same person
    },
    
    EventType.INJURY: {
        EventType.SUBSTITUTION,  # Injury led to substitution
    },
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_event_triggers(event_type: EventType) -> EventTrigger:
    """Get trigger configuration for an event type."""
    return EVENT_TRIGGERS.get(event_type, EventTrigger())


def is_compatible_event(event1: EventType, event2: EventType) -> bool:
    """Check if two event types can co-occur in same block."""
    if event1 == event2:
        return True
    
    compatible_set = EVENT_COMPATIBILITY.get(event1, set())
    return event2 in compatible_set


def get_all_event_types() -> List[EventType]:
    """Get list of all event types."""
    return list(EventType)


def get_dependency_markers() -> DependencyMarkers:
    """Get dependency marker configuration."""
    return DependencyMarkers()
