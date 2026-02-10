"""
Ollama Backend for Football Event Anchor Extraction

使用 Ollama 本地大模型从足球新闻语义块中抽取事实锚点。
严格遵循 Event vs State 判定规范。
"""

import json
from typing import Dict, Any, Optional
import ollama

SYSTEM_PROMPT = """You are a football-domain information extraction agent.
Extract structured anchors from ONE semantic block and output a COMPLETE JSON.

=====================
OUTPUT JSON SCHEMA
=====================
{
  "block_id": "...",
  "text": "...",
  "source": "...",
  "publish_date": "...",
  "anchors": {
    "participants": [
      {"type": "Player|Club|Coach|Stadium|Tournament|Referee|Other", "name": "..."}
    ],
    "temporal_anchors": [
      {"event_date": "YYYY-MM-DD", "valid_from": "YYYY-MM-DD", "valid_to": "YYYY-MM-DD"}
    ],
    "sources": [
      {"name": "...", "type": "Media|Official|Social|Other"}
    ],
    "constraints": [
      {
        "type": "TRANSFER_STATUS|CONTRACT_STATUS|INJURY_STATUS|MATCH_STATUS|SUSPENSION_STATUS",
        "subject": "...",
        "expected_state": "..."
      }
    ]
  },
  "fact_type": "EVENT|STATE"
}

=====================
CRITICAL RULES
=====================

1️⃣ PARTICIPANTS
- Extract ALL explicitly mentioned entities (players, clubs, teams, coaches, etc.).
- Convert nicknames to official names (e.g. "the Gunners" → "Arsenal").
- Team / club nicknames MUST be type "Team" or "Club", NEVER "Player".
- Do NOT invent entities or use external knowledge.

2️⃣ CONSTRAINTS (STRICT)
- Extract ONLY facts EXPLICITLY stated in the text. NO inference.
- Each constraint MUST satisfy ALL of the following:
  - subject is NOT empty
  - subject EXACTLY matches a name in participants
  - subject is NOT a generic word (❌ "match", "transfer", "semi-final")
- If text states a role (e.g. "is manager/coach"):
  → use CONTRACT_STATUS or ROLE-equivalent constraint with explicit wording only.

3️⃣ TEMPORAL ANCHORS
- Extract ONLY explicit dates/times from text.
- Format strictly as YYYY-MM-DD.
- Do NOT use publish_date as event time.

4️⃣ SOURCES
- Always generate from input `source` field.

5️⃣ FACT TYPE
- EVENT: completed or scheduled factual events (signed, agreed, won, played).
- STATE: time-dependent conditions (contract, injury, role, suspension).

=====================
HARD REQUIREMENTS
=====================
- Copy block_id, text, source, publish_date EXACTLY as input.
- ALL top-level fields MUST exist.
- Use [] for empty arrays.
- constraints array MUST contain ≥1 item.
- NEVER hallucinate facts, entities, dates, or states.
- Output JSON ONLY. No explanations.
"""

# ============================================================================
# Developer Prompt - 针对单个 block 的动态提示
# ============================================================================

DEVELOPER_PROMPT = """Input:
ID: {block_id} | Source: {source} | Date: {publish_date}
Text: {text}

Output JSON (constraints in anchors, fact_type required):
"""


# ============================================================================
# Event Decomposition Prompts (事件分解层)
# ============================================================================

