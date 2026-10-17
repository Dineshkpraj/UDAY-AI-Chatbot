"""Blind, synthetic A/B evaluation of UDAY's memory-based personalization."""

import random

from google import genai
from google.genai import types

from config import get_gemini_api_key, get_model_name
from memory import rank_relevant_facts


CASES = [
    {
        "name": "response style preference",
        "facts": [
            "The user prefers concise, practical answers.",
            "The user enjoys gardening on weekends.",
            "The user works evening shifts at a hospital.",
        ],
        "message": "Work has been stressful today. Can you give me one concise, practical step for right now?",
    },
    {
        "name": "avoid an unhelpful coping suggestion",
        "facts": [
            "Box breathing makes the user feel uncomfortable.",
            "The user likes taking short walks outside.",
            "The user is learning to cook vegetarian meals.",
        ],
        "message": "I feel tense before a presentation. Could a breathing exercise help?",
    },
    {
        "name": "relevant ongoing context",
        "facts": [
            "The user is a nursing student preparing for exams.",
            "The user prefers suggestions broken into small steps.",
            "The user has a pet cat named Miso.",
        ],
        "message": "I am overwhelmed by everything I need to do this week. Can you break it into small steps?",
    },
]


def build_prompt(message, memories):
    memory_section = (
        "\nUser-approved context that is relevant to this message:\n"
        + "\n".join(f"- {fact}" for fact in memories)
        if memories
        else ""
    )
    return (
        "You are UDAY, a warm, concise mental wellness companion. Do not diagnose or "
        "make clinical claims. Offer one or two practical, low-risk suggestions."
        + memory_section
        + f"\n\nUser message: {message}"
    )


def main():
    client = genai.Client(api_key=get_gemini_api_key())
    rng = random.Random(2026)

    print("Synthetic A/B evaluation: compare relevance and personalization.")
    print("No real user conversations are used. Review outputs for helpfulness, fact use, and unsupported assumptions.\n")
    for case in CASES:
        memories = rank_relevant_facts(case["facts"], case["message"], limit=3)
        conditions = [
            ("without memory", []),
            ("with retrieved memory", memories),
        ]
        rng.shuffle(conditions)
        labels = ["A", "B"]
        print(f"=== {case['name']} ===")
        outputs = {}
        for label, (condition, context) in zip(labels, conditions):
            response = client.models.generate_content(
                model=get_model_name(),
                contents=build_prompt(case["message"], context),
                config=types.GenerateContentConfig(temperature=0),
            )
            outputs[label] = (condition, context)
            print(f"\n{label}: {response.text.strip()}")
        print("\nBlind comparison: rate A and B for personal relevance, accurate context use, and unsupported assumptions.")
        for label, (condition, context) in outputs.items():
            print(f"{label} was {condition}; selected facts: {context or '[none]'}")
        print()


if __name__ == "__main__":
    main()
