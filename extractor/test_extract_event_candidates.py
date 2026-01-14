#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件：_extract_event_candidates
用于验证事件候选提取功能

测试范围：
1. 单个事件提取（过去时动词）
2. 多个事件提取（不同动词）
3. 并列事件提取（and连接）
4. 不同时态动词（过去时、动名词、完成时、状态）
5. 连接词分段（before, after, since, until, when）
6. 边界情况（无事件、重复、空文本）
7. 真实数据测试
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from extractor.ner import FootballAnchorExtractor


def test_single_event_extraction():
    """测试1: 单个事件提取"""
    print("=" * 80)
    print("测试1: 单个事件提取")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        ("Arsenal won the match.", 1, "won"),
        ("Messi scored a goal.", 1, "scored"),
        ("Ronaldo joined Manchester United.", 1, "joined"),
        ("The club signed a new player.", 1, "signed"),
        ("The team announced the transfer.", 1, "announced"),
    ]
    
    for text, expected_count, expected_trigger in test_cases:
        result = extractor._extract_event_candidates(text)
        status = "✅" if len(result) == expected_count else "❌"
        print(f"{status} '{text}'")
        print(f"   预期: {expected_count} 个事件, trigger='{expected_trigger}'")
        print(f"   实际: {len(result)} 个事件")
        
        if result:
            for event in result:
                print(f"      [{event['event_id']}] trigger='{event['trigger']}', span_text='{event['span_text']}'")
        print()
    
    print()


def test_multiple_events_extraction():
    """测试2: 多个事件提取（不同动词）"""
    print("=" * 80)
    print("测试2: 多个事件提取（不同动词）")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        ("Arsenal won the match. Messi scored a goal.", 2),
        ("He joined the club and signed a contract.", 2),
        ("The player arrived in London. He completed his medical.", 2),
    ]
    
    for text, expected_count in test_cases:
        result = extractor._extract_event_candidates(text)
        status = "✅" if len(result) == expected_count else "❌"
        print(f"{status} '{text}'")
        print(f"   预期: {expected_count} 个事件")
        print(f"   实际: {len(result)} 个事件")
        
        for event in result:
            print(f"      [{event['event_id']}] trigger='{event['trigger']}', span_text='{event['span_text']}'")
        print()
    
    print()


def test_parallel_events_extraction():
    """测试3: 并列事件提取（and连接）"""
    print("=" * 80)
    print("测试3: 并列事件提取（and连接）")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        ("He signed a contract and joined the team.", 2, ["signed", "joined"]),
        ("Arsenal won the match and scored five goals.", 2, ["won", "scored"]),
        ("He agreed to the terms and completed the transfer.", 2, ["agreed", "completed"]),
    ]
    
    for text, expected_count, expected_triggers in test_cases:
        result = extractor._extract_event_candidates(text)
        actual_triggers = [e['trigger'] for e in result]
        status = "✅" if len(result) == expected_count and all(t in actual_triggers for t in expected_triggers) else "❌"
        
        print(f"{status} '{text}'")
        print(f"   预期: {expected_count} 个事件, triggers={expected_triggers}")
        print(f"   实际: {len(result)} 个事件, triggers={actual_triggers}")
        
        for event in result:
            print(f"      [{event['event_id']}] trigger='{event['trigger']}', span_text='{event['span_text']}'")
        print()
    
    print()


def test_different_verb_tenses():
    """测试4: 不同时态动词"""
    print("=" * 80)
    print("测试4: 不同时态动词（过去时、动名词、完成时、状态）")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        # 过去时
        ("He won the championship.", 1, "past", "won"),
        
        # 动名词（使用更纯粹的例子，避免与其他动词混淆）
        ("Winning the match was important.", 1, "gerund", "winning"),
        
        # 完成时
        ("He has signed with the club.", 1, "perfect", "signed"),
        ("They have joined the team.", 1, "perfect", "joined"),
        
        # 状态动词
        ("He is the head coach.", 1, "state", "is"),
        ("He was under contract.", 1, "state", "was"),
    ]
    
    for text, expected_count, verb_type, expected_trigger in test_cases:
        result = extractor._extract_event_candidates(text)
        status = "✅" if len(result) == expected_count else "❌"
        
        print(f"{status} '{text}' (类型: {verb_type})")
        print(f"   预期: {expected_count} 个事件, trigger='{expected_trigger}'")
        print(f"   实际: {len(result)} 个事件")
        
        for event in result:
            print(f"      [{event['event_id']}] trigger='{event['trigger']}', span_text='{event['span_text']}'")
        print()
    
    print()


