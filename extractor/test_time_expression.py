#!/usr/bin/env python3
"""
时间表达式提取器测试
"""

from time_expression_extractor import TimeExpressionExtractor, TimeGranularity


def test_time_expressions():
    """测试时间表达式提取功能"""
    
    extractor = TimeExpressionExtractor()
    
    # 测试用例集合
    test_cases = [
        # Case 1: 完整日期
        {
            "name": "完整日期 - 多种格式",
            "text": "The match was on 1 September 2025. Arsenal played on September 15, 2025. Transfer window closes on 2025-08-31.",
            "publish_date": "2025-09-20",
            "expected_count": 3,
            "expected_granularity": [TimeGranularity.DAY, TimeGranularity.DAY, TimeGranularity.DAY]
        },
        
        # Case 2: 日期+月份（无年份）
        {
            "name": "日期+月份（补全年份）",
            "text": "The signing happened on 14 January. Match scheduled for 25 December.",
            "publish_date": "2025-09-20",
            "expected_count": 2,
            "expected_granularity": [TimeGranularity.DAY, TimeGranularity.DAY]
        },
        
        # Case 3: 年月
        {
            "name": "年月表达式",
            "text": "He joined in September 2025. The team struggled during March 2023.",
            "publish_date": "2025-09-20",
            "expected_count": 2,
            "expected_granularity": [TimeGranularity.MONTH, TimeGranularity.MONTH]
        },
        
        # Case 4: 年份
        {
            "name": "年份表达式",
            "text": "He played in 2021. The 2022 season was great. They competed in 2003/04 season.",
            "publish_date": "2025-09-20",
            "expected_count": 3,
            "expected_granularity": [TimeGranularity.YEAR, TimeGranularity.YEAR, TimeGranularity.YEAR]
        },
        
        # Case 5: 相对时间 - 方向型
        {
            "name": "相对时间 - 方向型",
            "text": "He left last year. The transfer happened last season. Next summer will be crucial. This week is important.",
            "publish_date": "2025-09-20",
            "expected_count": 4,
            "expected_granularity": [TimeGranularity.RELATIVE] * 4
        },
        
        # Case 6: 相对时间 - 单词型
        {
            "name": "相对时间 - 单词型",
            "text": "The game is tomorrow. Yesterday we lost. Today's match is crucial.",
            "publish_date": "2025-09-20",
            "expected_count": 3,
            "expected_granularity": [TimeGranularity.RELATIVE] * 3
        },
        
        # Case 7: 相对时间 - 星期几
        {
            "name": "相对时间 - 星期几",
            "text": "Training on Monday morning. Match on Friday. Last Tuesday was tough. Next Sunday we play.",
            "publish_date": "2025-09-20",
            "expected_count": 4,
            "expected_granularity": [TimeGranularity.RELATIVE] * 4
        },
        
        # Case 8: 相对时间 - 数字型
        {
            "name": "相对时间 - 数字型",
            "text": "He signed 2 years ago. The club was founded 50 years ago. 3 months ago they won.",
            "publish_date": "2025-09-20",
            "expected_count": 3,
            "expected_granularity": [TimeGranularity.RELATIVE] * 3
        },
        
        # Case 9: Duration - 合同
        {
            "name": "Duration - 合同",
            "text": "He signed a five-year deal. The four-and-a-half year contract expires soon. A 3 years contract was offered.",
            "publish_date": "2025-09-20",
            "expected_count": 3,
            "expected_granularity": [TimeGranularity.DURATION] * 3
        },
        
        # Case 10: Duration - 时间跨度
        {
            "name": "Duration - 时间跨度",
            "text": "The loan will last in five years. They have been together for 2 months. The ban is effective within 3 weeks.",
            "publish_date": "2025-09-20",
            "expected_count": 3,
            "expected_granularity": [TimeGranularity.DURATION] * 3
        },
        
        # Case 11: 混合测试（真实足球新闻）
        {
            "name": "混合 - 真实转会新闻",
            "text": """
            Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United.
            The defender signs a five-year deal until June 2029, joining on 14 January.
            De Ligt, who played 73 times for Bayern since joining in 2022, reunites with 
            Erik ten Hag. The transfer was finalized yesterday after weeks of negotiations.
            """,
            "publish_date": "2025-01-15",
            "expected_count": 5,  # five-year, June 2029, 14 January, 2022, yesterday
            "expected_granularity": None  # 混合粒度
        },
        
        # Case 12: 混合测试（比赛报道）
        {
            "name": "混合 - 比赛报道",
            "text": """
            Arsenal beat Crystal Palace 5-1 on Monday evening. Saka scored twice in the 
            first half. This season Arsenal has been dominant. Last week they also won 
            3-0. The team will face Liverpool next Sunday.
            """,
            "publish_date": "2025-09-20",
            "expected_count": 4,  # Monday evening, This season, Last week, next Sunday
            "expected_granularity": None
        },
    ]
    
    # 运行测试
    print("=" * 100)
    print("时间表达式提取器测试")
    print("=" * 100)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 100}")
        print(f"测试用例 {i}: {test_case['name']}")
        print("-" * 100)
        print(f"文本: {test_case['text'][:200]}{'...' if len(test_case['text']) > 200 else ''}")
        print(f"发布日期: {test_case['publish_date']}")
        print()
        
        # 执行提取
        results = extractor.extract_time_expressions(
            test_case['text'], 
            test_case['publish_date']
        )
        
        # 显示结果
        print(f"提取结果 (共 {len(results)} 个):")
        for result in results:
            print(f"  [{result['time_id']}] {result['evidence']:40} → {result['normalized']:25} ({result['granularity'].value})")
        
        # 验证
        expected_count = test_case['expected_count']
        actual_count = len(results)
        
        if actual_count == expected_count:
            print(f"\n✅ 通过 - 提取数量正确: {actual_count}/{expected_count}")
            
            # 检查粒度（如果指定）
            if test_case['expected_granularity']:
                granularities = [r['granularity'] for r in results]
                if granularities == test_case['expected_granularity']:
                    print(f"✅ 粒度检查通过")
                    passed += 1
                else:
                    print(f"⚠️  粒度检查未通过")
                    print(f"   期望: {[g.value for g in test_case['expected_granularity']]}")
                    print(f"   实际: {[g.value for g in granularities]}")
                    failed += 1
            else:
                passed += 1
        else:
            print(f"\n❌ 失败 - 提取数量不匹配: {actual_count}/{expected_count}")
            failed += 1
    
    # 汇总
    print("\n" + "=" * 100)
    print(f"测试汇总: {passed} 通过, {failed} 失败")
    print("=" * 100)
    
    return passed, failed


