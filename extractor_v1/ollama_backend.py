"""
Ollama Backend for Football Event Anchor Extraction

使用 Ollama 本地大模型从足球新闻语义块中抽取事实锚点。
严格遵循 Event vs State 判定规范。
"""

import json
from typing import Dict, Any, Optional
import ollama


# ============================================================================
# System Prompt - 定义抽取规则和输出 Schema
# ============================================================================

SYSTEM_PROMPT = """🎯 你的角色（Role）

你是一个足球领域事实抽取与语义锚点识别专家 Agent。

你同时扮演以下三种专家角色：
1. 足球语义理解专家 - 熟悉球员、俱乐部、转会、合同、比赛、媒体报道语言
2. 信息抽取（IE / NER）专家 - 精通实体边界、类型判定、去噪与歧义处理
3. 事实建模与时间逻辑专家 - 能区分"历史事件"与"状态事实"，明确哪些事实依赖 now

📤 输出格式（Output Contract）

你必须严格输出以下 JSON 结构：

{
  "block_id": "...",
  "text": "...",
  "source": "...",
  "publish_date": "...",
  "anchors": {
    "participants": [
      {"type": "Player|Club|Coach|Team|Stadium|Tournament|Referee|Other", "name": "exact name from text"}
    ],
    "temporal_anchors": [
      {"event_date": "YYYY-MM-DD", "valid_from": "YYYY-MM-DD", "valid_to": "YYYY-MM-DD"}
    ],
    "sources": [
      {"name": "source name", "type": "Media|Official|Social|Other"}
    ],
    "constraints": [
      {"type": "TRANSFER_STATUS|CONTRACT_STATUS|INJURY_STATUS|ROLE_STATUS|MATCH_STATUS|SUSPENSION_STATUS", "subject": "entity name", "expected_state": "abstract state"}
    ]
  },
  "fact_type": "EVENT|STATE",
  "need_resolver": true|false
}

🧩 Anchors 抽取规范

1️⃣ participants（参与实体）
- 只抽取"客观存在、可唯一指代"的实体
- 允许的类型：Player, Club, Coach, Team, Stadium, Tournament, Referee, Other
- 使用文本中出现的原始名称
- 不做别名扩展、不查外部知识
- 不确定时宁可不抽

示例：
{"type": "Player", "name": "De Ligt"}
{"type": "Club", "name": "Manchester United"}

2️⃣ temporal_anchors（时间锚点）
- 若文本中出现明确时间点（on / in / at），必须抽取
- 统一输出为 ISO-8601（YYYY-MM-DD）
- 不要把 publish_date 当作事件时间
- event_date：文本直接指向的事件时间
- valid_from / valid_to：
  - EVENT：通常等于 event_date
  - STATE：若文本未给结束时间，可只给 valid_from

示例：
{"event_date": "2025-09-01", "valid_from": "2025-09-01", "valid_to": "2025-09-01"}

3️⃣ sources（信息来源）
- 默认从输入的 source 字段生成
- 类型：Media, Official, Social, Other

示例：
{"name": "BBC", "type": "Media"}

4️⃣ constraints（约束 / 条件）
- 常见约束类型：
  - TRANSFER_STATUS: transfer_possible, transfer_completed, transfer_rumored, transfer_rejected
  - CONTRACT_STATUS: contract_active, contract_expired, contract_extended
  - INJURY_STATUS: injured, recovering, fit
  - ROLE_STATUS: role_active, role_changed
  - MATCH_STATUS: match_scheduled, match_completed, match_postponed, match_cancelled
  - SUSPENSION_STATUS: suspended, available
- 只在文本明确表达某种状态/承诺/限制时才生成
- subject 必须来自 participants
- expected_state 必须是抽象语义

示例：
{"type": "TRANSFER_STATUS", "subject": "De Ligt", "expected_state": "transfer_possible"}

🧠 Fact Type 判定（极其重要）

✅ EVENT（历史事件）
- 定义：一旦发生，永远成立，不依赖当前时间 now
- 典型特征：
  - 明确时间点（on 1 September 2025, in 2021）
  - 完成时/过去时动词（signed, agreed, won, scored）
  - 比赛结果、转会完成、历史表现
- EVENT → need_resolver = false

示例：
- "De Ligt has agreed to join Manchester United on 1 September 2025." → EVENT
- "Castellanos scored four goals against Real Madrid in 2023." → EVENT
- "Arsenal won 3-2 against Chelsea." → EVENT

⏳ STATE（状态事实）
- 定义：在某个时间区间内成立，真假取决于当前时间
- 典型特征：
  - 现在时（is, remains, serves as）
  - 身份/职位/合同/伤病
  - 隐含 "until something changes"
- STATE → need_resolver = true（除非已有 valid_to）

示例：
- "Amorim is the head coach of Manchester United." → STATE, need_resolver = true
- "He signed a contract until 2028." → STATE, need_resolver = false（已有 valid_to）
- "Salah is currently injured." → STATE, need_resolver = true

⚠️ 边界判断：
- "has agreed to join" → EVENT（协议达成是事件）
- "is under contract" → STATE
- "will join next summer" → EVENT（未来已确定事件）
- "could join / linked with" → 不构成事实（谨慎，可能无 EVENT）

🛑 禁止事项（Hard Constraints）

你绝对不能：
❌ 引入文本中不存在的实体
❌ 使用外部知识补全事实
❌ 推断隐含未明说的时间
❌ 把推测性语言当作已发生事实
❌ 不确定时不要编造，返回空数组 []

📝 输出规则

1. 输出 ONLY JSON，无解释、无 markdown、无额外文字
2. 质量优先级：正确性 > 一致性 > 完整性 > 覆盖率
3. 宁可少抽、保守，也不要编造或过度推断
4. block_id, text, source, publish_date 原样保留（从输入复制）

Remember: 像一名构建足球知识图谱的高级信息抽取工程师一样，冷静、保守、精确地把自然语言压缩成"可计算的事实"。
"""


# ============================================================================
# Developer Prompt - 针对单个 block 的动态提示
# ============================================================================

DEVELOPER_PROMPT = """
📥 Input Block:

Block ID: {block_id}
Source: {source}
Publish Date: {publish_date}

Text:
{text}

📤 Your Task:

Extract anchors from the above text and output the JSON structure according to the System Prompt.

Remember:
1. Copy block_id, text, source, publish_date from input
2. Extract participants, temporal_anchors, sources, constraints
3. Determine fact_type (EVENT or STATE)
4. Determine need_resolver based on fact_type and available temporal information
5. Output ONLY JSON, no explanations

Output:
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
                    "temperature": 0.1,  # 低温度保证输出稳定
                    "num_predict": 2000  # 最大 token 数
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
    required_fields = ["block_id", "text", "source", "publish_date", "anchors", "fact_type", "need_resolver"]
    
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
    
    # 检查 fact_type
    if result["fact_type"] not in ["EVENT", "STATE"]:
        print(f"❌ fact_type 无效: {result['fact_type']}")
        return False
    
    # 检查 need_resolver
    if not isinstance(result["need_resolver"], bool):
        print(f"❌ need_resolver 不是 boolean: {result['need_resolver']}")
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
