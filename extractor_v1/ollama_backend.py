"""
Ollama Backend for Football Event Anchor Extraction

使用 Ollama 本地大模型从足球新闻语义块中抽取事实锚点。
严格遵循 Event vs State 判定规范。
"""

import json
from typing import Dict, Any, Optional
import ollama

SYSTEM_PROMPT = """You are a FOOTBALL EVENT EXTRACTION AGENT.

Your task is to extract structured data for ONE football event.

You are performing STRICT INFORMATION EXTRACTION.

You must:
- Use ONLY the provided input fields.
- Use ONLY event_description as the primary source.
- NOT use external knowledge.
- NOT infer missing facts.
- NOT create new categories.
- NOT enrich beyond the text.

If information is not explicitly supported,
leave the field empty or null.

==================================================
PRIMARY SOURCE PRIORITY
==================================================

1) event_description (authoritative)
2) block_text (only to clarify incomplete names already mentioned)

You MUST NOT:
- Extract entities only from title_anchors
- Infer teams, competitions, or dates
- Assume contextual football knowledge

==================================================
OUTPUT STRUCTURE
==================================================

Return VALID JSON only.
No explanations.
No markdown.
No comments.

All top-level fields MUST exist.
Arrays MAY be empty.

{
  "event_id": string,
  "title_anchors": [...],
  "event_description": string,
  "participants": [
    {
      "type": "Person" | "Club" | "NationalTeam" | "Competition" | "Stadium",
      "name": string
    }
  ],
  "fact_type": "EVENT" | "STATE",
  "constraints": [
    { "type": string }
  ],
  "temporal_anchors": [
    {
      "event_date": string | null,
      "valid_from": string | null,
      "valid_to": string | null
    }
  ],
  "sources": [
    {
      "type": string,
      "source": string,
      "publish_date": string
    }
  ]
}

==================================================
PARTICIPANTS
==================================================

Extract ONLY named entities that appear explicitly
in event_description.

Do NOT:
- Add entities from title_anchors
- Add implied clubs
- Guess missing names
- Expand abbreviations unless explicitly written

If no named entities appear → return [].

==================================================
FACT_TYPE
==================================================

EVENT:
- Instantaneous actions
  (goal, save, transfer, appointment, win, signing)

STATE:
- Explicit ongoing condition
  (injured, suspended, under contract, banned)

If unclear → default to EVENT.

==================================================
CONSTRAINTS (MANDATORY MACRO CATEGORY)
==================================================

Each event MUST include at least ONE constraint type.

constraints array MUST NOT be empty.

You may ONLY use one or more of the following 9 types.
Spelling must match EXACTLY.
No variations allowed.
No new categories allowed.

Allowed constraint types:

1. MATCH_ACTION
2. MATCH_OUTCOME
3. MATCH_CONTEXT
4. PLAYER_MOVEMENT
5. CONTRACT_EVENT
6. AVAILABILITY_EVENT
7. APPOINTMENT_EVENT
8. PERFORMANCE_EVENT
9. ADMINISTRATIVE_EVENT

Rules:
- constraints MUST contain at least one type.
- If uncertain, choose the closest macro category.
- Multiple types allowed when logically justified.
- Do NOT duplicate identical types.
- Do NOT invent subtypes.

Every football-related event must logically belong to at least one macro category.

==================================================
TEMPORAL_ANCHORS
==================================================

Temporal information must be extracted ONLY
from event_description.

All dates MUST be normalized to ISO 8601 format.

Allowed formats:
- YYYY
- YYYY-MM
- YYYY-MM-DD

STRICT RULES:

- No natural language dates.
- No relative expressions (yesterday, last week).
- No time-of-day.
- No timezones.
- No duration calculations.
- Do NOT use publish_date as fallback.
- Do NOT infer contract end dates.

If a date cannot be safely normalized → null.

For EVENT:
- event_date = explicit normalized date if present
- valid_from = null
- valid_to = null

For STATE:
- event_date = null
- valid_from = explicit normalized start date if present
- valid_to = explicit normalized end date if present

If no explicit time information appears:
Return exactly one temporal_anchors object
with all fields set to null.

==================================================
SOURCES
==================================================

You MUST include exactly one source object.

The "type" field MUST be one of:

1. OFFICIAL
2. MEDIA
3. USER_GENERATED
4. UNKNOWN

Definitions:

OFFICIAL:
- Official club website
- Official league website
- Official federation/association
- Official announcement

MEDIA:
- Professional news outlet
- Sports media
- News agency
- Professional journalist reporting

USER_GENERATED:
- Blog
- Forum
- Social media post
- Unverified account
- Independent creator

UNKNOWN:
- Source type cannot be determined

Rules:

- Use ONLY one of the four values.
- Do NOT invent new categories.
- Copy the input source name exactly into "source".
- Copy publish_date exactly as given.
- Do NOT modify publish_date format.

==================================================
STRICT OUTPUT RULES
==================================================

- Copy event_id exactly.
- Copy title_anchors exactly.
- Copy event_description exactly.
- Do NOT summarize.
- Do NOT rephrase.
- Do NOT add extra fields.
- JSON only.

"""

