"""
Test Event Decomposition Module

测试事件分解层是否正确工作。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_v1.event_decomposition import EventDecomposer
import json
import logging

# Suppress INFO logs
logging.getLogger().setLevel(logging.WARNING)


def print_events(result: dict, test_name: str):
    """打印事件分解结果"""
    print(f"\n{'='*80}")
    print(f"Test: {test_name}")
    print(f"{'='*80}")
    
    if "events" not in result or not result["events"]:
        print("⚠️  No events generated")
        return
    
    events = result["events"]
    print(f"\n✓ Generated {len(events)} event(s):\n")
    
    for i, event in enumerate(events, 1):
        print(f"[Event {i}]")
        print(f"  Event ID: {event['event_id']}")
        print(f"  Title Anchors: {event.get('title_anchors', 'N/A')}")
        print(f"  Description: {event['event_description']}")
        print(f"  Block Text: {event['block_text'][:100]}..." if len(event['block_text']) > 100 else f"  Block Text: {event['block_text']}")
        print(f"  Inference Time: {event.get('inference_time', 0):.2f}s")
        print()


def test_single_event():
    """测试单事件场景"""
    block = {
        "block_id": "001",
        "title": "De Ligt Agrees Manchester United Transfer",
        "text": "De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
        "source": "BBC",
        "publish_date": "2025-08-23"
    }
    
    decomposer = EventDecomposer(model="llama3:latest")
    result = decomposer.decompose(block)
    
    print_events(result, "Single Event - Transfer Agreement")
    
    # Validation
    assert len(result["events"]) >= 1, "Should have at least 1 event"
    assert result["events"][0]["title_anchors"], "Should have title_anchors"
    
    return result


def test_multiple_events():
    """测试多事件场景"""
    block = {
        "block_id": "002",
        "title": "Arsenal Defeats Chelsea 2-1 with Saka Winner",
        "text": "Arsenal won 2-1 against Chelsea. Saka scored the winning goal in the 85th minute.",
        "source": "Sky Sports",
        "publish_date": "2025-01-15"
    }
    
    decomposer = EventDecomposer(model="llama3:latest")
    result = decomposer.decompose(block)
    
    print_events(result, "Multiple Events - Match with Decisive Goal")
    
    # Validation
    events = result["events"]
    assert len(events) >= 1, "Should have at least 1 event"
    
    print(f"Validation:")
    print(f"  Total events: {len(events)}")
    for event in events:
        assert event["title_anchors"], "Each event should have title_anchors"
    
    return result


def test_complex_block():
    """测试复杂语义块（来自真实数据）"""
    block = {
        "block_id": "003",
        "title": "Arsenal Wins EFL Cup Quarter-Final Against Palace on Penalties",
        "text": "After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix. The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time. A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.",
        "source": "BBC Sport",
        "publish_date": "2025-01-15"
    }
    
    decomposer = EventDecomposer(model="llama3:latest")
    result = decomposer.decompose(block)
    print(f"\nOriginal text: \n {block['text']}")
    print_events(result, "Complex Block - Match Narrative with Multiple Goals")
    
    return result


def test_independent_events():
    """测试独立事件"""
    block = {
        "block_id": "004",
        "title": "Major Transfer News: Salah and Haaland Signings",
        "text": "Liverpool signed Salah. Manchester City acquired Haaland.",
        "source": "ESPN",
        "publish_date": "2025-01-10"
    }
    
    decomposer = EventDecomposer(model="llama3:latest")
    result = decomposer.decompose(block)
    
    print_events(result, "Independent Events - Two Separate Transfers")
    
    # Validation
    events = result["events"]
    assert len(events) >= 1, "Should have at least 1 event"
    for event in events:
        assert event["title_anchors"], "Each event should have title_anchors"
    
    return result


def main():
    """运行所有测试"""
    print("="*80)
    print("EVENT DECOMPOSITION MODULE - TEST SUITE")
    print("="*80)
    
    tests = [
        ("Single Event", test_single_event),
        ("Multiple Events", test_multiple_events),
        ("Complex Block", test_complex_block),
        ("Independent Events", test_independent_events)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            print(f"\n🧪 Running: {name}...")
            result = test_func()
            print(f"✅ {name} - PASSED")
            results.append((name, True, result))
        except AssertionError as e:
            print(f"❌ {name} - FAILED: {e}")
            results.append((name, False, None))
        except Exception as e:
            print(f"💥 {name} - ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, None))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, _ in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