def test_edge_cases():
    """测试边界情况"""
    
    extractor = TimeExpressionExtractor()
    
    print("\n" + "=" * 100)
    print("边界情况测试")
    print("=" * 100)
    
    edge_cases = [
        {
            "name": "重叠时间表达式",
            "text": "The 2021 season started in September 2021 on 1 September 2021.",
            "publish_date": "2025-09-20",
        },
        {
            "name": "嵌套时间表达式",
            "text": "He signed a five-year deal in 2020 that expires next year.",
            "publish_date": "2025-09-20",
        },
        {
            "name": "无时间表达式",
            "text": "The player is very talented and skillful.",
            "publish_date": "2025-09-20",
        },
        {
            "name": "特殊字符和格式",
            "text": "Match date: 2025-09-01. Contract: five-year. Duration: 3 years ago.",
            "publish_date": "2025-09-20",
        },
    ]
    
    for i, case in enumerate(edge_cases, 1):
        print(f"\n边界测试 {i}: {case['name']}")
        print("-" * 100)
        print(f"文本: {case['text']}")
        
        results = extractor.extract_time_expressions(case['text'], case['publish_date'])
        
        print(f"提取结果 (共 {len(results)} 个):")
        for result in results:
            print(f"  [{result['time_id']}] {result['evidence']:30} → {result['normalized']:20} ({result['granularity'].value}) span:{result['span']}")
    
    print("\n" + "=" * 100)


def test_normalization():
    """测试日期标准化"""
    
    extractor = TimeExpressionExtractor()
    
    print("\n" + "=" * 100)
    print("日期标准化测试")
    print("=" * 100)
    
    test_dates = [
        ("1 September 2025", "2025-09-01"),
        ("September 1, 2025", "2025-09-01"),
        ("September 1 2025", "2025-09-01"),
        ("2025-09-01", "2025-09-01"),
        ("invalid date", None),
    ]
    
    passed = 0
    failed = 0
    
    for input_date, expected in test_dates:
        result = extractor._normalize_date(input_date)
        if result == expected:
            print(f"✅ {input_date:30} → {result}")
            passed += 1
        else:
            print(f"❌ {input_date:30} → {result} (期望: {expected})")
            failed += 1
    
    print(f"\n标准化测试: {passed} 通过, {failed} 失败")
    print("=" * 100)


if __name__ == "__main__":
    # 运行主测试
    passed, failed = test_time_expressions()
    
    # 运行边界测试
    test_edge_cases()
    
    # 运行标准化测试
    test_normalization()
    
    print("\n" + "=" * 100)
    print("所有测试完成!")
    print("=" * 100)
