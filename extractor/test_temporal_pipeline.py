"""
测试 Temporal Aligner 完整流水线
详细展示每个步骤的输出
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractor.ner import FootballAnchorExtractor


def print_section(title: str):
    """打印分隔符"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_json(data, indent=2):
    """美化打印 JSON 数据"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def test_temporal_pipeline():
    """测试完整的时间锚点提取流水线"""
    
    extractor = FootballAnchorExtractor()
    
    # 测试用例
    test_cases = [
        {
            "name": "测试 1: 多事件 + 多时间",
            "text": "West Ham United is delighted to announce the signing of Argentina international forward Taty Castellanos. The 27-year-old joins the Hammers from Italian club Lazio on a four-and-a-half year contract with the option for a further year. An aggressive, deep-lying forward capable of scoring and creating goals, linking play and working hard for his team, Castellanos has enjoyed a superb career in the MLS, La Liga and Serie A and will now bring his all-round qualities to the Premier League.",
            "publish_date": "2025-11-20"
        },
        # {
        #     "name": "测试 2: Duration 转换",
        #     "text": "Signed a four-and-a-half year contract.",
        #     "publish_date": "2026-01-10"
        # },
        # {
        #     "name": "测试 3: Fallback 机制",
        #     "text": "Amorim is the head coach of Manchester United.",
        #     "publish_date": "2026-01-10"
        # },
        # {
        #     "name": "测试 4: 复杂转会新闻",
        #     "text": "West Ham United has signed Taty Castellanos from Lazio on a four-and-a-half year contract. The 27-year-old joins the Hammers from Italian club Lazio.",
        #     "publish_date": "2026-01-05"
        # }
    ]
    
    for test_case in test_cases:
        print_section(test_case["name"])
        
        text = test_case["text"]
        publish_date = test_case["publish_date"]
        
        print(f"\n📄 输入文本:")
        print(f"  \"{text}\"")
        print(f"  发布日期: {publish_date}")
        
        # 步骤 1: 提取 participants 和 constraints
        print("\n" + "-" * 80)
        print("步骤 1: 提取参与者和约束")
        print("-" * 80)
        
        participants = extractor._extract_participants(text)
        print(f"\n👥 参与者 ({len(participants)} 个):")
        for p in participants:
            print(f"  - {p['type']}: {p['name']}")
        
        constraints = extractor._extract_constraints(text, participants)
        print(f"\n🔗 约束 ({len(constraints)} 个):")
        for c in constraints:
            print(f"  - {c['type']}: {c.get('subject', 'N/A')} → {c.get('expected_state', 'N/A')}")
        
        # 步骤 2: 判定 fact_type
        print("\n" + "-" * 80)
        print("步骤 2: 判定 Fact Type（不依赖 temporal_anchors）")
        print("-" * 80)
        
        fact_type = extractor._determine_fact_type(text, constraints)
        print(f"\n📊 Fact Type: {fact_type}")
        
        # 步骤 3: 提取时间表达式
        print("\n" + "-" * 80)
        print("步骤 3: 提取时间表达式")
        print("-" * 80)
        
        time_expressions = extractor._extract_time_expressions(text, publish_date)
        print(f"\n⏰ 时间表达式 ({len(time_expressions)} 个):")
        for t in time_expressions:
            print(f"  - {t['time_id']}: \"{t['evidence']}\" → {t['normalized']} ({t['granularity']})")
            print(f"    位置: {t['span']}")
        
        # 步骤 4: 提取事件候选
        print("\n" + "-" * 80)
        print("步骤 4: 提取事件候选")
        print("-" * 80)
        
        event_candidates = extractor._extract_event_candidates(text)
        print(f"\n🎯 事件候选 ({len(event_candidates)} 个):")
        for e in event_candidates:
            print(f"  - {e['event_id']}: trigger=\"{e['trigger']}\"")
            print(f"    文本: \"{e['span_text'][:60]}...\" " if len(e['span_text']) > 60 else f"    文本: \"{e['span_text']}\"")
            print(f"    位置: {e['span']}")
        
        # 步骤 5: 时间-事件对齐
        print("\n" + "-" * 80)
        print("步骤 5: 时间-事件对齐（Temporal Aligner）")
        print("-" * 80)
        
        temporal_anchors = extractor._align_temporal_anchors(
            event_candidates, time_expressions, publish_date, fact_type
        )
        print(f"\n🔗 时间锚点 ({len(temporal_anchors)} 个):")
        for anchor in temporal_anchors:
            print(f"  - event_date: {anchor.get('event_date', 'None')}")
            print(f"    valid_from: {anchor.get('valid_from', 'None')}")
            print(f"    valid_to: {anchor.get('valid_to', 'None')}")
            print(f"    time_type: {anchor.get('time_type')}")
            print(f"    evidence: \"{anchor.get('evidence', 'N/A')}\"")
            print()
        
        # 步骤 6: 判定是否需要 resolver
        print("-" * 80)
        print("步骤 6: 判定是否需要 Resolver")
        print("-" * 80)
        
        need_resolver = extractor._determine_need_resolver(fact_type, temporal_anchors)
        print(f"\n🤖 Need Resolver: {need_resolver}")
        
        # 最终总结
        print("\n" + "=" * 80)
        print("✅ 流水线完成")
        print("=" * 80)
        print(f"Fact Type: {fact_type}")
        print(f"时间锚点数: {len(temporal_anchors)}")
        print(f"Need Resolver: {need_resolver}")
        print()


def test_edge_cases():
    """测试边界情况"""
    
    print_section("边界情况测试")
    
    extractor = FootballAnchorExtractor()
    
    edge_cases = [
        {
            "name": "无时间无事件",
            "text": "The team played well.",
            "publish_date": "2026-01-10"
        },
        {
            "name": "只有年份",
            "text": "Scored 10 goals in 2023.",
            "publish_date": "2026-01-10"
        },
        {
            "name": "多个 Duration",
            "text": "Signed a three-year contract before extending with a two-year deal.",
            "publish_date": "2026-01-10"
        },
    ]
    
    for i, case in enumerate(edge_cases, 1):
        print(f"\n{'='*80}")
        print(f"边界测试 {i}: {case['name']}")
        print(f"{'='*80}")
        print(f"文本: \"{case['text']}\"")
        print(f"发布日期: {case['publish_date']}")
        
        text = case["text"]
        publish_date = case["publish_date"]
        
        participants = extractor._extract_participants(text)
        constraints = extractor._extract_constraints(text, participants)
        fact_type = extractor._determine_fact_type(text, constraints)
        time_expressions = extractor._extract_time_expressions(text, publish_date)
        event_candidates = extractor._extract_event_candidates(text)
        temporal_anchors = extractor._align_temporal_anchors(
            event_candidates, time_expressions, publish_date, fact_type
        )
        need_resolver = extractor._determine_need_resolver(fact_type, temporal_anchors)
        
        print(f"\n结果:")
        print(f"  - Fact Type: {fact_type}")
        print(f"  - 时间表达式: {len(time_expressions)} 个")
        print(f"  - 事件候选: {len(event_candidates)} 个")
        print(f"  - 时间锚点: {len(temporal_anchors)} 个")
        print(f"  - Need Resolver: {need_resolver}")


if __name__ == "__main__":
    print("🏈" * 40)
    print("  Temporal Aligner 完整流水线测试")
    print("🏈" * 40)
    
    # 主测试
    test_temporal_pipeline()
    
    # 边界测试
    test_edge_cases()
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)
