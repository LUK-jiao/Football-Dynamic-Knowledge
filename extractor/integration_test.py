#!/usr/bin/env python3
"""
Extractor 集成测试：完整流水线验证

测试流程：
1. 原始文本 (Raw Text)
2. 句子分割 (Sentence Splitter)
3. 语义分块 (Semantic Blocker)
4. 锚点抽取 (Anchor Extractor) ← 本模块
5. 结构化输出 (JSON)

测试重点：
- 验证 semantic_blocker → extractor 的数据对接
- 验证四类锚点的正确抽取
- 验证输出格式的严格性
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import List, Dict, Any
from datetime import datetime

from preprocess.sentence_splitter.splitter import SentenceSplitter
from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, GranularityMode, OllamaBackend
from extractor.ner import FootballAnchorExtractor


def print_section(title: str, level: int = 1):
    """打印分段标题"""
    if level == 1:
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    elif level == 2:
        print("\n" + "-" * 80)
        print(f"  {title}")
        print("-" * 80)
    else:
        print(f"\n[{title}]")


def print_json(data: Dict[str, Any], indent: int = 2):
    """美化打印 JSON"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def validate_output_format(output: Dict[str, Any]) -> bool:
    """
    验证输出格式是否符合规范
    
    必须包含：
    - block_id, text, source, publish_date (原始字段)
    - anchors (新增字段)
        - participants (数组)
        - temporal_anchors (数组)
        - sources (数组)
        - constraints (数组)
    """
    required_fields = ["block_id", "text", "source", "publish_date", "anchors"]
    for field in required_fields:
        if field not in output:
            print(f"❌ 缺少字段: {field}")
            return False
    
    anchors = output["anchors"]
    required_anchor_types = ["participants", "temporal_anchors", "sources", "constraints"]
    for anchor_type in required_anchor_types:
        if anchor_type not in anchors:
            print(f"❌ anchors 缺少字段: {anchor_type}")
            return False
        if not isinstance(anchors[anchor_type], list):
            print(f"❌ anchors.{anchor_type} 必须是数组")
            return False
    
    return True