# ============================================================================
# Developer Prompt - 针对单个 event 的动态提示
# ============================================================================

DEVELOPER_PROMPT = """Input Event:
Event ID: {event_id}
Title Anchors: {title_anchors}
Event Description: {event_description}
Source: {source}
Publish Date: {publish_date}

(Block Text for reference: {block_text})

Output JSON (extract anchors from event_description, fact_type required):
"""


# ============================================================================
# Event Decomposition Prompts (事件分解层)
# ============================================================================

EVENT_DECOMPOSITION_SYSTEM_PROMPT = """You are a FOOTBALL EVENT DECOMPOSITION AGENT.

Your task is to convert a football-related semantic block into 1–N structured event units.

This module is DOMAIN-GENERIC.
It must work for:

transfers

matches

goals

contracts

injuries

suspensions

managerial appointments

official statements

regulatory decisions

==================================================
INPUT

You will receive:

block_id

title

text (original semantic block)

source

publish_date

==================================================
OUTPUT JSON SCHEMA (STRICT)

{
  "events": [
    {
      "event_id": "string",
      "title_anchors": "string",
      "event_description": "string",
      "block_text": "string",
      "source": "string",
      "publish_date": "string"
    }
  ]
}

==================================================
MODULE RESPONSIBILITY (BOUNDARY)

This module ONLY does:

event splitting

event semantic compression (event_description generation)

title-based contextual anchoring

This module MUST NOT do:

parent–child modeling

time normalization

state judgment

constraint extraction

entity normalization

inference beyond explicit text

==================================================
CORE PRINCIPLE

You are an INDEXING LAYER, not a FACT REASONER.

Each event_description must be:

strictly grounded in explicit text

self-contained

NER-extractable

suitable as the primary input for downstream modules

==================================================
1️⃣ EVENT SPLITTING RULES

One semantic block can produce 1 to N events.

Each event represents ONE clear football-related fact or action.

Split events ONLY when:

actions are logically independent, OR

multiple distinct football facts are stated.

If the block describes a single fact → produce ONE event.
If uncertain → DO NOT split.

==================================================
2️⃣ TITLE_ANCHORS RULE

title_anchors MUST be derived from the provided title.

It represents the minimal contextual scope of the block.

It must be concise (not a sentence).

It should typically contain:

team names

competition

transfer context

player name

event type

Examples:

"Arsenal vs Crystal Palace EFL Cup quarter-final"

"De Ligt transfer to Manchester United"

"Chelsea managerial appointment"

"FA disciplinary decision"

Do NOT generate narrative phrases.
Do NOT repeat the full title verbatim if it is long.

==================================================
3️⃣ EVENT_DESCRIPTION RULES (CRITICAL)

event_description MUST:

Be exactly ONE sentence

Be concise and information-dense

Explicitly contain named entities

Clearly state WHAT happened and WHO was involved

Preserve explicit facts only

event_description MAY include:

time expressions (as text, not normalized)

scores

competition names

locations

event_description MUST NOT:

add interpretation

add emotional tone

introduce future implications

summarize the entire block

infer unstated facts

include vague wording

Good examples:

"Marc Guehi scored an equaliser in stoppage time"

"Manchester United signed Matthijs de Ligt from Bayern Munich"

"Arsenal defeated Crystal Palace 8-7 on penalties"

"Chelsea appointed a new head coach"

Bad examples:

"A dramatic moment followed"

"This secured qualification"

"The team showed resilience"

"The match ended in excitement"

The description must be NER-ready:
A downstream system should be able to extract:

PERSON

CLUB

COMPETITION

ACTION TYPE

==================================================
4️⃣ BLOCK_TEXT RULE

block_text MUST be the FULL original input text

Do NOT modify, summarize, or partially copy

All events share the same block_text

==================================================
5️⃣ EVENT_ID RULE

Use sequential numbering:
"{block_id}-1"
"{block_id}-2"
"{block_id}-3"
...

No nesting.

==================================================
FORBIDDEN ACTIONS

❌ No comments
❌ No explanations
❌ No placeholder values
❌ No markdown

==================================================
OUTPUT HARD CONSTRAINTS (ABSOLUTE)

Output ONLY valid JSON

No prefix text

No suffix text

No commentary

No markdown

JSON must be directly parseable

==================================================
FINAL INSTRUCTION

Return ONLY the JSON object.
Nothing else.
"""

