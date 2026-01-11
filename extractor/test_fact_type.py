#!/usr/bin/env python3
"""
Fact Type 判定功能测试

测试重点：
1. EVENT vs STATE 的正确判定
2. need_resolver 的正确判定
3. 各种边界情况
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from extractor.ner import FootballAnchorExtractor


def print_section(title: str):
    """打印分段标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_case(extractor: FootballAnchorExtractor, 
              text: str, 
              expected_fact_type: str,
              expected_need_resolver: bool,
              case_name: str):
    """
    单个测试案例
    
    Args:
        extractor: 抽取器实例
        text: 测试文本
        expected_fact_type: 期望的 fact_type
        expected_need_resolver: 期望的 need_resolver
        case_name: 测试案例名称
    """
    print(f"\n{'─' * 80}")
    print(f"测试案例: {case_name}")
    print(f"{'─' * 80}")
    
    chunk = {
        "block_id": "test_001",
        "text": text,
        "source": "Test Source",
        "publish_date": "2025-08-23"
    }
    
    result = extractor.extract_anchors(chunk)
    
    actual_fact_type = result.get("fact_type")
    actual_need_resolver = result.get("need_resolver")
    
    print(f"\n📝 输入文本:")
    print(f"  {text}")
    
    print(f"\n📊 判定结果:")
    print(f"  fact_type: {actual_fact_type}")
    print(f"  need_resolver: {actual_need_resolver}")
    
    print(f"\n🎯 期望结果:")
    print(f"  fact_type: {expected_fact_type}")
    print(f"  need_resolver: {expected_need_resolver}")
    
    # 显示锚点信息（辅助调试）
    print(f"\n🔍 锚点详情:")
    anchors = result.get("anchors", {})
    
    temporal = anchors.get("temporal_anchors", [])
    print(f"  时间锚点 ({len(temporal)} 个):")
    for t in temporal:
        print(f"    - event_date: {t.get('event_date')}, "
              f"valid_from: {t.get('valid_from')}, "
              f"valid_to: {t.get('valid_to')}, "
              f"type: {t.get('time_type')}")
    
    constraints_list = anchors.get("constraints", [])
    print(f"  约束锚点 ({len(constraints_list)} 个):")
    for c in constraints_list:
        print(f"    - {c.get('type')}: {c.get('subject')} → {c.get('expected_state')}")
    
    # 验证结果
    fact_type_pass = actual_fact_type == expected_fact_type
    need_resolver_pass = actual_need_resolver == expected_need_resolver
    
    if fact_type_pass and need_resolver_pass:
        print(f"\n✅ 测试通过")
        return True
    else:
        print(f"\n❌ 测试失败")
        if not fact_type_pass:
            print(f"  - fact_type 不匹配: 期望 {expected_fact_type}, 实际 {actual_fact_type}")
        if not need_resolver_pass:
            print(f"  - need_resolver 不匹配: 期望 {expected_need_resolver}, 实际 {actual_need_resolver}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("  Fact Type 判定功能测试套件")
    print("🧪" * 40)
    
    extractor = FootballAnchorExtractor()
    results = []
    
    # ========================================================================
    # 分组 1: EVENT 类型（明确历史事件）
    # ========================================================================
    print_section("分组 1: EVENT 类型测试")
    
    # 测试 1.1: 转会完成（明确时间点 + 过去时）
    results.append(test_case(
        extractor,
        text="De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
        expected_fact_type="EVENT",
        expected_need_resolver=False,
        case_name="1.1 转会完成（明确时间点）"
    ))
    
    # 测试 1.2: 历史进球（明确时间点 + 过去时）
    results.append(test_case(
        extractor,
        text="Castellanos scored four goals in a single game for Girona against Real Madrid in La Liga in 2023.",
        expected_fact_type="EVENT",
        expected_need_resolver=False,
        case_name="1.2 历史进球（明确年份）"
    ))
    
    # 测试 1.3: 比赛结果（比分 + 过去时）
    results.append(test_case(
        extractor,
        text="Arsenal won 3-2 against Chelsea in the Premier League on 14 January.",
        expected_fact_type="EVENT",
        expected_need_resolver=False,
        case_name="1.3 比赛结果（比分状态）"
    ))
    
    # 测试 1.4: 赛季成就（历史时间 + 完成时）
    results.append(test_case(
        extractor,
        text="Castellanos won the MLS Cup and Golden Boot with New York City FC in 2021.",
        expected_fact_type="EVENT",
        expected_need_resolver=False,
        case_name="1.4 赛季成就（历史年份）"
    ))
    
    # ========================================================================
    # 分组 2: STATE 类型（当前状态）
    # ========================================================================
    print_section("分组 2: STATE 类型测试")
    
    # 测试 2.1: 教练身份（现在时 + 无明确时间）
    results.append(test_case(
        extractor,
        text="Amorim is the head coach of Manchester United.",
        expected_fact_type="STATE",
        expected_need_resolver=True,  # 没有有效期，需要 resolver
        case_name="2.1 教练身份（现在时状态）"
    ))
    
    # 测试 2.2: 合同状态（现在时 + 无明确时间）
    results.append(test_case(
        extractor,
        text="De Ligt is under contract with Bayern Munich.",
        expected_fact_type="STATE",
        expected_need_resolver=True,  # 没有有效期，需要 resolver
        case_name="2.2 合同状态（无到期日期）"
    ))
    
    # 测试 2.3: 伤病状态（现在时 + 无明确时间）
    results.append(test_case(
        extractor,
        text="Salah is currently injured and unavailable for selection.",
        expected_fact_type="STATE",
        expected_need_resolver=True,  # 没有有效期，需要 resolver
        case_name="2.3 伤病状态（当前伤病）"
    ))
    
    # 测试 2.4: 球员身份（现在时 + remains）
    results.append(test_case(
        extractor,
        text="Ronaldo remains a key player for Al Nassr.",
        expected_fact_type="STATE",
        expected_need_resolver=True,  # 没有有效期，需要 resolver
        case_name="2.4 球员身份（remains 关键词）"
    ))
    
    # ========================================================================
    # 分组 3: STATE + 明确有效期（不需要 resolver）
    # ========================================================================
    print_section("分组 3: STATE 类型（有明确有效期）")
    
    # 测试 3.1: 合同到期日（STATE + valid_to）
    results.append(test_case(
        extractor,
        text="He signed a four-and-a-half year contract until 2028.",
        expected_fact_type="STATE",  # 合同状态是 STATE
        expected_need_resolver=False,  # 有 valid_to，不需要 resolver
        case_name="3.1 合同到期日（until 2028）"
    ))
    
    # 测试 3.2: 租借期限（STATE + valid_from + valid_to）
    results.append(test_case(
        extractor,
        text="The loan deal runs from January 2026 until June 2026.",
        expected_fact_type="STATE",
        expected_need_resolver=False,  # 有完整区间，不需要 resolver
        case_name="3.2 租借期限（明确起止时间）"
    ))
    
    # ========================================================================
    # 分组 4: 边界情况
    # ========================================================================
    print_section("分组 4: 边界情况测试")
    
    # 测试 4.1: 转会传闻（过去时 agreed，但后续可能变化）
    results.append(test_case(
        extractor,
        text="Manchester United have agreed a deal to sign De Ligt.",
        expected_fact_type="EVENT",  # 协议达成是历史事件
        expected_need_resolver=False,
        case_name="4.1 转会协议达成（have agreed）"
    ))
    
    # 测试 4.2: 伤病报告（过去时 suffered + 明确时间）
    results.append(test_case(
        extractor,
        text="Salah suffered a hamstring injury during training yesterday.",
        expected_fact_type="EVENT",  # 受伤是历史事件
        expected_need_resolver=False,
        case_name="4.2 伤病报告（yesterday）"
    ))
    
    # 测试 4.3: 停赛宣布（过去时 announced + 明确时间）
    results.append(test_case(
        extractor,
        text="The FA announced a three-match ban for the player on Monday.",
        expected_fact_type="EVENT",  # 宣布是历史事件
        expected_need_resolver=False,
        case_name="4.3 停赛宣布（on Monday）"
    ))
    
    # 测试 4.4: 混合描述（历史 + 状态）
    results.append(test_case(
        extractor,
        text="He signed with Manchester United in 2021 and is currently the captain.",
        expected_fact_type="EVENT",  # 主导是签约事件（明确时间）
        expected_need_resolver=False,
        case_name="4.4 混合描述（历史签约）"
    ))
    
    # ========================================================================
    # 统计结果
    # ========================================================================
    print_section("测试总结")
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\n📊 测试统计:")
    print(f"  总计: {total} 个测试")
    print(f"  通过: {passed} 个 ✅")
    print(f"  失败: {failed} 个 ❌")
    print(f"  通过率: {passed/total*100:.1f}%")
    
    if failed == 0:
        print(f"\n🎉 所有测试通过！fact_type 判定功能正常工作。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查判定逻辑。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
