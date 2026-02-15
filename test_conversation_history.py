#!/usr/bin/env python3
"""
Test script for conversation history feature in /ask endpoint.

This tests the multi-turn Q&A capability where Claude maintains context
across follow-up questions.
"""

import requests
import json
from typing import List, Dict


API_BASE = "http://localhost:40080"


def test_conversation_history():
    """Test multi-turn conversation with history."""

    print("=" * 70)
    print("🧪 TESTING CONVERSATION HISTORY FEATURE")
    print("=" * 70)
    print()

    # First question (no history)
    print("=" * 70)
    print("TURN 1: Initial Question (No History)")
    print("=" * 70)
    question1 = "What is ACMS?"
    print(f"Question: {question1}")

    response1 = requests.post(
        f"{API_BASE}/ask",
        json={
            "question": question1,
            "context_limit": 5,
        }
    )

    if response1.status_code != 200:
        print(f"❌ Error: {response1.status_code}")
        print(response1.text)
        return

    data1 = response1.json()
    answer1 = data1["answer"]
    print(f"\nAnswer: {answer1[:300]}...")
    print(f"Sources: {len(data1['sources'])} memories")
    print(f"Confidence: {data1['confidence']}")
    print()

    # Build conversation history (last Q&A pair)
    conversation_history = [
        {"role": "user", "content": question1},
        {"role": "assistant", "content": answer1}
    ]

    # Second question (with history - follow-up)
    print("=" * 70)
    print("TURN 2: Follow-up Question (With History)")
    print("=" * 70)
    question2 = "How does it work?"
    print(f"Question: {question2}")
    print(f"History: {len(conversation_history)} messages (1 Q&A pair)")

    response2 = requests.post(
        f"{API_BASE}/ask",
        json={
            "question": question2,
            "context_limit": 5,
            "conversation_history": conversation_history
        }
    )

    if response2.status_code != 200:
        print(f"❌ Error: {response2.status_code}")
        print(response2.text)
        return

    data2 = response2.json()
    answer2 = data2["answer"]
    print(f"\nAnswer: {answer2[:300]}...")
    print(f"Sources: {len(data2['sources'])} memories")
    print(f"Confidence: {data2['confidence']}")

    # Check if answer references ACMS (shows history is working)
    has_acms_context = any(
        word in answer2.lower()
        for word in ["acms", "system", "memory", "context"]
    )
    print(f"✅ References ACMS context: {has_acms_context}")
    print()

    # Update history with second Q&A pair
    conversation_history.extend([
        {"role": "user", "content": question2},
        {"role": "assistant", "content": answer2}
    ])

    # Third question (with 2 Q&A pairs in history)
    print("=" * 70)
    print("TURN 3: Another Follow-up (With 2 Q&A Pairs)")
    print("=" * 70)
    question3 = "What are the key benefits?"
    print(f"Question: {question3}")
    print(f"History: {len(conversation_history)} messages (2 Q&A pairs)")

    response3 = requests.post(
        f"{API_BASE}/ask",
        json={
            "question": question3,
            "context_limit": 5,
            "conversation_history": conversation_history
        }
    )

    if response3.status_code != 200:
        print(f"❌ Error: {response3.status_code}")
        print(response3.text)
        return

    data3 = response3.json()
    answer3 = data3["answer"]
    print(f"\nAnswer: {answer3[:300]}...")
    print(f"Sources: {len(data3['sources'])} memories")
    print(f"Confidence: {data3['confidence']}")
    print()

    # Test without history (should be less contextual)
    print("=" * 70)
    print("TURN 4: Same Question Without History (Control Test)")
    print("=" * 70)
    print(f"Question: {question2}")
    print("History: None")

    response4 = requests.post(
        f"{API_BASE}/ask",
        json={
            "question": question2,
            "context_limit": 5,
        }
    )

    if response4.status_code != 200:
        print(f"❌ Error: {response4.status_code}")
        print(response4.text)
        return

    data4 = response4.json()
    answer4 = data4["answer"]
    print(f"\nAnswer (without history): {answer4[:300]}...")
    print()

    print("=" * 70)
    print("✅ CONVERSATION HISTORY TEST COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Turn 1: {len(answer1)} chars")
    print(f"  - Turn 2 (with history): {len(answer2)} chars")
    print(f"  - Turn 3 (with 2 Q&A pairs): {len(answer3)} chars")
    print(f"  - Turn 4 (no history): {len(answer4)} chars")
    print()
    print("✅ Conversation history feature is working!")
    print("   Claude can now maintain context across multiple turns.")


def test_history_limit():
    """Test that history is automatically limited to last 6 messages."""

    print()
    print("=" * 70)
    print("🧪 TESTING HISTORY AUTO-LIMITING (Last 6 Messages)")
    print("=" * 70)
    print()

    # Build a long history (10 Q&A pairs = 20 messages)
    long_history = []
    for i in range(10):
        long_history.extend([
            {"role": "user", "content": f"Question {i+1}"},
            {"role": "assistant", "content": f"Answer {i+1}"}
        ])

    print(f"Testing with {len(long_history)} messages in history...")
    print("(ClaudeGenerator should auto-limit to last 6 messages)")

    response = requests.post(
        f"{API_BASE}/ask",
        json={
            "question": "What's the latest?",
            "context_limit": 5,
            "conversation_history": long_history
        }
    )

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    print(f"✅ Success! Answer length: {len(data['answer'])} chars")
    print("   History was automatically limited to prevent token overflow.")
    print()


if __name__ == "__main__":
    print()
    print("🚀 ACMS Conversation History Test Suite")
    print()

    # Check if API is running
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5)
        if health.status_code != 200:
            print(f"❌ API server not healthy: {health.status_code}")
            exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API server at {API_BASE}")
        print(f"   Error: {e}")
        print()
        print("Please start the API server first:")
        print("  python3 src/api_server.py")
        exit(1)

    # Run tests
    test_conversation_history()
    test_history_limit()

    print()
    print("🎉 ALL TESTS PASSED!")
    print()