def test_pipeline(raw_text: str, source: str, publish_date: str, test_name: str):
    """
    完整流水线测试
    
    Args:
        raw_text: 原始文本
        source: 来源名称
        publish_date: 发布日期 (YYYY-MM-DD)
        test_name: 测试名称
    """
    print_section(f"测试案例: {test_name}", level=1)
    
    print("\n📄 原始输入:")
    print(f"  来源: {source}")
    print(f"  日期: {publish_date}")
    print(f"  文本长度: {len(raw_text)} 字符")
    print(f"  文本预览:\n{raw_text[:200]}...\n")
    
    # ========================================================================
    # 步骤 1: 句子分割
    # ========================================================================
    print_section("步骤 1: 句子分割", level=3)
    
    splitter = SentenceSplitter()
    sentences = splitter.split(raw_text)
    
    print(f"✅ 分割结果: {len(sentences)} 个句子")
    for i, sent in enumerate(sentences[:3], 1):
        print(f"  句子 {i}: {sent[:60]}...")
    if len(sentences) > 3:
        print(f"  ... (省略 {len(sentences) - 3} 个句子)")
    
    # ========================================================================
    # 步骤 2: 语义分块
    # ========================================================================
    print_section("步骤 2: 语义分块", level=3)
    
    llm_backend = OllamaBackend()
    chunker = SemanticChunker(
        llm=llm_backend,
        config = ChunkerConfig(
        granularity=GranularityMode.FINE,
        context_window=2,
        max_sentences_per_chunk=10,
        enable_structural_rules=True,
        enable_orphan_merge=True,
        log_scores=True
    )
    )
    
    chunks = chunker.chunk(sentences)
    
    print(f"✅ 分块结果: {len(chunks)} 个语义块")
    for i, chunk in enumerate(chunks, 1):
        print(f"  块 {i}:")
        print(f"    类型: {chunk.chunk_type}")
        print(f"    句子数: {len(chunk.sentences)}")
        print(f"    预览: {' '.join(chunk.sentences)[:80]}...")
    
    # ========================================================================
    # 步骤 3: 转换为 Extractor 输入格式
    # ========================================================================
    print_section("步骤 3: 格式转换 (Blocker → Extractor)", level=3)
    
    extractor_inputs = []
    for chunk in chunks:
        extractor_input = chunk.to_extractor_input(
            source=source,
            publish_date=publish_date
        )
        extractor_inputs.append(extractor_input)
    
    print(f"✅ 转换完成: {len(extractor_inputs)} 个输入块")
    print("\n示例输入块:")
    print_json(extractor_inputs[0] if extractor_inputs else {})
    
    # ========================================================================
    # 步骤 4: 锚点抽取
    # ========================================================================
    print_section("步骤 4: 锚点抽取", level=3)
    
    extractor = FootballAnchorExtractor()
    outputs = []
    
    for extractor_input in extractor_inputs:
        output = extractor.extract_anchors(extractor_input)
        outputs.append(output)
    
    print(f"✅ 抽取完成: {len(outputs)} 个输出块")
    
    # ========================================================================
    # 步骤 5: 验证输出格式
    # ========================================================================
    print_section("步骤 5: 验证输出格式", level=3)
    
    all_valid = True
    for i, output in enumerate(outputs, 1):
        print(f"\n验证块 {i} ({output.get('block_id', 'unknown')}):")
        if validate_output_format(output):
            print("  ✅ 格式正确")
        else:
            print("  ❌ 格式错误")
            all_valid = False
    
    if all_valid:
        print("\n🎉 所有输出块格式验证通过！")
    else:
        print("\n⚠️  部分输出块格式不符合规范")
    
    # ========================================================================
    # 步骤 6: 展示详细结果
    # ========================================================================
    print_section("步骤 6: 详细结果展示", level=3)
    
    for i, output in enumerate(outputs, 1):
        print(f"\n{'='*60}")
        print(f"块 {i}: {output['block_id']}")
        print(f"{'='*60}")
        
        print(f"\n📝 原始文本:")
        print(f"  {output['text'][:150]}...")
        
        anchors = output['anchors']
        
        # 参与者
        print(f"\n👥 参与者锚点 ({len(anchors['participants'])} 个):")
        if anchors['participants']:
            for p in anchors['participants']:
                print(f"  - {p['type']}: {p['name']}")
        else:
            print("  (无)")
        
        # 时间
        print(f"\n⏰ 时间锚点 ({len(anchors['temporal_anchors'])} 个):")
        if anchors['temporal_anchors']:
            for t in anchors['temporal_anchors']:
                print(f"  - 事件日期: {t.get('event_date', 'N/A')}")
                print(f"    有效期: {t.get('valid_from', 'N/A')} → {t.get('valid_to', 'N/A')}")
        else:
            print("  (无)")
        
        # 来源
        print(f"\n📰 来源锚点 ({len(anchors['sources'])} 个):")
        if anchors['sources']:
            for s in anchors['sources']:
                print(f"  - {s['name']} ({s['type']})")
        else:
            print("  (无)")
        
        # 约束
        print(f"\n🔗 约束锚点 ({len(anchors['constraints'])} 个):")
        if anchors['constraints']:
            for c in anchors['constraints']:
                print(f"  - {c['type']}")
                print(f"    主体: {c['subject']}")
                print(f"    状态: {c['expected_state']}")
        else:
            print("  (无)")
    
    # ========================================================================
    # 步骤 7: 统计汇总
    # ========================================================================
    print_section("步骤 7: 统计汇总", level=3)
    
    total_participants = sum(len(o['anchors']['participants']) for o in outputs)
    total_temporal = sum(len(o['anchors']['temporal_anchors']) for o in outputs)
    total_sources = sum(len(o['anchors']['sources']) for o in outputs)
    total_constraints = sum(len(o['anchors']['constraints']) for o in outputs)
    
    print(f"\n📊 整体统计:")
    print(f"  原始文本: {len(raw_text)} 字符")
    print(f"  分句结果: {len(sentences)} 个句子")
    print(f"  语义块: {len(chunks)} 个")
    print(f"  输出块: {len(outputs)} 个")
    print(f"\n  锚点统计:")
    print(f"    参与者: {total_participants} 个")
    print(f"    时间: {total_temporal} 个")
    print(f"    来源: {total_sources} 个")
    print(f"    约束: {total_constraints} 个")
    
    # ========================================================================
    # 步骤 8: 导出 JSON
    # ========================================================================
    # 确保输出目录存在
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 添加时间戳避免覆盖旧文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{test_name.replace(' ', '_').lower()}_{timestamp}.json"
    output_path = os.path.join(output_dir, output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 已导出到: {output_path}")
    
    return outputs


def main():
    """运行所有测试"""
    print("\n" + "🏈" * 40)
    print("  Extractor 集成测试套件")
    print("  完整流水线: 原始文本 → 句子分割 → 语义分块 → 锚点抽取")
    print("🏈" * 40)
    
    # ========================================================================
    # 测试 1: 足球比赛报道（来自 preprocess.integration_test）
    # ========================================================================
    test_1_text = """
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, 
    with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions.
    Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time.
    The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.
    After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix.
    The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.
    A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.
    This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.
    Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals."
    The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent.
    "I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
    """
    
    # test_pipeline(
    #     raw_text=test_1_text,
    #     source="Sky Sports",
    #     publish_date="2025-01-15",
    #     test_name="Arsenal EFL Cup Match"
    # )
    
    # ========================================================================
    # 测试 2: 转会新闻
    # ========================================================================
    test_2_text = """
    West Ham United is delighted to announce the signing of Argentina international forward Taty Castellanos.

The 27-year-old joins the Hammers from Italian club Lazio on a four-and-a-half year contract with the option for a further year.

An aggressive, deep-lying forward capable of scoring and creating goals, linking play and working hard for his team, Castellanos has enjoyed a superb career in the MLS, La Liga and Serie A and will now bring his all-round qualities to the Premier League.

Born in Mendoza and capped twice by his country, Castellanos won the MLS Cup and Golden Boot with New York City FC in 2021 before netting four goals in a single game for Girona against Real Madrid in La Liga in 2023. He then scored 14 times last season as Lazio finished seventh in Serie A and reached the UEFA Europa League quarter-finals.

Identified as a key target by Head Coach Nuno Espírito Santo, the Hammers’ new No11 - who has signed in time to be available for Tuesday evening’s Premier League match against Nottingham Forest at London Stadium - is now looking forward to pulling on a West Ham shirt and showing the Claret and Blue Army what he can do.

“I'm really happy because it's a very important challenge for me personally and I've come to contribute, to try to help the team as much as I can,” said Castellanos.

“Every match is a battle, and I'm here to contribute that, to try to bring that energy, that fighting spirit I have inside, so that every match is as important and as tough as possible.

“I hope to give my all to the fans. I've always defended the jersey of every team with the utmost responsibility, and I want to tell them that I'm going to give everything, to defend this jersey, and obviously, to achieve our goals day after day. That's the most important thing.”

Everyone at West Ham United would like to welcome Taty and his family to East London, and wishes him every success for his career in Claret and Blue.
    """
    
    test_pipeline(
        raw_text=test_2_text,
        source="West Ham United Official",
        publish_date="2026-01-05",
        test_name="Taty Castellanos Transfer"
    )
    
    # ========================================================================
    # 测试 3: 伤病报告
    # ========================================================================
    test_3_text = """
    Liverpool's Mohamed Salah will miss the next two Premier League matches due to a hamstring injury.
    The Egyptian forward suffered the injury during training yesterday and underwent a scan this morning.
    Manager Jurgen Klopp confirmed the news at his press conference, stating that Salah is expected to return after the international break.
    The club's medical team is working closely with the player to ensure a full recovery.
    This setback comes at a crucial time as Liverpool prepare to face Manchester City on Saturday.
    """
    
    # test_pipeline(
    #     raw_text=test_3_text,
    #     source="Liverpool FC Official",
    #     publish_date="2025-11-20",
    #     test_name="Salah Injury Report"
    # )
    
    print_section("✅ 所有测试完成", level=1)
    # print("\n💡 关键验证点:")
    # print("  1. ✅ semantic_blocker → extractor 数据格式对接")
    # print("  2. ✅ 四类锚点正确抽取")
    # print("  3. ✅ 输出格式严格符合规范")
    # print("  4. ✅ block_id 保持不变")
    # print("  5. ✅ 原始字段完整保留")
    # print("  6. ✅ JSON 可解析性")
    # print("\n🎯 流水线已就绪，可供下游模块使用（Knowledge Graph / Verifier / RAG）\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
