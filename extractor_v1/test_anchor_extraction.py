"""
Test Suite for Football Anchor Extraction

测试 ollama_backend.py 和 anchor_extractor.py 的完整功能。
"""

import json
import sys
import time
from typing import Dict, Any

# 导入模块
try:
    from extractor_v1.ollama_backend import OllamaBackend, validate_schema, print_prompt
    from extractor_v1.anchor_extractor import AnchorExtractor
except ImportError:
    # 如果直接运行，尝试添加父目录到路径
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extractor_v1.ollama_backend import OllamaBackend, validate_schema, print_prompt
    from extractor_v1.anchor_extractor import AnchorExtractor


# ============================================================================
# 测试数据（Event 格式 - 从 Event Decomposition Layer 输出）
# ============================================================================

TEST_EVENTS = [
    # 测试 1: 转会新闻（EVENT - 明确时间点）
    {
        "event_id": "001-1",
        "title_anchors": "De Ligt Transfer to Manchester United",
        "event_description": "Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United on July 30, 2024.",
        "block_text": "Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United on July 30, 2024. The 25-year-old defender signs a five-year deal until June 2029.",
        "source": "BBC Sport",
        "publish_date": "2024-07-30"
    },
    
    # 测试 2: 比赛结果（EVENT - 历史事实）
    {
        "event_id": "002-1",
        "title_anchors": "Arsenal vs Chelsea Match Result",
        "event_description": "Arsenal won 3-2 against Chelsea at Emirates Stadium, with Saka scoring two goals.",
        "block_text": "Arsenal won 3-2 against Chelsea at Emirates Stadium. Saka scored two goals in the match.",
        "source": "Sky Sports",
        "publish_date": "2025-01-20"
    },
    
    # 测试 3: 教练身份（STATE - 无结束时间）
    {
        "event_id": "003-1",
        "title_anchors": "Ruben Amorim Manchester United Manager",
        "event_description": "Ruben Amorim is the head coach of Manchester United, joining from Sporting CP.",
        "block_text": "Ruben Amorim is the head coach of Manchester United. He joined the club from Sporting CP.",
        "source": "Official",
        "publish_date": "2024-11-01"
    },
    
    # 测试 4: 合同状态（STATE - 有结束时间）
    {
        "event_id": "004-1",
        "title_anchors": "De Ligt Contract Extension",
        "event_description": "De Ligt signed a contract with Manchester United until 2029.",
        "block_text": "De Ligt signed a contract with Manchester United until 2029.",
        "source": "ESPN",
        "publish_date": "2024-07-30"
    },
    
    # 测试 5: 伤病状态（STATE - 无结束时间）
    {
        "event_id": "005-1",
        "title_anchors": "Salah Injury Update",
        "event_description": "Mohamed Salah is currently injured and unavailable for selection.",
        "block_text": "Mohamed Salah is currently injured and unavailable for selection.",
        "source": "Liverpool FC Official",
        "publish_date": "2025-01-15"
    },
    
    # 测试 6: 历史进球（EVENT）
    {
        "event_id": "006-1",
        "title_anchors": "Castellanos Four Goals vs Real Madrid",
        "event_description": "Taty Castellanos scored four goals against Real Madrid in the 2023 Copa del Rey.",
        "block_text": "Taty Castellanos scored four goals against Real Madrid in the 2023 Copa del Rey.",
        "source": "Marca",
        "publish_date": "2023-05-20"
    },
]


# ============================================================================
# 测试函数
# ============================================================================

def test_prompt_display(event: Dict[str, Any]):
    """测试 Prompt 显示"""
    print("=" * 100)
    print("测试 2: Prompt 显示")
    print("=" * 100)
    print()
    
    print(f"Event ID: {event['event_id']}")
    print(f"Title: {event['title_anchors']}")
    print(f"描述: {event['event_description'][:100]}...")
    print()
    
    print_prompt(event)