EVENT_DECOMPOSITION_SYSTEM_PROMPT = """You are a FOOTBALL EVENT DECOMPOSITION AGENT.

Your task is to convert a football-related semantic block into 1–N structured event units.

This module is DOMAIN-GENERIC.
It must work for transfers, matches, contracts, injuries, appointments, suspensions, and official statements.

==================================================
INPUT
==================================================

You will receive:
- block_id
- text (original semantic block)
- source
- publish_date

==================================================
OUTPUT JSON SCHEMA (STRICT)
==================================================

{
  "events": [
    {
      "event_id": "string",
      "parent_event_id": "string | null",
      "is_sub_event": boolean,
      "event_description": "string",
      "block_text": "string",
      "source": "string",
      "publish_date": "string"
    }
  ]
}

==================================================
MODULE RESPONSIBILITY (BOUNDARY)
==================================================

This module ONLY does:
- event splitting
- parent–child relationship assignment
- event semantic compression (event_description)

This module MUST NOT do:
- time extraction or normalization
- state judgment (completed, injured, suspended, etc.)
- constraint generation
- entity normalization
- inference beyond explicit text

==================================================
CORE PRINCIPLE
==================================================

You are an INDEXING LAYER, not a FACT REASONER.

Each event_description must be:
- grounded in explicit text
- usable as the PRIMARY input for downstream extraction

==================================================
1️⃣ EVENT SPLITTING RULES
==================================================

- One semantic block can produce 1 to N events.
- Each event represents ONE clear football-related fact or action.
- Split events ONLY when:
  - actions are logically independent, OR
  - one action is a decisive component of another.

Examples of valid events (domain-generic):
- a transfer agreement
- a contract extension
- a match result
- a goal
- a red card
- an injury announcement
- a managerial appointment

If the text describes a single fact → produce ONE event.
If uncertain → DO NOT split.

==================================================
2️⃣ PARENT–CHILD RELATIONSHIP RULES
==================================================

Main event:
- is_sub_event = false
- parent_event_id = null
- represents the primary fact of the block

Sub-event:
- is_sub_event = true
- parent_event_id = main event's event_id
- represents:
  - a causal action
  - a decisive moment
  - a concrete detail that directly explains the main event

If no clear hierarchy exists:
- create multiple main events
- all with parent_event_id = null

==================================================
3️⃣ EVENT_DESCRIPTION RULES (CRITICAL)
==================================================

event_description MUST:

- Be ONE sentence
- Be concise but information-dense
- Describe WHAT happened, WHO was involved, and WHAT action occurred
- Be sufficient for downstream modules to extract:
  - participants
  - event type
  - possible constraints

event_description MAY include:
- time expressions (as text)
- scores or outcomes
- locations

event_description MUST NOT:
- add interpretation or narrative tone
- introduce future implications
- infer unstated facts
- summarize the entire block

Good examples:
- "De Ligt agreed to join Manchester United from Bayern Munich"
- "Arsenal defeated Crystal Palace on penalties"
- "Marc Guehi scored an equaliser in stoppage time"
- "Chelsea announced the appointment of a new head coach"

Bad examples:
- "A dramatic moment followed"
- "This secured qualification"
- "The team showed resilience"

==================================================
4️⃣ BLOCK_TEXT RULES
==================================================

- block_text MUST be the FULL original input text
- DO NOT modify, summarize, or partially copy
- All events may share the same block_text

==================================================
5️⃣ EVENT_ID RULES
==================================================

- Main events: "{block_id}-1", "{block_id}-2", ...
- Sub-events: "{parent_event_id}-1", "{parent_event_id}-2", ...

Example:
block_id = "010"
- main event: "010-1"
- sub-event: "010-1-1"

==================================================
FORBIDDEN ACTIONS
==================================================

❌ No date normalization
❌ No state assignment
❌ No constraint generation
❌ No entity inference
❌ No comments or explanations

==================================================
OUTPUT HARD CONSTRAINTS (ABSOLUTE)
==================================================

- Output ONLY valid JSON
- No markdown
- No natural language prefixes or suffixes
- No comments
- No placeholder values ("...", "same as above")

JSON must be directly parseable by standard JSON parsers.

==================================================
FINAL INSTRUCTION
==================================================

Return ONLY the JSON object.
Nothing else.


"""

EVENT_DECOMPOSITION_DEVELOPER_PROMPT = """Input:
Block ID: {block_id}
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
        model: str = "llama3:latest",
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
        
    def _build_messages(self, block: Dict[str, Any]) -> list:
        """
        构建两段式 Prompt 消息列表
        
        Args:
            block: 输入的语义块（包含 block_id, text, source, publish_date）
            
        Returns:
            消息列表 [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        # System Message
        system_message = {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
        
        # Developer Message（填充 block 数据）
        developer_content = DEVELOPER_PROMPT.format(
            block_id=block.get("block_id", "N/A"),
            source=block.get("source", "N/A"),
            publish_date=block.get("publish_date", "N/A"),
            text=block.get("text", "")
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
    
    def extract_anchors(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单个语义块中抽取锚点
        
        Args:
            block: 输入的语义块
            
        Returns:
            包含锚点的结果 dict
        """
        # 1. 构建消息
        messages = self._build_messages(block)
        
        # 2. 调用 LLM
        raw_response = self._call_ollama(messages)
        
        # 3. 解析 JSON
        result = self._parse_json(raw_response)
        
        # 4. 直接返回，不做任何后处理
        return result
    
    def decompose_events(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        将语义块分解为事件单元（Event Decomposition Layer）
        
        Args:
            block: 输入的语义块，必须包含：
                - block_id: 唯一标识
                - text: 原始文本
                - source: 信息来源
                - publish_date: 发布日期
        
        Returns:
            包含事件列表的结果 dict：
            {
                "events": [
                    {
                        "event_id": "...",
                        "parent_event_id": "..." | null,
                        "is_sub_event": true | false,
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
        required_event_fields = ["event_id", "parent_event_id", "is_sub_event", 
                                 "event_description", "block_text", "source", "publish_date"]
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
    验证输出是否符合 Schema
    
    Args:
        result: 抽取结果
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["block_id", "text", "source", "publish_date", "anchors", "fact_type"]
    
    # 检查顶层字段
    for field in required_fields:
        if field not in result:
            print(f"❌ 缺少字段: {field}")
            return False
    
    # 检查 anchors 子字段
    anchors = result.get("anchors", {})
    required_anchor_fields = ["participants", "temporal_anchors", "sources", "constraints"]
    
    for field in required_anchor_fields:
        if field not in anchors:
            print(f"❌ anchors 缺少字段: {field}")
            return False
    
    # 检查 constraints 必须存在且不能为空
    constraints = anchors.get("constraints")
    if not isinstance(constraints, list):
        print(f"❌ constraints 必须是数组类型")
        return False
    
    if len(constraints) == 0:
        print(f"❌ constraints 不能为空，必须至少包含一个约束")
        return False
    
    # 检查 fact_type
    if result["fact_type"] not in ["EVENT", "STATE"]:
        print(f"❌ fact_type 无效: {result['fact_type']}")
        return False
    
    print("✅ Schema 验证通过")
    return True


# ============================================================================
# 调试工具
# ============================================================================

def print_prompt(block: Dict[str, Any]):
    """
    打印完整的 Prompt（用于调试）
    
    Args:
        block: 输入的语义块
    """
    backend = OllamaBackend()
    messages = backend._build_messages(block)
    
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
