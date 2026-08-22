from core.workflow.planner import ResearchPlanner


def test_planner():
    print("\n" + "=" * 70)
    print("       ResearchPilot - ResearchPlanner Unit Test")
    print("=" * 70)

    planner = ResearchPlanner(max_sub_questions=4)
    topic = "Quantum neural networks: architectures, trainability, and limitations"

    print(f"\nDecomposing topic: '{topic}'...")
    plan = planner.create_plan(topic)

    print(f"\nMain Topic: {plan['main_topic']}")
    print(f"Generated {len(plan['sub_questions'])} sub-questions (Max allowed: 4):")

    for sq in plan["sub_questions"]:
        print(f"  [{sq['id']}] Question: {sq['sub_question']}")
        print(f"       Objective: {sq['objective']}")
        print(f"       Preference: {sq.get('source_preference', 'arxiv')}\n")

    assert len(plan["sub_questions"]) > 0, "No sub-questions generated!"
    assert len(plan["sub_questions"]) <= 4, "Exceeded max sub-question limit!"

    print("[PASS] ResearchPlanner unit test completed successfully!")


if __name__ == "__main__":
    test_planner()
