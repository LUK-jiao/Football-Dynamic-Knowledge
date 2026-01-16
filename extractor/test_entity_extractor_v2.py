"""
测试 EntityExtractor v2 (三层架构)

验证 spaCy + Dictionary + Syntax 混合方案
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.entity_extractor import EntityExtractor, EntityType


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_mandatory_example():
    """🎯 强制测试案例（来自需求文档）"""
    print_section("🎯 强制测试案例")
    
    text = """
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals
    by winning on penalties against Crystal Palace, with Kepa Arrizabalaga
    saving the decisive spot-kick taken by Maxence Lacroix.
    """
    
    print(f"📝 测试文本:\n{text}\n")
    
    extractor = EntityExtractor()
    entities = extractor.extract_participants(text)
    
    print("📊 提取结果:\n")
    for entity in entities:
        print(f"  [{entity['type']}] {entity['name']}")
    
    # 期望输出
    expected = {
        "Mikel Arteta": EntityType.COACH,
        "Arsenal": EntityType.CLUB,
        "EFL Cup": EntityType.TOURNAMENT,
        "Crystal Palace": EntityType.CLUB,
        "Kepa Arrizabalaga": EntityType.PLAYER,
        "Maxence Lacroix": EntityType.PLAYER,
    }
    
    print("\n✅ 验证期望输出:\n")
    
    all_passed = True
    entity_map = {e["name"]: e["type"] for e in entities}
    
    for name, expected_type in expected.items():
        if name in entity_map:
            actual_type = entity_map[name]
            passed = actual_type == expected_type
            status = "✅" if passed else "❌"
            print(f"  {status} {name}: 期望={expected_type}, 实际={actual_type}")
            if not passed:
                all_passed = False
        else:
            print(f"  ❌ {name}: 期望={expected_type}, 实际=未提取")
            all_passed = False
    
    print(f"\n{'🎉 全部通过！' if all_passed else '⚠️ 部分失败'}")
    return all_passed


def test_coach_detection():
    """测试 Coach 识别（语法规则）"""
    print_section("测试 1: Coach 识别（Syntax Reasoning）")
    
    test_cases = [
        {
            "name": "所有格模式: Arteta's Arsenal side",
            "text": "Mikel Arteta's Arsenal side won the match.",
            "expected_coach": "Mikel Arteta"
        },
        {
            "name": "修饰模式: manager Pep Guardiola",
            "text": "Manager Pep Guardiola spoke after the game.",
            "expected_coach": "Pep Guardiola"
        },
        {
            "name": "修饰模式: coach Carlo Ancelotti",
            "text": "The club appointed coach Carlo Ancelotti.",
            "expected_coach": "Carlo Ancelotti"
        },
    ]
    
    extractor = EntityExtractor()
    
    for i, case in enumerate(test_cases, 1):
        print(f"案例 {i}: {case['name']}")
        print(f"  文本: {case['text']}")
        
        entities = extractor.extract_participants(case["text"])
        coaches = [e["name"] for e in entities if e["type"] == EntityType.COACH]
        
        expected = case["expected_coach"]
        passed = expected in coaches
        
        print(f"  期望: {expected}")
        print(f"  提取: {coaches}")
        print(f"  结果: {'✅ 通过' if passed else '❌ 失败'}\n")


def test_player_detection():
    """测试 Player 识别（语法规则）"""
    print_section("测试 2: Player 识别（Match Action Verbs）")
    
    test_cases = [
        {
            "name": "动词主语: Kepa saving",
            "text": "Kepa Arrizabalaga saving the decisive spot-kick.",
            "expected_player": "Kepa Arrizabalaga"
        },
        {
            "name": "被动语态: taken by Maxence",
            "text": "The spot-kick taken by Maxence Lacroix.",
            "expected_player": "Maxence Lacroix"
        },
        {
            "name": "主动动词: Salah scored",
            "text": "Mohamed Salah scored twice in the match.",
            "expected_player": "Mohamed Salah"
        },
    ]
    
    extractor = EntityExtractor()
    
    for i, case in enumerate(test_cases, 1):
        print(f"案例 {i}: {case['name']}")
        print(f"  文本: {case['text']}")
        
        entities = extractor.extract_participants(case["text"])
        players = [e["name"] for e in entities if e["type"] == EntityType.PLAYER]
        
        expected = case["expected_player"]
        passed = expected in players
        
        print(f"  期望: {expected}")
        print(f"  提取: {players}")
        print(f"  结果: {'✅ 通过' if passed else '❌ 失败'}\n")


def test_tournament_detection():
    """测试 Tournament 识别（结构规则）"""
    print_section("测试 3: Tournament 识别（Structure Pattern）")
    
    test_cases = [
        {
            "name": "关键词: EFL Cup",
            "text": "Arsenal won the EFL Cup semi-finals.",
            "expected_tournament": "EFL Cup"
        },
        {
            "name": "修饰语: Champions League final",
            "text": "The Champions League final will be in Munich.",
            "expected_tournament": "Champions League"
        },
        {
            "name": "关键词: Premier League",
            "text": "Manchester City leads the Premier League.",
            "expected_tournament": "Premier League"
        },
    ]
    
    extractor = EntityExtractor()
    
    for i, case in enumerate(test_cases, 1):
        print(f"案例 {i}: {case['name']}")
        print(f"  文本: {case['text']}")
        
        entities = extractor.extract_participants(case["text"])
        tournaments = [e["name"] for e in entities if e["type"] == EntityType.TOURNAMENT]
        
        expected = case["expected_tournament"]
        passed = expected in tournaments
        
        print(f"  期望: {expected}")
        print(f"  提取: {tournaments}")
        print(f"  结果: {'✅ 通过' if passed else '❌ 失败'}\n")


def test_club_detection():
    """测试 Club 识别（Dictionary）"""
    print_section("测试 4: Club 识别（Dictionary Prior）")
    
    test_cases = [
        {
            "name": "已知俱乐部: Arsenal",
            "text": "Arsenal defeated Chelsea 2-1.",
            "expected_clubs": ["Arsenal", "Chelsea"]
        },
        {
            "name": "别名: Gunners",
            "text": "The Gunners scored in the first half.",
            "expected_clubs": []  # 别名暂不支持
        },
        {
            "name": "多个俱乐部",
            "text": "Manchester United signed a player from Bayern Munich.",
            "expected_clubs": ["Manchester United", "Bayern Munich"]
        },
    ]
    
    extractor = EntityExtractor()
    
    for i, case in enumerate(test_cases, 1):
        print(f"案例 {i}: {case['name']}")
        print(f"  文本: {case['text']}")
        
        entities = extractor.extract_participants(case["text"])
        clubs = [e["name"] for e in entities if e["type"] == EntityType.CLUB]
        
        expected = case["expected_clubs"]
        if expected:
            passed = all(club in clubs for club in expected)
        else:
            passed = True  # 如果不期望提取，则通过
        
        print(f"  期望: {expected}")
        print(f"  提取: {clubs}")
        print(f"  结果: {'✅ 通过' if passed else '❌ 失败'}\n")


def test_conflict_resolution():
    """测试冲突解决（Syntax > Dictionary）"""
    print_section("测试 5: 冲突解决（优先级验证）")
    
    # Mikel Arteta: 词典中有 ["coach", "former_player"]
    # 但在 "Arteta's Arsenal side" 中，语法判定为 Coach
    
    text = "Mikel Arteta's Arsenal side won the match."
    
    print(f"📝 测试文本: {text}\n")
    print("📚 词典信息: Mikel Arteta = ['coach', 'former_player']")
    print("🔧 语法证据: 'Arteta's Arsenal side' → possession pattern\n")
    
    extractor = EntityExtractor()
    entities = extractor.extract_participants(text)
    
    arteta = next((e for e in entities if "Arteta" in e["name"]), None)
    
    if arteta:
        print(f"✅ 提取实体: {arteta['name']}")
        print(f"✅ 判定类型: {arteta['type']}")
        
        if arteta["type"] == EntityType.COACH:
            print("\n🎉 优先级正确：Syntax > Dictionary")
        else:
            print(f"\n❌ 优先级错误：期望 Coach，实际 {arteta['type']}")
    else:
        print("❌ 未提取到 Mikel Arteta")


def test_real_world_transfer_news():
    """测试真实世界案例（转会新闻）"""
    print_section("测试 6: 真实世界案例（转会新闻）")
    
    text = """
    West Ham United is delighted to announce the signing of Argentina international 
    forward Taty Castellanos. The 27-year-old joins the Hammers from Lazio on a 
    four-and-a-half-year contract until summer 2029. Born in Mendoza and capped twice 
    by his country, Castellanos won the MLS Cup and Golden Boot with New York City FC.
    """
    
    print(f"📝 测试文本:\n{text}\n")
    
    extractor = EntityExtractor()
    entities = extractor.extract_participants(text)
    
    print("📊 提取结果:\n")
    
    by_type = {}
    for entity in entities:
        entity_type = entity["type"]
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(entity["name"])
    
    for entity_type in sorted(by_type.keys(), key=str):
        print(f"  {entity_type}:")
        for name in by_type[entity_type]:
            print(f"    - {name}")
    
    print(f"\n总计: {len(entities)} 个实体")


def test_edge_cases():
    """测试边界情况"""
    print_section("测试 7: 边界情况")
    
    test_cases = [
        {
            "name": "空文本",
            "text": "",
            "expected_count": 0
        },
        {
            "name": "无实体文本",
            "text": "The game was very exciting and entertaining.",
            "expected_count": 0
        },
        {
            "name": "只有俱乐部",
            "text": "Arsenal played against Chelsea.",
            "min_count": 2
        },
    ]
    
    extractor = EntityExtractor()
    
    for case in test_cases:
        print(f"案例: {case['name']}")
        print(f"  文本: {case['text'] if case['text'] else '(空)'}")
        
        entities = extractor.extract_participants(case["text"])
        
        if "expected_count" in case:
            passed = len(entities) == case["expected_count"]
            print(f"  期望数量: {case['expected_count']}")
        else:
            passed = len(entities) >= case["min_count"]
            print(f"  最小数量: {case['min_count']}")
        
        print(f"  实际数量: {len(entities)}")
        print(f"  结果: {'✅ 通过' if passed else '❌ 失败'}\n")


def main():
    """运行所有测试"""
    print("\n" + "🏈"*40)
    print("  EntityExtractor v2 测试套件 (三层架构)")
    print("  Layer 1: spaCy NER → Layer 2: Dictionary → Layer 3: Syntax")
    print("🏈"*40)
    
    # 强制测试案例（必须通过）
    mandatory_passed = test_mandatory_example()
    
    # # 其他测试
    # test_coach_detection()
    # test_player_detection()
    # test_tournament_detection()
    # test_club_detection()
    # test_conflict_resolution()
    # test_real_world_transfer_news()
    # test_edge_cases()
    
    print("\n" + "="*80)
    if mandatory_passed:
        print("✅ 强制测试案例通过 - 系统符合基本要求")
    else:
        print("❌ 强制测试案例失败 - 需要修复核心功能")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
