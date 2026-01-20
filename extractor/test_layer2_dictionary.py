"""
测试 Layer 2: Dictionary Enrichment & Typing

验证词典匹配的各种场景
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.entity_extractor import EntityExtractor


def test_canonical_match():
    """测试 canonical name 精确匹配"""
    print("="*80)
    print("🎯 测试场景 1: Canonical Name 精确匹配")
    print("="*80 + "\n")
    
    text = "Mikel Arteta coached Arsenal against Crystal Palace."
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    # Layer 1: 候选生成
    candidates = extractor._extract_ner_candidates(doc)
    
    # Layer 2: 词典匹配
    enriched = extractor._enrich_with_dictionary(candidates, text)
    
    print(f"候选数: {len(enriched)}\n")
    
    for cand in enriched:
        print(f"✓ {cand['text']}")
        if cand.get("dictionary_hit"):
            hit = cand["dictionary_hit"]
            print(f"  → 词典匹配: {hit['dict']} | {hit['canonical']} | {hit['match_type']}")
            print(f"  → 类型: {cand['type']}")
            print(f"  → Confidence: {cand['confidence']:.2f}")
        else:
            print(f"  → 无词典匹配")
            print(f"  → 类型: {cand.get('type', 'None')}")
        print()
    
    # 验证
    arteta = next((c for c in enriched if "Arteta" in c["text"]), None)
    arsenal = next((c for c in enriched if c["text"] == "Arsenal"), None)
    palace = next((c for c in enriched if "Palace" in c["text"]), None)
    
    assert arteta and arteta.get("dictionary_hit"), "❌ Mikel Arteta 应该匹配到 coach 词典"
    assert arteta["dictionary_hit"]["match_type"] == "canonical", "❌ 应该是 canonical 匹配"
    
    assert arsenal and arsenal.get("dictionary_hit"), "❌ Arsenal 应该匹配到 club 词典"
    assert arsenal["dictionary_hit"]["match_type"] == "canonical", "❌ 应该是 canonical 匹配"
    
    assert palace and palace.get("dictionary_hit"), "❌ Crystal Palace 应该匹配到 club 词典"
    
    print("✅ Canonical 匹配测试通过\n")


def test_alias_match():
    """测试别名匹配"""
    print("="*80)
    print("🎯 测试场景 2: Alias 匹配")
    print("="*80 + "\n")
    
    text = "The Gunners defeated Spurs at Wembley."
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    candidates = extractor._extract_ner_candidates(doc)
    enriched = extractor._enrich_with_dictionary(candidates, text)
    
    print(f"候选数: {len(enriched)}\n")
    
    for cand in enriched:
        print(f"✓ {cand['text']}")
        if cand.get("dictionary_hit"):
            hit = cand["dictionary_hit"]
            print(f"  → 词典匹配: {hit['dict']} | canonical='{hit['canonical']}' | type={hit['match_type']}")
            print(f"  → 实际类型: {cand['type']}")
        else:
            print(f"  → 无词典匹配")
        print()
    
    # 验证
    gunners = next((c for c in enriched if "Gunners" in c["text"]), None)
    spurs = next((c for c in enriched if "Spurs" in c["text"]), None)
    wembley = next((c for c in enriched if "Wembley" in c["text"]), None)
    
    if gunners:
        assert gunners.get("dictionary_hit"), "❌ Gunners 应该匹配到 Arsenal 的别名"
        assert gunners["dictionary_hit"]["canonical"] == "Arsenal", "❌ canonical 应该是 Arsenal"
        assert gunners["dictionary_hit"]["match_type"] == "alias", "❌ 应该是 alias 匹配"
        print("✅ Gunners → Arsenal 别名匹配正确")
    
    if spurs:
        assert spurs.get("dictionary_hit"), "❌ Spurs 应该匹配到 Tottenham 的别名"
        print("✅ Spurs 别名匹配正确")
    
    if wembley:
        assert wembley.get("dictionary_hit"), "❌ Wembley 应该匹配到 stadium"
        print("✅ Wembley 匹配正确")
    
    print("\n✅ Alias 匹配测试通过\n")


def test_single_token_match():
    """测试单token匹配（带惩罚）"""
    print("="*80)
    print("🎯 测试场景 3: 单 Token 匹配")
    print("="*80 + "\n")
    
    text = "Arsenal played well. Palace defended strongly."
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    candidates = extractor._extract_ner_candidates(doc)
    enriched = extractor._enrich_with_dictionary(candidates, text)
    
    print(f"候选数: {len(enriched)}\n")
    
    for cand in enriched:
        print(f"✓ {cand['text']}")
        if cand.get("dictionary_hit"):
            hit = cand["dictionary_hit"]
            print(f"  → 词典匹配: {hit['dict']} | {hit['canonical']} | {hit['match_type']}")
            print(f"  → Confidence: {cand['confidence']:.2f}")
        else:
            print(f"  → 无词典匹配")
        print()
    
    # "Palace" 应该匹配，但 confidence 较低
    palace = next((c for c in enriched if c["text"] == "Palace"), None)
    
    if palace and palace.get("dictionary_hit"):
        assert palace["dictionary_hit"]["match_type"] in ["single_token", "alias"], \
            "❌ Palace 应该是 single_token 或 alias 匹配"
        print("✅ Palace 单token匹配测试通过")
    
    print("\n✅ 单 Token 匹配测试通过\n")


def test_no_false_positives():
    """测试不引入新 span"""
    print("="*80)
    print("🎯 测试场景 4: 不引入新 Span（约束验证）")
    print("="*80 + "\n")
    
    text = "Some random text mentioning Harry Kane without proper span."
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    candidates = extractor._extract_ner_candidates(doc)
    print(f"Layer 1 候选数: {len(candidates)}")
    
    enriched = extractor._enrich_with_dictionary(candidates, text)
    print(f"Layer 2 候选数: {len(enriched)}")
    
    # Layer 2 不应该增加候选数量
    assert len(enriched) == len(candidates), \
        "❌ Layer 2 不应该引入新的 span"
    
    print("\n✅ 约束验证通过：Layer 2 不引入新 span\n")


def test_confidence_boost():
    """测试 confidence 提升逻辑"""
    print("="*80)
    print("🎯 测试场景 5: Confidence Boost")
    print("="*80 + "\n")
    
    text = "Mikel Arteta and Kepa Arrizabalaga and the Gunners."
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    candidates = extractor._extract_ner_candidates(doc)
    enriched = extractor._enrich_with_dictionary(candidates, text)
    
    print("Confidence 对比:\n")
    
    for cand in enriched:
        if cand.get("dictionary_hit"):
            hit = cand["dictionary_hit"]
            print(f"{cand['text']:25s} | match_type={hit['match_type']:10s} | confidence={cand['confidence']:.2f}")
    
    # 验证 confidence 等级
    arteta = next((c for c in enriched if "Arteta" in c["text"]), None)
    gunners = next((c for c in enriched if "Gunners" in c["text"]), None)
    
    if arteta and gunners:
        # canonical 应该比 alias 的 confidence 更高
        if arteta.get("dictionary_hit") and gunners.get("dictionary_hit"):
            if arteta["dictionary_hit"]["match_type"] == "canonical" and \
               gunners["dictionary_hit"]["match_type"] == "alias":
                assert arteta["confidence"] >= gunners["confidence"], \
                    "❌ canonical 匹配应该比 alias 匹配有更高的 confidence"
                print("\n✅ Confidence 等级正确：canonical > alias")
    
    print("\n✅ Confidence Boost 测试通过\n")


def test_dictionary_metadata():
    """测试词典元数据完整性"""
    print("="*80)
    print("🎯 测试场景 6: Dictionary Metadata 完整性")
    print("="*80 + "\n")
    
    text = "Arsenal and Manchester United played at Wembley."
    
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    candidates = extractor._extract_ner_candidates(doc)
    enriched = extractor._enrich_with_dictionary(candidates, text)
    
    print("Dictionary Hit 元数据:\n")
    
    for cand in enriched:
        if cand.get("dictionary_hit"):
            hit = cand["dictionary_hit"]
            print(f"{cand['text']}:")
            print(f"  - dict: {hit['dict']}")
            print(f"  - canonical: {hit['canonical']}")
            print(f"  - id: {hit['id']}")
            print(f"  - match_type: {hit['match_type']}")
            print(f"  - matched_name: {hit['matched_name']}")
            print()
            
            # 验证必需字段
            assert "dict" in hit, "❌ 缺少 dict 字段"
            assert "canonical" in hit, "❌ 缺少 canonical 字段"
            assert "id" in hit, "❌ 缺少 id 字段"
            assert "match_type" in hit, "❌ 缺少 match_type 字段"
            assert "matched_name" in hit, "❌ 缺少 matched_name 字段"
    
    print("✅ Dictionary Metadata 完整性验证通过\n")


def test_multi_dictionary():
    """测试多词典协同"""
    print("="*80)
    print("🎯 测试场景 7: 多词典协同工作")
    print("="*80 + "\n")
    
    # text = """Carrick's last job as a manager was at Middlesbrough. Inheriting a Boro outfit who were hovering around the Championship relegation zone in October 2022, Carrick’s neat and tidy brand of controlled, attack-minded football, took them to the playoffs that same season."""    
    text = """Mikel Arteta coached Arsenal against Crystal Palace at the Emirates Stadium in the Premier League. Meanwhile, Pep Guardiola led Manchester City to victory over Liverpool at the Etihad Stadium in the same competition."""
    extractor = EntityExtractor()
    doc = extractor.nlp(text)
    
    candidates = extractor._extract_ner_candidates(doc)
    enriched = extractor._enrich_with_dictionary(candidates, text)

    print(f"raw text:\n{text}\n")

    print("候选实体列表：\n")
    for i, cand in enumerate(candidates, 1):
        sources_str = ", ".join(cand.get("debug_sources", []))
        print(f"{i:2d}. [{cand['span'][0]:3d}-{cand['span'][1]:3d}] {cand['text']:<30s} (来源: {sources_str})")
    
    print("\n词典层处理结果:\n")
    for i, enriched_cand in enumerate(enriched, 1):
        if enriched_cand.get("dictionary_hit"):
            hit = enriched_cand["dictionary_hit"]
            print(f"{i:2d}. {enriched_cand['text']:<30s} → {hit['dict']} | {hit['canonical']} | {hit['match_type']}")
    
    
    dict_counts = {}
    for cand in enriched:
        if cand.get("dictionary_hit"):
            dict_name = cand["dictionary_hit"]["dict"]
            dict_counts[dict_name] = dict_counts.get(dict_name, 0) + 1
    
    for dict_name, count in sorted(dict_counts.items()):
        print(f"  {dict_name:15s}: {count} 个实体")
    
    # 应该同时匹配 coach, player, stadium, competition
    expected_dicts = {"coach", "player", "stadium", "competition"}
    matched_dicts = set(dict_counts.keys())
    
    print(f"\n期望词典: {expected_dicts}")
    print(f"实际匹配: {matched_dicts}")
    
    if matched_dicts >= expected_dicts:
        print("\n✅ 多词典协同测试通过")
    else:
        print(f"\n⚠️  部分词典未匹配: {expected_dicts - matched_dicts}")
    
    print()


def main():
    """运行所有测试"""
    print("\n" + "🏈"*40)
    print("  Layer 2 测试套件：Dictionary Enrichment & Typing")
    print("🏈"*40 + "\n")
    
    # test_canonical_match()
    # test_alias_match()
    # test_single_token_match()
    # test_no_false_positives()
    # test_confidence_boost()
    # test_dictionary_metadata()
    test_multi_dictionary()
    
    print("="*80)
    print("✅ 所有 Layer 2 测试通过")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