EVENT_DECOMPOSITION_DEVELOPER_PROMPT = """Input:
Block ID: {block_id}
Title: {title}
Source: {source}
Publish Date: {publish_date}
Text: {text}

Output JSON (array of events):
"""


# ============================================================================
# Ollama Backend Class
# ============================================================================

class OllamaBackend:
    """
    Ollama 后端封装类，负责与 Ollama LLM 通信。
    
    职责：
    1. 构建两段式 Prompt（System + Developer）
    2. 调用 Ollama API
    3. 解析 JSON 响应
    4. 不做任何后处理和字段修正
    """
    
    def __init__(
        self, 
        model: str = "gemma3:12b",
        host: str = "http://localhost:11434"
    ):
        """
        初始化 Ollama 后端
        
        Args:
            model: Ollama 模型名称（如 "llama3.2:latest", "mistral", "qwen"）
            host: Ollama 服务地址
        """
        self.model = model
        self.host = host
        
    def _build_messages(self, event: Dict[str, Any]) -> list:
        """
        构建两段式 Prompt 消息列表
        
        Args:
            event: 输入的事件（包含 event_id, title_anchors, event_description, block_text, source, publish_date）
            
        Returns:
            消息列表 [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        # System Message
        system_message = {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
        
        # Developer Message（填充 event 数据）
        developer_content = DEVELOPER_PROMPT.format(
            event_id=event.get("event_id", "N/A"),
            title_anchors=event.get("title_anchors", "N/A"),
            event_description=event.get("event_description", ""),
            block_text=event.get("block_text", "")[:200] + "...",  # 只显示前200字符作为参考
            source=event.get("source", "N/A"),
            publish_date=event.get("publish_date", "N/A")
        )
        
        developer_message = {
            "role": "user",
            "content": developer_content
        }
        
        return [system_message, developer_message]
    
    def _call_ollama(self, messages: list) -> str:
        """
        调用 Ollama API
        
        Args:
            messages: 消息列表
            
        Returns:
            模型的原始响应文本
            
        Raises:
            RuntimeError: API 调用失败
        """
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.05,   # 极低温度，保证输出一致性和稳定性
                    "num_predict": 1500,   # 最大 token 数
                    "num_ctx": 4096,       # 上下文窗口
                    "top_p": 0.85,         # nucleus sampling，更保守的采样
                    "repeat_penalty": 1.15 # 更强的重复惩罚
                }
            )
            
            # 提取响应内容
            content = response.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Ollama 返回空响应")
            
            return content
            
        except Exception as e:
            raise RuntimeError(f"Ollama API 调用失败: {str(e)}")
    
    def _parse_json(self, raw_response: str) -> Dict[str, Any]:
        """
        解析模型返回的 JSON
        
        Args:
            raw_response: 模型的原始响应
            
        Returns:
            解析后的 dict
            
        Raises:
            ValueError: JSON 解析失败
        """
        # 清理可能的 markdown 代码块标记和前缀文字
        cleaned = raw_response.strip()
        
        # 移除 markdown 代码块
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # 尝试找到 JSON 对象的开始位置（寻找第一个 {）
        json_start = cleaned.find('{')
        if json_start > 0:
            # 如果 { 不在开头，说明前面有额外文字，去掉
            cleaned = cleaned[json_start:]
        
        # 尝试找到 JSON 对象的结束位置（寻找最后一个 }）
        json_end = cleaned.rfind('}')
        if json_end > 0 and json_end < len(cleaned) - 1:
            # 如果 } 不在结尾，说明后面有额外文字，去掉
            cleaned = cleaned[:json_end + 1]
        
        # 如果 JSON 不完整，尝试补全闭合括号
        open_braces = cleaned.count('{')
        close_braces = cleaned.count('}')
        if open_braces > close_braces:
            # 补全缺失的闭合括号
            cleaned += '}' * (open_braces - close_braces)
        
        # 解析 JSON
        try:
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {str(e)}\n原始响应:\n{raw_response}")
    
    def extract_anchors(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单个事件中抽取锚点（Anchor Extraction Layer）
        
        Args:
            event: 输入的事件，必须包含：
                - event_id: 事件唯一标识
                - title_anchors: 标题提炼（用于上下文理解）
                - event_description: 事件描述（PRIMARY NER SOURCE）
                - block_text: 原始文本块（参考用）
                - source: 信息来源
                - publish_date: 发布日期
            
        Returns:
            包含锚点的结果 dict（扁平化结构）：
            {
                "event_id": "...",
                "title_anchors": "...",
                "event_description": "...",
                "participants": [...],
                "fact_type": "EVENT|STATE",
                "constraints": [...],
                "temporal_anchors": [...],
                "sources": [...]
            }
        """
        # 验证输入
        required_fields = ["event_id", "event_description"]
        for field in required_fields:
            if field not in event:
                raise ValueError(f"Event 缺少必填字段: {field}")
        
        # 1. 构建消息
        messages = self._build_messages(event)
        
        # 2. 调用 LLM
        raw_response = self._call_ollama(messages)
        
        # 3. 解析 JSON
        result = self._parse_json(raw_response)
        
        # 4. 添加事件标识信息
        result["event_id"] = event.get("event_id")
        result["title_anchors"] = event.get("title_anchors", "N/A")
        
        # 5. 直接返回，不做任何后处理
        return result
    
    def chat(self, prompt: str, temperature: float = 0.3) -> str:
        """
        Simple chat interface for general queries.
        
        Args:
            prompt: User prompt
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Model response text
        """
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": temperature,
                    "num_predict": 2000,
                    "num_ctx": 8192
                }
            )
            
            content = response.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Ollama returned empty response")
            
            return content
            
        except Exception as e:
            raise RuntimeError(f"Ollama API call failed: {str(e)}")
    
    def decompose_events(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        将语义块分解为事件单元（Event Decomposition Layer）
        
        Args:
            block: 输入的语义块，必须包含：
                - block_id: 唯一标识
                - text: 原始文本
                - source: 信息来源
                - publish_date: 发布日期
                - title: 文章标题（可选）
        
        Returns:
            包含事件列表的结果 dict：
            {
                "events": [
                    {
                        "event_id": "...",
                        "title_anchors": "...",
                        "event_description": "...",
                        "block_text": "...",
                        "source": "...",
                        "publish_date": "..."
                    }
                ]
            }
        
        Raises:
            ValueError: 输入格式不正确或解析失败
        """
        # 验证输入
        required_fields = ["block_id", "text", "source", "publish_date"]
        for field in required_fields:
            if field not in block:
                raise ValueError(f"Block 缺少必填字段: {field}")
        
        # 1. 构建事件分解消息
        system_message = {
            "role": "system",
            "content": EVENT_DECOMPOSITION_SYSTEM_PROMPT
        }
        
        developer_content = EVENT_DECOMPOSITION_DEVELOPER_PROMPT.format(
            block_id=block.get("block_id", "N/A"),
            title=block.get("title", "N/A"),
            source=block.get("source", "N/A"),
            publish_date=block.get("publish_date", "N/A"),
            text=block.get("text", "")
        )
        
        developer_message = {
            "role": "user",
            "content": developer_content
        }
        
        messages = [system_message, developer_message]
        
        # 2. 调用 LLM
        raw_response = self._call_ollama(messages)
        
        # 3. 解析 JSON
        result = self._parse_json(raw_response)
        
        # 4. 验证输出格式
        if "events" not in result or not isinstance(result["events"], list):
            raise ValueError("Event decomposition output must contain 'events' array")
        
        # 5. 验证每个 event 的必填字段
        required_event_fields = ["event_id", "title_anchors", "event_description", 
                                 "block_text", "source", "publish_date"]
        for event in result["events"]:
            for field in required_event_fields:
                if field not in event:
                    raise ValueError(f"Event missing required field: {field}")
        
        return result


# ============================================================================
# 便捷函数（向后兼容）
# ============================================================================

def run_event_anchor_extraction(
    block: Dict[str, Any],
    model: str = "llama3.2:latest",
    host: str = "http://localhost:11434"
) -> Dict[str, Any]:
    """
    运行事件锚点抽取（便捷函数）
    
    Args:
        block: 输入的语义块
        model: Ollama 模型名称
        host: Ollama 服务地址
        
    Returns:
        包含锚点的结果 dict
    """
    backend = OllamaBackend(model=model, host=host)
    return backend.extract_anchors(block)


# ============================================================================
# Schema 验证（可选，用于调试）
# ============================================================================

def validate_schema(result: Dict[str, Any]) -> bool:
    """
    验证输出是否符合新的扁平化 Schema
    
    Args:
        result: 抽取结果
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "event_id", 
        "title_anchors", 
        "event_description",
        "participants", 
        "fact_type", 
        "constraints", 
        "temporal_anchors", 
        "sources"
    ]
    
    # 检查顶层字段
    for field in required_fields:
        if field not in result:
            print(f"❌ 缺少字段: {field}")
            return False
    
    # 检查数组类型字段
    array_fields = ["participants", "constraints", "temporal_anchors", "sources"]
    for field in array_fields:
        if not isinstance(result[field], list):
            print(f"❌ {field} 必须是数组类型")
            return False
    
    # 检查 fact_type
    if result["fact_type"] not in ["EVENT", "STATE"]:
        print(f"❌ fact_type 无效: {result['fact_type']}")
        return False
    
    # 检查 constraints 类型（如果非空）
    allowed_constraint_types = [
        "MATCH_ACTION",
        "MATCH_OUTCOME", 
        "MATCH_CONTEXT",
        "PLAYER_MOVEMENT",
        "CONTRACT_EVENT",
        "AVAILABILITY_EVENT",
        "APPOINTMENT_EVENT",
        "PERFORMANCE_EVENT",
        "ADMINISTRATIVE_EVENT"
    ]
    
    for constraint in result["constraints"]:
        if "type" not in constraint:
            print(f"❌ constraint 缺少 type 字段")
            return False
        if constraint["type"] not in allowed_constraint_types:
            print(f"⚠️  警告: constraint type 不在允许列表中: {constraint['type']}")
    
    # 检查 sources 格式
    for source in result["sources"]:
        if "type" not in source or "source" not in source or "publish_date" not in source:
            print(f"❌ source 缺少必需字段 (type, source, publish_date)")
            return False
        
        allowed_source_types = ["OFFICIAL", "MEDIA", "USER_GENERATED", "UNKNOWN"]
        if source["type"] not in allowed_source_types:
            print(f"❌ source type 无效: {source['type']}")
            return False
    
    print("✅ Schema 验证通过")
    return True


# ============================================================================
# 调试工具
# ============================================================================

def print_prompt(event: Dict[str, Any]):
    """
    打印完整的 Prompt（用于调试）
    
    Args:
        event: 输入的事件
    """
    backend = OllamaBackend()
    messages = backend._build_messages(event)
    
    print("=" * 100)
    print("SYSTEM PROMPT")
    print("=" * 100)
    print(messages[0]["content"])
    print()
    print("=" * 100)
    print("DEVELOPER PROMPT")
    print("=" * 100)
    print(messages[1]["content"])
    print()


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    # 测试 Block
    test_block = {
        "block_id": "test_001",
        "text": "De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
        "source": "BBC Sport",
        "publish_date": "2025-08-23"
    }
    
    print("📋 测试 Block:")
    print(json.dumps(test_block, indent=2, ensure_ascii=False))
    print()
    
    # 打印 Prompt
    print_prompt(test_block)
    
    # 运行抽取
    print("=" * 100)
    print("运行抽取...")
    print("=" * 100)
    
    try:
        result = run_event_anchor_extraction(test_block)
        
        print("✅ 抽取成功")
        print()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 验证 Schema
        validate_schema(result)
        
    except Exception as e:
        print(f"❌ 抽取失败: {str(e)}")
