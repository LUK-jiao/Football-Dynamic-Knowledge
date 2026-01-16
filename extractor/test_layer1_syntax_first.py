"""
测试 Layer 1: Syntax-First Entity Candidate Generation

验证语法优先的实体候选生成层
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.entity_extractor import EntityExtractor


def test_mandatory_case():
    """🎯 强制测试案例"""
    print("="*80)
    print("🎯 强制测试案例：语法优先实体候选生成")
    print("="*80)
    
    text = """Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals
by winning on penalties against Crystal Palace, with Kepa Arrizabalaga
saving the decisive spot-kick taken by Maxence Lacroix."""
    
    print(f"\n📝 测试文本:\n{text}\n")
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    # 调用第一层
    candidates = extractor._extract_ner_candidates(doc)
    
    print(f"📊 第一层生成候选数: {len(candidates)}\n")
    
    # 按 span 排序
    candidates.sort(key=lambda x: x["span"][0])
    
    print("候选实体列表：\n")
    for i, cand in enumerate(candidates, 1):
        sources_str = ", ".join(cand.get("debug_sources", []))
        print(f"{i:2d}. [{cand['span'][0]:3d}-{cand['span'][1]:3d}] {cand['text']:<30s} (来源: {sources_str})")
    
    # 验证期望候选
    print("\n" + "="*80)
    print("✅ 验证期望候选")
    print("="*80 + "\n")
    
    expected_candidates = [
        "Mikel Arteta",
        "Arsenal",
        "Arsenal side",
        "EFL Cup",
        "EFL Cup semi-finals",
        "Crystal Palace",
        "Kepa Arrizabalaga",
        "Maxence Lacroix",
    ]
    
    candidate_texts = [c["text"] for c in candidates]
    
    all_found = True
    for expected in expected_candidates:
        if expected in candidate_texts:
            print(f"  ✅ {expected}")
        else:
            print(f"  ❌ {expected} (未找到)")
            all_found = False
    
    if all_found:
        print("\n🎉 所有期望候选都已生成！")
    else:
        print("\n⚠️ 部分期望候选缺失")
    
    return all_found


def test_rule_coverage():
    """测试各规则覆盖情况"""
    print("\n" + "="*80)
    print("📋 测试各规则覆盖情况")
    print("="*80 + "\n")
    
    text = """Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals
by winning on penalties against Crystal Palace, with Kepa Arrizabalaga
saving the decisive spot-kick taken by Maxence Lacroix."""
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    candidates = extractor._extract_ner_candidates(doc)
    
    # 统计各规则生成的候选数
    rule_stats = {}
    for cand in candidates:
        for source in cand.get("debug_sources", []):
            rule_stats[source] = rule_stats.get(source, 0) + 1
    
    print("各规则生成的候选数：\n")
    for rule, count in sorted(rule_stats.items(), key=lambda x: -x[1]):
        print(f"  {rule:<30s}: {count:2d} 个候选")
    
    print(f"\n总计: {len(candidates)} 个候选")


def test_specific_rules():
    """测试特定规则"""
    print("\n" + "="*80)
    print("🔍 测试特定规则")
    print("="*80)
    
    test_cases = [
        {
            "name": "Rule 1: 连续 PROPN",
            "text": "Kepa Arrizabalaga saved the penalty.",
            "expected": ["Kepa Arrizabalaga"],
            "rule": "continuous_propn"
        },
        {
            "name": "Rule 2: PROPN + NOUN",
            "text": "Arsenal side won the match.",
            "expected": ["Arsenal side"],
            "rule": "propn_noun_compound"
        },
        {
            "name": "Rule 3: 所有格 (poss)",
            "text": "Pep Guardiola's team played well.",
            "expected": ["Pep Guardiola"],
            "rule": "possessive_poss"
        },
        {
            "name": "Rule 4: 介词宾语 (pobj)",
            "text": "They won against Arsenal.",
            "expected": ["Arsenal"],
            "rule": "pobj_against"
        },
        {
            "name": "Rule 5: 主语 (nsubj)",
            "text": "Mohamed Salah scored twice.",
            "expected": ["Mohamed Salah"],
            "rule": "subj_obj_nsubj"
        },
        {
            "name": "Rule 6: noun_chunk",
            "text": "The Champions League final was exciting.",
            "expected": ["The Champions League"],
            "rule": "noun_chunk"
        },
    ]
    
    extractor = EntityExtractor()
    
    for case in test_cases:
        print(f"\n{case['name']}")
        print(f"  文本: {case['text']}")
        
        doc = extractor.nlp(case["text"])
        candidates = extractor._extract_ner_candidates(doc)
        
        # 找到包含目标规则的候选
        rule_candidates = []
        for cand in candidates:
            if case["rule"] in cand.get("debug_sources", []):
                rule_candidates.append(cand["text"])
        
        print(f"  期望: {case['expected']}")
        print(f"  提取: {rule_candidates}")
        
        # 验证
        found = any(exp in rule_candidates for exp in case["expected"])
        print(f"  结果: {'✅ 通过' if found else '❌ 失败'}")


def test_deduplication():
    """测试去重逻辑"""
    print("\n" + "="*80)
    print("🔄 测试去重逻辑")
    print("="*80 + "\n")
    
    text = "Arsenal played against Arsenal. Arsenal won."
    
    print(f"文本: {text}")
    print("(同一个实体 'Arsenal' 出现三次，不同位置)\n")
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    candidates = extractor._extract_ner_candidates(doc)
    
    # 统计 "Arsenal" 出现次数
    arsenal_candidates = [c for c in candidates if c["text"] == "Arsenal"]
    arsenal_count = len(arsenal_candidates)
    
    print(f"候选中 'Arsenal' 的数量: {arsenal_count}")
    
    if arsenal_count == 3:
        print("✅ 正确：三次出现都被提取（span 位置不同）")
    else:
        print(f"⚠️ 实际提取了 {arsenal_count} 次")
    
    # 显示所有候选
    print("\n所有候选：")
    for c in candidates:
        sources_str = ", ".join(c.get("debug_sources", []))
        print(f"  [{c['span'][0]:2d}-{c['span'][1]:2d}] {c['text']:<30s} (来源: {sources_str})")


def test_no_dictionary_dependency():
    """验证第一层不依赖词典"""
    print("\n" + "="*80)
    print("🚫 验证第一层不依赖词典")
    print("="*80 + "\n")
    
    # 使用一个完全不在词典中的名字
    text = "Xavi Hernandez's Barcelona team won the match."
    
    print(f"文本: {text}")
    print("(Xavi Hernandez 不在 person_dict 中)\n")
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    candidates = extractor._extract_ner_candidates(doc)
    
    # 检查是否提取到 "Xavi Hernandez"
    found = any("Xavi" in c["text"] for c in candidates)
    
    print("提取的候选：")
    for c in candidates:
        print(f"  - {c['text']} (来源: {', '.join(c.get('debug_sources', []))})")
    
    if found:
        print("\n✅ 正确：即使不在词典中，也能基于语法提取")
    else:
        print("\n❌ 失败：未能提取不在词典中的实体")


def main():
    """运行所有测试"""
    print("\n" + "🏈"*40)
    print("  Layer 1 测试套件：Syntax-First Entity Candidate Generation")
    print("🏈"*40)
    
    # 强制测试
    mandatory_passed = test_mandatory_case()
    
    # 规则覆盖
    test_rule_coverage()
    
    # 特定规则测试
    test_specific_rules()
    
    # 去重测试
    test_deduplication()
    
    # 词典独立性测试
    test_no_dictionary_dependency()
    
    print("\n" + "="*80)
    if mandatory_passed:
        print("✅ 强制测试通过 - Layer 1 语法优先实体候选生成正常工作")
    else:
        print("❌ 强制测试失败 - 需要修复规则")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
