#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 _extract_time_expressions 函数

覆盖所有时间粒度：
- YEAR: 年份
- MONTH: 年月
- DAY: 完整日期
- DURATION: 时间段
- RELATIVE: 相对时间
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.ner import FootballAnchorExtractor, TimeGranularity


def print_separator(char="=", length=80):
    print(char * length)


def print_time_expressions(expressions, title="时间表达式"):
    """打印时间表达式列表"""
    print(f"\n{title} ({len(expressions)} 个):")
    if not expressions:
        print("  (无)")
        return
    
    for expr in expressions:
        print(f"  [{expr['time_id']}] \"{expr['evidence']}\"")
        print(f"      normalized: {expr['normalized']}")
        print(f"      granularity: {expr['granularity']}")
        print(f"      span: {expr['span']}")


def test_year_extraction():
    """测试年份抽取 (YEAR)"""
    print_separator("🏈", 80)
    print("测试组 1: 年份抽取 (YEAR)")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        "He won the trophy in 2021.",
        "The club was founded in 1895.",
        "During 2023, they won three titles.",
        "The 2021 season was successful.",
        "He played in the 2020/21 season.",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n案例 {i}: \"{text}\"")
        expressions = extractor._extract_time_expressions(text, "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证
        if expressions and expressions[0]['granularity'] == TimeGranularity.YEAR:
            print("✅ 正确识别为 YEAR")
        else:
            print("❌ 识别失败")
    
    print()


def test_month_extraction():
    """测试年月抽取 (MONTH)"""
    print_separator("🏈", 80)
    print("测试组 2: 年月抽取 (MONTH)")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        "He joined in September 2025.",
        "The match was held during March 2023.",
        "In January 2026, he scored his first goal.",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n案例 {i}: \"{text}\"")
        expressions = extractor._extract_time_expressions(text, "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证
        if expressions and expressions[0]['granularity'] == TimeGranularity.MONTH:
            print("✅ 正确识别为 MONTH")
        else:
            print("❌ 识别失败")
    
    print()


def test_day_extraction():
    """测试完整日期抽取 (DAY)"""
    print_separator("🏈", 80)
    print("测试组 3: 完整日期抽取 (DAY)")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        ("1 September 2025", "DMY 格式"),
        ("September 1, 2025", "MDY 格式"),
        ("The match was on 15 December 2023.", "DMY 在句中"),
        ("He signed on January 10, 2026.", "MDY 在句中"),
        ("Contract starts on 2026-01-05.", "ISO 格式"),
    ]
    
    for i, (text, desc) in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {desc}")
        print(f"文本: \"{text}\"")
        expressions = extractor._extract_time_expressions(text, "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证
        if expressions and expressions[0]['granularity'] == TimeGranularity.DAY:
            print("✅ 正确识别为 DAY")
        else:
            print("❌ 识别失败")
    
    print()


def test_duration_extraction():
    """测试时间段抽取 (DURATION)"""
    print_separator("🏈", 80)
    print("测试组 4: 时间段抽取 (DURATION)")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        ("Signed a four-and-a-half year contract.", "小数年份"),
        ("He agreed to a five-year deal.", "整数年份"),
        ("Extended with a three year contract.", "整数年份（无连字符）"),
        ("Signed a two-year deal with the club.", "数字形式"),
        ("Agreed a six month contract.", "月份单位"),
        ("West Ham United is delighted to announce the signing of Argentina international forward Taty Castellanos. The 27-year-old joins the Hammers from Italian club Lazio on a four-and-a-half year contract with the option for a further year. An aggressive, deep-lying forward capable of scoring and creating goals, linking play and working hard for his team, Castellanos has enjoyed a superb career in the MLS, La Liga and Serie A and will now bring his all-round qualities to the Premier League.", "复杂文本")
    ]
    
    for i, (text, desc) in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {desc}")
        print(f"文本: \"{text}\"")
        expressions = extractor._extract_time_expressions(text, "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证
        has_duration = any(e['granularity'] == TimeGranularity.DURATION for e in expressions)
        if has_duration:
            print("✅ 正确识别为 DURATION")
        else:
            print("❌ 识别失败")
    
    print()


def test_relative_extraction():
    """测试相对时间抽取 (RELATIVE)"""
    print_separator("🏈", 80)
    print("测试组 5: 相对时间抽取 (RELATIVE)")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        ("He joined last year.", "方向型 - last year"),
        ("The match is next month.", "方向型 - next month"),
        ("He scored 10 goals this season.", "方向型 - this season"),
        ("The deal was signed yesterday.", "单词型 - yesterday"),
        ("The press conference is today.", "单词型 - today"),
        ("The match starts tomorrow.", "单词型 - tomorrow"),
        ("2 years ago, he played for Lazio.", "数字型 - years ago"),
        ("He left the club 3 months ago.", "数字型 - months ago"),
        ("5 days ago, he scored a hat-trick.", "数字型 - days ago"),
        ("Last summer, he joined the club.", "方向型 - last summer"),
        ("Next week, the match will be held.", "方向型 - next week"),
        ("He then scored 14 times on Tuesday.", "星期几 - on Tuesday"),
        ("The match is on Monday.", "星期几 - on Monday"),
        ("He played last Friday.", "星期几 - last Friday"),
        ("Next Sunday will be important.", "星期几 - next Sunday"),
        ("The press conference is Monday morning.", "星期几 - Monday morning"),
        ("Available for Tuesday evening's match.", "星期几 - Tuesday evening"),
    ]
    
    for i, (text, desc) in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {desc}")
        print(f"文本: \"{text}\"")
        expressions = extractor._extract_time_expressions(text, "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证
        has_relative = any(e['granularity'] == TimeGranularity.RELATIVE for e in expressions)
        if has_relative:
            print("✅ 正确识别为 RELATIVE")
        else:
            print("❌ 识别失败")
    
    print()


def test_mixed_extraction():
    """测试混合时间表达式"""
    print_separator("🏈", 80)
    print("测试组 6: 混合时间表达式")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        {
            "text": "He joined last year and won the cup in 2021.",
            "desc": "相对时间 + 绝对年份",
            "expected_count": 2,
            "expected_types": [TimeGranularity.YEAR, TimeGranularity.RELATIVE]
        },
        {
            "text": "Signed on 1 September 2025 for a four-year contract.",
            "desc": "完整日期 + Duration",
            "expected_count": 2,
            "expected_types": [TimeGranularity.DAY, TimeGranularity.DURATION]
        },
        {
            "text": "Yesterday, he signed a five-year deal starting in January 2026.",
            "desc": "相对时间 + 年月 + Duration",
            "expected_count": 3,
            "expected_types": [TimeGranularity.MONTH, TimeGranularity.RELATIVE, TimeGranularity.DURATION]
        },
        {
            "text": "Won in 2021 before scoring in 2023.",
            "desc": "多个年份",
            "expected_count": 2,
            "expected_types": [TimeGranularity.YEAR, TimeGranularity.YEAR]
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case['desc']}")
        print(f"文本: \"{case['text']}\"")
        expressions = extractor._extract_time_expressions(case['text'], "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证数量
        if len(expressions) == case['expected_count']:
            print(f"✅ 数量正确 ({case['expected_count']} 个)")
        else:
            print(f"❌ 数量错误: 预期 {case['expected_count']}, 实际 {len(expressions)}")
        
        # 验证类型
        actual_types = [e['granularity'] for e in expressions]
        if set(actual_types) == set(case['expected_types']):
            print(f"✅ 类型正确")
        else:
            print(f"❌ 类型错误: 预期 {case['expected_types']}, 实际 {actual_types}")
    
    print()


def test_edge_cases():
    """测试边界情况"""
    print_separator("🏈", 80)
    print("测试组 7: 边界情况")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    test_cases = [
        # {
        #     "text": "West Ham United is delighted to announce the signing of Argentina international forward Taty Castellanos. The 27-year-old joins the Hammers from Italian club Lazio on a four-and-a-half year contract with the option for a further year. An aggressive, deep-lying forward capable of scoring and creating goals, linking play and working hard for his team, Castellanos has enjoyed a superb career in the MLS, La Liga and Serie A and will now bring his all-round qualities to the Premier League.",
        #     "desc": "合同时间",
        #     "expected_count": 1
        # },
        # {
        #     "text": "Born in Mendoza and capped twice by his country, Castellanos won the MLS Cup and Golden Boot with New York City FC in 2021 before netting four goals in a single game for Girona against Real Madrid in La Liga in 2023.",
        #     "desc": "两个年份",
        #     "expected_count": 2
        # },
        {
            "text": "He then scored 14 times on Tuesday.",
            "desc": "last season 能识别吗",
            "expected_count": 1
        },
        {
            "text": "Identified as a key target by Head Coach Nuno Espírito Santo, the Hammers’ new No11 - who has signed in time to be available for Tuesday evening’s Premier League match against Nottingham Forest at London Stadium - is now looking forward to pulling on a West Ham shirt and showing the Claret and Blue Army what he can do.",
            "desc": "相对时间",
            "expected_count": 1
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case['desc']}")
        print(f"文本: \"{case['text']}\"")
        expressions = extractor._extract_time_expressions(case['text'], "2026-01-10")
        print_time_expressions(expressions)
        
        # 验证
        if len(expressions) == case['expected_count']:
            print(f"✅ 符合预期 ({case['expected_count']} 个)")
        else:
            print(f"⚠️  实际 {len(expressions)} 个，预期 {case['expected_count']} 个")
    
    print()


def test_span_deduplication():
    """测试基于 span 的去重机制"""
    print_separator("🏈", 80)
    print("测试组 8: Span 去重机制")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    print("\n说明: 现在使用 span (start, end) 进行去重，而不是 evidence 文本")
    
    test_cases = [
        {
            "text": "in September 2025",
            "desc": "MONTH 和 YEAR 重叠（September 2025）",
            "note": "MONTH 正则应该匹配整个 'in September 2025'，YEAR 不应匹配"
        },
        {
            "text": "four-and-a-half year contract",
            "desc": "Duration 嵌套（four-and-a-half vs half）",
            "note": "可能匹配到两个 duration，但 span 不同"
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case['desc']}")
        print(f"文本: \"{case['text']}\"")
        print(f"备注: {case['note']}")
        expressions = extractor._extract_time_expressions(case['text'], "2026-01-10")
        print_time_expressions(expressions)
        
        # 检查 span 是否有重叠
        spans = [e['span'] for e in expressions]
        has_overlap = False
        for j in range(len(spans)):
            for k in range(j + 1, len(spans)):
                span1, span2 = spans[j], spans[k]
                # 检查是否重叠
                if not (span1[1] <= span2[0] or span2[1] <= span1[0]):
                    has_overlap = True
                    print(f"⚠️  Span 重叠: {span1} 和 {span2}")
        
        if not has_overlap and len(expressions) > 0:
            print("✅ 无 span 重叠")
    
    print()


def test_output_schema():
    """测试输出结构的一致性"""
    print_separator("🏈", 80)
    print("测试组 9: 输出结构验证")
    print_separator("🏈", 80)
    
    extractor = FootballAnchorExtractor()
    
    text = "He joined last year and signed a 5-year contract on 1 January 2026."
    print(f"\n测试文本: \"{text}\"")
    
    expressions = extractor._extract_time_expressions(text, "2026-01-10")
    print_time_expressions(expressions)
    
    print("\n结构验证:")
    all_valid = True
    
    for i, expr in enumerate(expressions, 1):
        print(f"\n  表达式 {i}:")
        
        # 检查必需字段
        required_fields = ['time_id', 'evidence', 'normalized', 'granularity', 'span']
        for field in required_fields:
            if field in expr:
                print(f"    ✅ {field}: {type(expr[field]).__name__}")
            else:
                print(f"    ❌ 缺失字段: {field}")
                all_valid = False
        
        # 检查类型
        if not isinstance(expr['time_id'], str):
            print(f"    ❌ time_id 应为 str")
            all_valid = False
        
        if not isinstance(expr['evidence'], str):
            print(f"    ❌ evidence 应为 str")
            all_valid = False
        
        if not isinstance(expr['normalized'], str):
            print(f"    ❌ normalized 应为 str")
            all_valid = False
        
        if not isinstance(expr['granularity'], (str, TimeGranularity)):
            print(f"    ❌ granularity 应为 str 或 TimeGranularity")
            all_valid = False
        
        if not isinstance(expr['span'], tuple) or len(expr['span']) != 2:
            print(f"    ❌ span 应为 (start, end) 元组")
            all_valid = False
    
    if all_valid:
        print("\n✅ 所有输出结构符合 schema")
    else:
        print("\n❌ 输出结构存在问题")
    
    print()


def test_real_data_from_json():
    """使用真实 JSON 数据测试时间表达式提取"""
    import json
    
    print_separator("🏈", 80)
    print("测试：使用 Arsenal EFL Cup 真实数据")
    print_separator("🏈", 80)
    
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
        
        # 提取时间表达式
        time_expressions = extractor._extract_time_expressions(text, publish_date)
        
        print(f"\n⏰ 提取到的时间表达式 ({len(time_expressions)} 个):")
        if time_expressions:
            for expr in time_expressions:
                print(f"  [{expr['time_id']}] \"{expr['evidence']}\"")
                print(f"      normalized: {expr['normalized']}")
                print(f"      granularity: {expr['granularity']}")
                print(f"      span: {expr['span']}")
        else:
            print("  (无)")
    
    print(f"{'='*80}")
    print(f"测试完成！")
    print(f"{'='*80}")

def run_all_tests():
    """运行所有测试"""
    print("\n")
    print_separator("🏈", 80)
    print("  _extract_time_expressions 完整测试套件")
    print_separator("🏈", 80)
    print("\n")
    
    test_year_extraction()
    test_month_extraction()
    test_day_extraction()
    test_duration_extraction()
    test_relative_extraction()
    test_mixed_extraction()
    test_edge_cases()
    test_span_deduplication()
    test_output_schema()
    
    print_separator("=", 80)
    print("  ✅ 所有测试完成")
    print_separator("=", 80)
    print()

if __name__ == "__main__":
    # run_all_tests()
    test_real_data_from_json()
    # test_duration_extraction()
    # test_month_extraction()
    # test_mixed_extraction()
    # test_edge_cases()

