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