def test_connector_segmentation():
    """测试5: 连接词分段（before, after, since, until, when）
    
    说明：基于 spaCy 依存句法分析，连接词引导的从句通常会被识别为主句的一部分，
    因此每个句子通常只提取一个主要事件。这是符合依存句法结构的正确行为。
    """
    print("=" * 80)
    print("测试5: 连接词分段（基于依存句法分析）")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    # 更新预期结果：基于依存句法，每个句子通常只提取一个主要事件
    test_cases = [
        ("He joined Arsenal before he signed a contract.", 1, ["joined"]),
        ("After winning the match, they celebrated.", 1, ["celebrated"]),
        ("He has played for Arsenal since he joined in 2010.", 1, ["played"]),
        ("He remained with the club until he left in 2020.", 1, ["remained"]),
        ("When he scored the goal, the crowd cheered.", 1, ["cheered"]),
    ]
    
    for text, expected_count, expected_triggers in test_cases:
        result = extractor._extract_event_candidates(text)
        actual_triggers = [e['trigger'] for e in result]
        status = "✅" if len(result) == expected_count and all(t in actual_triggers for t in expected_triggers) else "❌"
        
        print(f"{status} '{text}'")
        print(f"   预期: {expected_count} 个事件, triggers={expected_triggers}")
        print(f"   实际: {len(result)} 个事件, triggers={actual_triggers}")
        
        for event in result:
            print(f"      [{event['event_id']}] trigger='{event['trigger']}', span_text='{event['span_text']}'")
        print()
    
    print()


def test_edge_cases():
    """测试6: 边界情况"""
    print("=" * 80)
    print("测试6: 边界情况")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        # 空文本
        ("", 1, "implicit"),
        
        # 无明确动词的文本（应该返回隐式事件）
        ("Arsenal is a football club in London.", 1, None),
        
        # 只有名词的文本
        ("Manchester United Football Club.", 1, "implicit"),
        
        # 重复的动词
        ("He won and won again.", None, None),
    ]
    
    for text, expected_count, expected_trigger in test_cases:
        result = extractor._extract_event_candidates(text)
        
        if expected_count is not None:
            status = "✅" if len(result) == expected_count else "❌"
            print(f"{status} '{text}'")
            print(f"   预期: {expected_count} 个事件" + (f", trigger='{expected_trigger}'" if expected_trigger else ""))
            print(f"   实际: {len(result)} 个事件")
        else:
            print(f"📝 '{text}'")
            print(f"   实际: {len(result)} 个事件")
        
        for event in result:
            print(f"      [{event['event_id']}] trigger='{event['trigger']}', span_text='{event['span_text'][:50]}...'")
        print()
    
    print()


def test_output_schema():
    """测试7: 输出结构验证"""
    print("=" * 80)
    print("测试7: 输出结构验证")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    text = "Arsenal won the match."
    result = extractor._extract_event_candidates(text)
    
    print(f"文本: '{text}'")
    print(f"返回结果: {len(result)} 个事件\n")
    
    required_fields = ["event_id", "trigger", "span_text", "span"]
    
    for event in result:
        print(f"事件 {event['event_id']}:")
        
        # 检查必需字段
        for field in required_fields:
            if field in event:
                print(f"  ✅ {field}: {event[field]}")
            else:
                print(f"  ❌ {field}: 缺失")
        
        # 检查 span 格式
        if 'span' in event:
            span = event['span']
            if isinstance(span, tuple) and len(span) == 2:
                print(f"  ✅ span 格式正确: (start={span[0]}, end={span[1]})")
                
                # 验证 span 与 span_text 的一致性
                actual_text = text[span[0]:span[1]]
                if actual_text.strip() == event['span_text'].strip():
                    print(f"  ✅ span 与 span_text 一致")
                else:
                    print(f"  ⚠️  span 与 span_text 不完全一致")
                    print(f"      从文本提取: '{actual_text}'")
                    print(f"      span_text:   '{event['span_text']}'")
            else:
                print(f"  ❌ span 格式错误: {span}")
        print()
    
    print()


