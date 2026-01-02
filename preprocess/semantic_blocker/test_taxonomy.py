#!/usr/bin/env python3
"""
Quick test script for event taxonomy.
Demonstrates event detection and classification.
"""

from preprocess.semantic_blocker.event_taxonomy import (
    EventType,
    EVENT_TRIGGERS,
    get_event_triggers,
    is_compatible_event,
    DependencyMarkers
)
import re


def detect_event_type(sentence: str) -> tuple[EventType, float]:
    """
    Detect the most likely event type for a sentence.
    
    Returns:
        (event_type, confidence)
    """
    sent_lower = sentence.lower()
    best_match = None
    best_score = 0
    
    for event_type in EventType:
        triggers = get_event_triggers(event_type)
        score = 0
        
        # Check verbs
        for verb in triggers.verbs:
            if f' {verb} ' in f' {sent_lower} ' or sent_lower.startswith(f'{verb} '):
                score += 3
        
        # Check keywords
        for keyword in triggers.keywords:
            if keyword in sent_lower:
                score += 2
        
        # Check patterns
        for pattern in triggers.patterns:
            if re.search(pattern, sent_lower):
                score += 2
        
        if score > best_score:
            best_score = score
            best_match = event_type
    
    # Calculate confidence
    confidence = min(0.95, best_score / 10.0) if best_score > 0 else 0.0
    
    return (best_match or EventType.GENERAL_NARRATIVE, confidence)


def is_dependent_sentence(sentence: str) -> bool:
    """Check if sentence is dependent on previous context."""
    markers = DependencyMarkers()
    sent_lower = sentence.lower().strip()
    
    # Check pronouns
    for pronoun in markers.ANAPHORIC_PRONOUNS:
        if sent_lower.startswith(pronoun + ' '):
            return True
    
    # Check temporal continuations
    for marker in markers.TEMPORAL_CONTINUATIONS:
        if sent_lower.startswith(marker + ' '):
            return True
    
    return False


def main():
    """Run taxonomy tests."""
    
    print("=" * 80)
    print("EVENT TAXONOMY - Quick Test")
    print("=" * 80)
    
    # Test cases
    test_sentences = [
        "Arsenal won 3-2 on penalties.",
        "Haaland scored in the 45th minute.",
        "Saka delivered the cross from the right wing.",
        "The Gunners will face Chelsea next week.",
        "Arteta told reporters after the match: 'We played well.'",
        "Kane picked up a hamstring injury.",
        "This was his 100th appearance for the club.",
        "The striker was ruled out for three weeks.",
        "It was a great moment for the team.",
        "Two late goals made it 1-1.",
    ]
    
    print("\n📊 Event Detection Test")
    print("-" * 80)
    
    for sent in test_sentences:
        event_type, confidence = detect_event_type(sent)
        is_dep = is_dependent_sentence(sent)
        
        print(f"\n📝 Sentence: {sent}")
        print(f"   Event: {event_type.value}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Dependent: {'Yes' if is_dep else 'No'}")
    
    # Test event compatibility
    print("\n" + "=" * 80)
    print("🔗 Event Compatibility Test")
    print("-" * 80)
    
    test_pairs = [
        (EventType.GOAL, EventType.ASSIST),
        (EventType.GOAL, EventType.MILESTONE),
        (EventType.MATCH_RESULT, EventType.GOAL),
        (EventType.MATCH_RESULT, EventType.FIXTURE),
        (EventType.MANAGER_QUOTE, EventType.MANAGER_QUOTE),
        (EventType.INJURY, EventType.SUBSTITUTION),
    ]
    
    for event1, event2 in test_pairs:
        compatible = is_compatible_event(event1, event2)
        symbol = "✅" if compatible else "❌"
        print(f"{symbol} {event1.value} ↔ {event2.value}")
    
    # Show trigger examples
    print("\n" + "=" * 80)
    print("🎯 Trigger Examples (Sample)")
    print("-" * 80)
    
    sample_events = [
        EventType.GOAL,
        EventType.MANAGER_QUOTE,
        EventType.FIXTURE,
        EventType.INJURY
    ]
    
    for event_type in sample_events:
        triggers = get_event_triggers(event_type)
        print(f"\n📌 {event_type.value.upper()}")
        print(f"   Verbs: {list(triggers.verbs)[:5]}...")
        print(f"   Keywords: {list(triggers.keywords)[:3]}...")
        print(f"   Patterns: {triggers.patterns[:2]}...")
    
    print("\n" + "=" * 80)
    print("✅ Taxonomy test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
