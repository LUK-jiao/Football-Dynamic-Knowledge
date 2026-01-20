#!/usr/bin/env python3
"""
Layer 3 Syntax Reasoning 验证测试
"""
import json
from entity_extractor import EntityExtractor

def main():
    # 初始化提取器
    extractor = EntityExtractor()
    
    # 测试文本（来自用户需求）
    # test_text = """
    # Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals after 
    # Kepa saving the spot-kick taken by Maxence Lacroix. The goalkeeper made 
    # crucial saves throughout the match.
    # """
    test_text = """Carrick's last job as a manager was at Middlesbrough. Inheriting a Boro outfit who were hovering around the Championship relegation zone in October 2022, Carrick’s neat and tidy brand of controlled, attack-minded football, took them to the playoffs that same season."""    

    
    print("=" * 80)
    print("Layer 3 Syntax Reasoning Test")
    print("=" * 80)
    print(f"\n测试文本:\n{test_text.strip()}\n")
    
    # 执行提取
    results = extractor.extract_participants(test_text)
    
    # 打印结果
    print("\n提取结果:")
    print("-" * 80)
    
    # 检查返回格式
    if results and isinstance(results[0], dict):
        # 新格式
        if 'text' in results[0]:
            for entity in results:
                print(f"\n实体: {entity['text']}")
                print(f"  类型: {entity['type']}")
                print(f"  置信度: {entity['confidence']:.2f}")
                print(f"  来源:")
                print(f"    - NER: {entity['source'].get('ner', False)}")
                print(f"    - Dictionary: {entity['source'].get('dictionary', False)}")
                print(f"    - Syntax: {entity['source'].get('syntax', False)}")
                
                if entity.get('syntax_evidence'):
                    print(f"  语法证据: {', '.join(entity['syntax_evidence'])}")
                
                if entity.get('dictionary_hit'):
                    print(f"  词典命中: {entity['dictionary_hit']['dict']} - {entity['dictionary_hit']['match_type']}")
        else:
            # 旧格式 {"type": str, "name": str}
            for entity in results:
                print(f"  {entity.get('name', entity.get('text', 'Unknown'))}: {entity.get('type', 'UNKNOWN')}")
    else:
        print("  无结果或格式异常")
        print(f"  返回类型: {type(results)}")
        if results:
            print(f"  首个元素: {results[0]}")
    
    print("\n" + "=" * 80)
    print("验证目标:")
    print("-" * 80)
    
    # 处理返回格式差异
    if results and isinstance(results[0], dict):
        if 'text' in results[0]:
            results_by_text = {e['text']: e for e in results}
        elif 'name' in results[0]:
            # 旧格式 {"type": str, "name": str}
            results_by_text = {e['name']: e for e in results}
        else:
            print("无法识别的结果格式")
            return
    else:
        print("结果为空或格式错误")
        return
    
    checks = [
        ("Arsenal", "Club"),
        ("Mikel Arteta", "Coach"),
        ("Kepa", "Player"),
        ("Maxence Lacroix", "Player"),
        ("EFL Cup", "Tournament"),
    ]
    
    passed = 0
    failed = 0
    
    for text, expected_type in checks:
        if text in results_by_text:
            entity = results_by_text[text]
            actual_type = entity.get('type', 'UNKNOWN')
            type_match = actual_type.lower() == expected_type.lower()
            
            status = "✓" if type_match else "✗"
            if type_match:
                passed += 1
            else:
                failed += 1
            
            print(f"{status} {text:20} → {actual_type:12} (期望: {expected_type:12})")
        else:
            failed += 1
            print(f"✗ {text:20} → 未提取 (期望: {expected_type})")
    
    print("-" * 80)
    print(f"通过: {passed}/{len(checks)}")
    print(f"失败: {failed}/{len(checks)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