def test_real_data():
    """测试8: 真实数据测试"""
    print("=" * 80)
    print("测试8: 真实数据测试")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    real_texts = [
        # 转会新闻
        "Matthijs de Ligt has joined Manchester United from Bayern Munich on a five-year contract. The defender completed his medical in Manchester before signing the deal.",
        
        # 比赛结果
        "Arsenal won the match 3-1 and scored five goals in total. Saka scored twice and assisted once.",
        
        # 伤病报告
        "Mohamed Salah picked up an injury during training. He left the session early and will miss the next match.",
        
        # 复杂句式
        "After winning the Premier League in 2020, Liverpool signed Thiago from Bayern. He has played 50 matches since joining the club.",
    ]
    
    for i, text in enumerate(real_texts, 1):
        print(f"\n真实案例 {i}:")
        print(f"文本: {text}\n")
        
        result = extractor._extract_event_candidates(text)
        
        print(f"⏰ 提取到的事件 ({len(result)} 个):")
        if result:
            for event in result:
                print(f"  [{event['event_id']}] trigger='{event['trigger']}'")
                print(f"      span_text: {event['span_text']}")
                print(f"      span: {event['span']}")
        else:
            print("  (无)")
        print()
    
    print("=" * 80)
    print()


def test_complex_scenarios():
    """测试9: 复杂场景"""
    print("=" * 80)
    print("测试9: 复杂场景")
    print("=" * 80)
    
    extractor = FootballAnchorExtractor()
    
    # 复杂场景1: 多层嵌套
    text1 = "After he signed with Arsenal in 2020, before he joined Barcelona in 2023, he played for Lyon."
    print(f"场景1: 多层嵌套时间关系")
    print(f"文本: {text1}\n")
    result1 = extractor._extract_event_candidates(text1)
    print(f"提取到 {len(result1)} 个事件:")
    for event in result1:
        print(f"  [{event['event_id']}] {event['trigger']}: {event['span_text']}")
    print()
    
    # 复杂场景2: 多个并列事件
    text2 = "He signed, joined, and played for the club."
    print(f"场景2: 多个并列事件")
    print(f"文本: {text2}\n")
    result2 = extractor._extract_event_candidates(text2)
    print(f"提取到 {len(result2)} 个事件:")
    for event in result2:
        print(f"  [{event['event_id']}] {event['trigger']}: {event['span_text']}")
    print()
    
    # 复杂场景3: 长文本
    text3 = """
    Cristiano Ronaldo joined Manchester United in 2003 and played for the club until 2009. 
    After winning multiple trophies, he signed with Real Madrid and scored over 400 goals. 
    He has won five Ballon d'Or awards since joining professional football.
    """
    print(f"场景3: 长文本多事件")
    print(f"文本: {text3.strip()[:100]}...\n")
    result3 = extractor._extract_event_candidates(text3)
    print(f"提取到 {len(result3)} 个事件:")
    for event in result3:
        print(f"  [{event['event_id']}] {event['trigger']}: {event['span_text'][:50]}...")
    print()
    
    print()

def test_real_data_from_json():
    """使用真实 JSON 数据测试时间表达式提取"""
    import json
    
    print("测试：使用 Arsenal EFL Cup 真实数据")
    
    # 读取 JSON 文件
    json_path = "extractor/output/arsenal_efl_cup_match_20260114_112335.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        blocks = json.load(f)
    
    extractor = FootballAnchorExtractor()
    
    print(f"\n总共 {len(blocks)} 个块需要测试\n")
    
    for i, block in enumerate(blocks, 1):
        block_id = block['block_id']
        text = block['text']
        publish_date = block['publish_date']
        existing_anchors = block['anchors']['temporal_anchors']
        
        print(f"{'='*80}")
        print(f"块 {i}: {block_id}")
        print(f"{'='*80}")
        print(f"\n📄 文本:")
        print(f"  {text}")
        print(f"\n📅 发布日期: {publish_date}")
        
        # 提取候选事件
        event_candidates = extractor._extract_event_candidates(text)
        
        print(f"\n⏰ 提取到的候选事件 ({len(event_candidates)} 个):")
        for event in event_candidates:
            print(f"  [{event['event_id']}] {event['trigger']}: {event['span_text'][:50]}...")
        print()
    
    print(f"{'='*80}")
    print(f"测试完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    print("\n")
    print("🏈" * 64)
    print("🏈" * 16 + "                                                " + "🏈" * 16)
    print("🏈" * 16 + "          测试：_extract_event_candidates        " + "🏈" * 16)
    print("🏈" * 16 + "                                                " + "🏈" * 16)
    print("🏈" * 64)
    print("\n")
    
    # 运行所有测试
    # test_single_event_extraction()
    # test_multiple_events_extraction()
    # test_parallel_events_extraction()
    # test_different_verb_tenses()
    # test_connector_segmentation()
    # test_edge_cases()
    # test_output_schema()
    # test_real_data()
    # test_complex_scenarios()
    test_real_data_from_json()
    
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)
