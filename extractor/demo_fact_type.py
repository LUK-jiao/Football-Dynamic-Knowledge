#!/usr/bin/env python3
"""
Fact Type 功能示例

展示 extractor 的 fact_type 判定和 need_resolver 决策功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from extractor.ner import FootballAnchorExtractor


def demo(text: str, source: str, publish_date: str, description: str):
    """展示单个示例"""
    print("\n" + "=" * 80)
    print(f"示例: {description}")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    chunk = {
        "block_id": "demo_001",
        "text": text,
        "source": source,
        "publish_date": publish_date
    }
    
    result = extractor.extract_anchors(chunk)
    
    print(f"\n📝 输入文本:")
    print(f'  "{text}"')
    
    print(f"\n🎯 判定结果:")
    print(f"  fact_type: {result['fact_type']}")
    print(f"  need_resolver: {result['need_resolver']}")
    
    print(f"\n📊 完整输出:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    """运行所有示例"""
    print("\n" + "🌟" * 40)
    print("  Fact Type 判定功能示例")
    print("  展示 extractor 如何判定 fact_type 和 need_resolver")
    print("🌟" * 40)
    
    # ========================================================================
    # 示例组 1: EVENT 类型（历史事件）
    # ========================================================================
    print("\n" + "━" * 80)
    print("  示例组 1: EVENT 类型（历史事件）")
    print("━" * 80)
    
    demo(
        text="De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
        source="BBC",
        publish_date="2025-08-23",
        description="转会协议达成（完成时 + 明确时间）"
    )
    
    demo(
        text="Castellanos scored four goals in a single game for Girona against Real Madrid in La Liga in 2023.",
        source="ESPN",
        publish_date="2025-11-20",
        description="历史进球记录（过去时 + 历史年份）"
    )
    
    demo(
        text="Arsenal won 3-2 against Chelsea in the Premier League.",
        source="Sky Sports",
        publish_date="2025-01-15",
        description="比赛结果（比分状态 → EVENT）"
    )
    
    # ========================================================================
    # 示例组 2: STATE 类型（需要 resolver）
    # ========================================================================
    print("\n" + "━" * 80)
    print("  示例组 2: STATE 类型（需要 resolver）")
    print("━" * 80)
    
    demo(
        text="Amorim is the head coach of Manchester United.",
        source="Manchester United Official",
        publish_date="2026-01-10",
        description="教练身份（现在时状态，无有效期）"
    )
    
    demo(
        text="De Ligt is under contract with Bayern Munich.",
        source="Bayern Munich Official",
        publish_date="2025-08-23",
        description="合同状态（无到期日期，需推理）"
    )
    
    demo(
        text="Salah is currently injured and unavailable for selection.",
        source="Liverpool FC Official",
        publish_date="2025-11-20",
        description="伤病状态（当前状态，需推理恢复时间）"
    )
    
    # ========================================================================
    # 示例组 3: STATE 类型（不需要 resolver）
    # ========================================================================
    print("\n" + "━" * 80)
    print("  示例组 3: STATE 类型（已有有效期，不需要 resolver）")
    print("━" * 80)
    
    demo(
        text="He signed a four-and-a-half year contract until 2028.",
        source="West Ham United Official",
        publish_date="2026-01-05",
        description="合同状态（有 valid_to，不需要 resolver）"
    )
    
    demo(
        text="Castellanos joined the Hammers on a contract valid from January 2026.",
        source="West Ham United Official",
        publish_date="2026-01-05",
        description="合同状态（有 valid_from，不需要 resolver）"
    )
    
    # ========================================================================
    # 示例组 4: 边界情况
    # ========================================================================
    print("\n" + "━" * 80)
    print("  示例组 4: 边界情况")
    print("━" * 80)
    
    demo(
        text="Manchester United have agreed a deal to sign De Ligt.",
        source="The Athletic",
        publish_date="2025-08-20",
        description="转会传闻（have agreed → EVENT）"
    )
    
    demo(
        text="Salah suffered a hamstring injury during training yesterday.",
        source="Liverpool FC Official",
        publish_date="2025-11-20",
        description="伤病报告（过去时动作 → EVENT）"
    )
    
    demo(
        text="He signed with Manchester United in 2021 and is currently the captain.",
        source="BBC",
        publish_date="2025-11-20",
        description="混合描述（历史签约主导 → EVENT）"
    )
    
    print("\n" + "=" * 80)
    print("  ✅ 示例演示完成")
    print("=" * 80)
    print("\n💡 关键要点:")
    print("  1. EVENT：历史事件，一旦发生永远成立，不需要 resolver")
    print("  2. STATE：状态事实，随时间变化，可能需要 resolver 推理有效期")
    print("  3. need_resolver = true：缺失 valid_from/valid_to，需要 resolver 推理")
    print("  4. need_resolver = false：已有有效期或不需要有效期（EVENT）")
    print("\n")


if __name__ == "__main__":
    main()