def test_backend_extraction(event: Dict[str, Any], model: str = "llama3:latest"):
    """测试 Backend 抽取"""
    print("=" * 100)
    print(f"测试 3: Backend 提取 - {event['event_id']}")
    print("=" * 100)
    print()
    
    print(f"Event ID: {event['event_id']}")
    print(f"Title: {event['title_anchors']}")
    print(f"描述长度: {len(event['event_description'])} 字符")
    print()
    print("事件描述:")
    print(event['event_description'])
    print()
    print("-" * 100)
    print("调用 Ollama Backend...")
    print("-" * 100)
    print()
    
    try:
        # 记录开始时间
        start_time = time.time()
        
        backend = OllamaBackend(model=model)
        result = backend.extract_anchors(event)
        
        # 计算推理时间
        inference_time = time.time() - start_time
        
        print("✅ 提取成功")
        print()
        print("-" * 100)
        print("提取结果:")
        print("-" * 100)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 验证 Schema
        print("-" * 100)
        validate_schema(result)
        print("-" * 100)
        print()
        
        # 分析结果
        print("📊 结果分析:")
        print(f"  - Event ID: {result.get('event_id')}")
        print(f"  - Title Anchors: {result.get('title_anchors')}")
        print(f"  - Fact Type: {result.get('fact_type')}")
        print(f"  - Participants: {len(result.get('participants', []))}")
        print(f"  - Temporal Anchors: {len(result.get('temporal_anchors', []))}")
        print(f"  - Constraints: {len(result.get('constraints', []))}")
        print(f"  - Sources: {len(result.get('sources', []))}")
        print(f"  - LLM 推理时间: {inference_time:.3f} 秒")
        print()
        
        return result
        
    except Exception as e:
        print(f"❌ 提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_anchor_extractor(event: Dict[str, Any], model: str = "llama3:latest"):
    """测试 AnchorExtractor"""
    print("=" * 100)
    print(f"测试 4: AnchorExtractor - {event['event_id']}")
    print("=" * 100)
    print()
    
    try:
        extractor = AnchorExtractor(model=model)
        result = extractor.extract_anchors(event)
        
        print("✅ 抽取成功")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        return result
        
    except Exception as e:
        print(f"❌ 抽取失败: {str(e)}")
        return None


def test_batch_processing(events: list, model: str = "llama3:latest"):
    """测试批量处理"""
    print("=" * 100)
    print("测试 5: 批量处理")
    print("=" * 100)
    print()
    
    print(f"待处理 events: {len(events)}")
    print()
    
    try:
        extractor = AnchorExtractor(model=model)
        results = extractor.extract_anchors_batch(events)
        
        print(f"✅ 批量处理完成，处理 {len(results)} 个 events")
        print()
        
        # 统计结果
        event_count = 0
        state_count = 0
        error_count = 0
        total_inference_time = 0
        
        for result in results:
            if "error" in result:
                error_count += 1
            else:
                if result.get("fact_type") == "EVENT":
                    event_count += 1
                elif result.get("fact_type") == "STATE":
                    state_count += 1
                
                # 累加推理时间
                total_inference_time += result.get("inference_time", 0)
        
        print("📊 批量处理统计:")
        print(f"  - 总数: {len(results)}")
        print(f"  - EVENT: {event_count}")
        print(f"  - STATE: {state_count}")
        print(f"  - 错误: {error_count}")
        print(f"  - 总推理时间: {total_inference_time:.2f} 秒")
        print(f"  - 平均推理时间: {total_inference_time / len(results):.2f} 秒")
        print()
        
        return results
        
    except Exception as e:
        print(f"❌ 批量处理失败: {str(e)}")
        return None


def test_edge_cases():
    """测试边界情况"""
    print("=" * 100)
    print("测试 6: 边界情况")
    print("=" * 100)
    print()
    
    extractor = AnchorExtractor()
    
    # 测试空描述
    print("📋 测试 6.1: 空描述")
    empty_event = {
        "event_id": "empty",
        "event_description": "",
        "source": "Test",
        "publish_date": "2025-01-01"
    }
    
    try:
        result = extractor.extract_anchors(empty_event)
        print("❌ 应该抛出 ValueError")
    except ValueError as e:
        print(f"✅ 正确抛出异常: {str(e)}")
    
    print()
    
    # 测试缺少字段
    print("📋 测试 6.2: 缺少必需字段")
    incomplete_event = {
        "event_id": "incomplete",
        "title_anchors": "Some title"
    }
    
    try:
        result = extractor.extract_anchors(incomplete_event)
        print("❌ 应该抛出 ValueError")
    except ValueError as e:
        print(f"✅ 正确抛出异常: {str(e)}")


def run_all_tests(model: str = "llama3:latest", skip_llm: bool = False):
    """运行所有测试"""
    print()
    print("🚀 开始运行测试套件")
    print()
    
    # 测试 3-4: Backend 和 Extractor（每个测试场景）
    if not skip_llm:
        for event in TEST_EVENTS:
            test_backend_extraction(event, model)
            print()
        
        # 测试 5: 批量处理
        test_batch_processing(TEST_EVENTS, model)
        print()
    
    # 测试 6: 边界情况
    test_edge_cases()
    print()
    
    print("=" * 100)
    print("✅ 测试套件运行完成")
    print("=" * 100)


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Football Anchor Extraction")
    parser.add_argument("--model", type=str, default="llama3:latest", help="Ollama 模型名称")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM 相关测试")
    parser.add_argument("--test", type=str, choices=["prompt", "backend", "extractor", "batch", "edge", "all"], 
                        default="all", help="运行特定测试")
    
    args = parser.parse_args()
    
    # 运行特定测试
    if args.test == "prompt":
        test_prompt_display(TEST_EVENTS[0])
    elif args.test == "backend":
        test_backend_extraction(TEST_EVENTS[0], args.model)
    elif args.test == "extractor":
        test_anchor_extractor(TEST_EVENTS[0], args.model)
    elif args.test == "batch":
        test_batch_processing(TEST_EVENTS, args.model)
    elif args.test == "edge":
        test_edge_cases()
    else:
        run_all_tests(args.model, args.skip_llm)
