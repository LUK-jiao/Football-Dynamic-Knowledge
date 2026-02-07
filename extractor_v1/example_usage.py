"""
Example: Using Football Anchor Extraction

演示如何使用事实锚点抽取系统。
"""

import json
from extractor_v1.anchor_extractor import AnchorExtractor


def example_1_basic_usage():
    """示例 1：基本使用"""
    print("=" * 100)
    print("示例 1: 基本使用")
    print("=" * 100)
    print()
    
    # 初始化抽取器
    extractor = AnchorExtractor(model="llama3.2:latest")
    
    # 准备输入 block
    block = {
        "block_id": "example_001",
        "text": "Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United on July 30, 2024.",
        "source": "BBC Sport",
        "publish_date": "2024-07-30"
    }
    
    print("📥 输入:")
    print(json.dumps(block, indent=2, ensure_ascii=False))
    print()
    
    # 提取锚点
    result = extractor.extract_anchors(block)
    
    print("📤 输出:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    # 分析结果
    print("📊 分析:")
    print(f"  - Fact Type: {result['fact_type']}")
    print(f"  - Need Resolver: {result['need_resolver']}")
    print(f"  - Participants: {len(result['anchors']['participants'])}")
    print(f"  - Temporal Anchors: {len(result['anchors']['temporal_anchors'])}")
    print()


def example_2_event_vs_state():
    """示例 2：EVENT vs STATE 对比"""
    print("=" * 100)
    print("示例 2: EVENT vs STATE 对比")
    print("=" * 100)
    print()
    
    extractor = AnchorExtractor(model="llama3.2:latest")
    
    # EVENT 示例
    event_block = {
        "block_id": "event_example",
        "text": "Arsenal won 3-2 against Chelsea at Emirates Stadium yesterday.",
        "source": "Sky Sports",
        "publish_date": "2025-01-20"
    }
    
    print("📌 EVENT 示例:")
    print(f"Text: {event_block['text']}")
    
    event_result = extractor.extract_anchors(event_block)
    print(f"→ Fact Type: {event_result['fact_type']}")
    print(f"→ Need Resolver: {event_result['need_resolver']}")
    print(f"→ 解释: 比赛结果是历史事件，一旦发生永远成立")
    print()
    
    # STATE 示例
    state_block = {
        "block_id": "state_example",
        "text": "Ruben Amorim is the head coach of Manchester United.",
        "source": "Official",
        "publish_date": "2025-01-20"
    }
    
    print("📌 STATE 示例:")
    print(f"Text: {state_block['text']}")
    
    state_result = extractor.extract_anchors(state_block)
    print(f"→ Fact Type: {state_result['fact_type']}")
    print(f"→ Need Resolver: {state_result['need_resolver']}")
    print(f"→ 解释: 教练身份是状态事实，随时间变化，需要 resolver 推理有效期")
    print()


def example_3_batch_processing():
    """示例 3：批量处理"""
    print("=" * 100)
    print("示例 3: 批量处理")
    print("=" * 100)
    print()
    
    extractor = AnchorExtractor(model="llama3.2:latest")
    
    # 准备多个 blocks
    blocks = [
        {
            "block_id": "batch_001",
            "text": "De Ligt signed a five-year contract with Manchester United until 2029.",
            "source": "ESPN",
            "publish_date": "2024-07-30"
        },
        {
            "block_id": "batch_002",
            "text": "Salah is currently injured and will miss the next match.",
            "source": "Liverpool FC",
            "publish_date": "2025-01-20"
        },
        {
            "block_id": "batch_003",
            "text": "Taty Castellanos scored four goals against Real Madrid in the Copa del Rey.",
            "source": "Marca",
            "publish_date": "2023-05-20"
        }
    ]
    
    print(f"📥 待处理: {len(blocks)} 个 blocks")
    print()
    
    # 批量抽取
    results = extractor.extract_anchors_batch(blocks)
    
    print("📤 结果统计:")
    print()
    
    for i, result in enumerate(results, 1):
        if "error" in result:
            print(f"Block {i}: ❌ 错误 - {result['error']}")
        else:
            print(f"Block {i}: {result['block_id']}")
            print(f"  - Fact Type: {result['fact_type']}")
            print(f"  - Need Resolver: {result['need_resolver']}")
            print(f"  - Participants: {len(result['anchors']['participants'])}")
            print()


def example_4_need_resolver_logic():
    """示例 4：Need Resolver 判定逻辑"""
    print("=" * 100)
    print("示例 4: Need Resolver 判定逻辑")
    print("=" * 100)
    print()
    
    extractor = AnchorExtractor(model="llama3.2:latest")
    
    # Case 1: EVENT → need_resolver = false
    print("📌 Case 1: EVENT")
    block1 = {
        "block_id": "case1",
        "text": "Arsenal won 3-2 against Chelsea.",
        "source": "BBC",
        "publish_date": "2025-01-20"
    }
    result1 = extractor.extract_anchors(block1)
    print(f"Text: {block1['text']}")
    print(f"→ Fact Type: {result1['fact_type']}")
    print(f"→ Need Resolver: {result1['need_resolver']}")
    print(f"→ 原因: 历史事件不需要有效期")
    print()
    
    # Case 2: STATE + 有 valid_to → need_resolver = false
    print("📌 Case 2: STATE（有 valid_to）")
    block2 = {
        "block_id": "case2",
        "text": "He signed a contract until 2028.",
        "source": "ESPN",
        "publish_date": "2024-07-30"
    }
    result2 = extractor.extract_anchors(block2)
    print(f"Text: {block2['text']}")
    print(f"→ Fact Type: {result2['fact_type']}")
    print(f"→ Need Resolver: {result2['need_resolver']}")
    print(f"→ 原因: 已有结束时间，不需要推理")
    print()
    
    # Case 3: STATE + 无 valid_to → need_resolver = true
    print("📌 Case 3: STATE（无 valid_to）")
    block3 = {
        "block_id": "case3",
        "text": "Amorim is the head coach of Manchester United.",
        "source": "Official",
        "publish_date": "2025-01-20"
    }
    result3 = extractor.extract_anchors(block3)
    print(f"Text: {block3['text']}")
    print(f"→ Fact Type: {result3['fact_type']}")
    print(f"→ Need Resolver: {result3['need_resolver']}")
    print(f"→ 原因: 缺失结束时间，需要 resolver 推理")
    print()


def main():
    """主函数"""
    print()
    print("🚀 Football Anchor Extraction Examples")
    print()
    
    try:
        # 示例 1
        example_1_basic_usage()
        
        # 示例 2
        example_2_event_vs_state()
        
        # 示例 3
        example_3_batch_processing()
        
        # 示例 4
        example_4_need_resolver_logic()
        
        print("=" * 100)
        print("✅ 所有示例运行完成")
        print("=" * 100)
        
    except Exception as e:
        print(f"❌ 运行失败: {str(e)}")
        print()
        print("请确保：")
        print("1. Ollama 服务已启动: ollama serve")
        print("2. 模型已下载: ollama pull llama3.2:latest")


if __name__ == "__main__":
    main()
