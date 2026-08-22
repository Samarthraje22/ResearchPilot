import os
from dotenv import load_dotenv
from core.rag.pipeline import ResearchRAG
from core.workflow.engine import ResearchWorkflow


def test_research_workflow_full():
    load_dotenv()

    print("\n" + "=" * 70)
    print("       ResearchPilot - Multi-Step Research Workflow Integration Test")
    print("=" * 70)

    # Initialize RAG pipeline and pre-ingest local research PDF
    rag = ResearchRAG()
    local_pdf = "data/test_fixtures/research_paper.pdf"
    pdf_chunks = rag.ingest_pdf(local_pdf)
    print(f"Pre-ingested real academic PDF ({os.path.basename(local_pdf)}): {pdf_chunks} chunks.")

    # Initialize Bounded Workflow Engine
    workflow = ResearchWorkflow(
        rag=rag,
        max_sub_questions=4,
        max_searches_per_sq=2,
        max_docs_per_sq=2,
        max_synthesis_chunks=8
    )

    topic = "Analyze recent approaches to quantum neural networks, compare their advantages and limitations, and identify potential research gaps."

    # Run bounded workflow
    result = workflow.run(topic, auto_ingest_arxiv=True)

    print("\n" + "=" * 70)
    print("                     STRUCTURED RESEARCH REPORT")
    print("=" * 70)
    print(result["report"])

    print("\n" + "=" * 70)
    print("                     SUB-QUESTION EVIDENCE BREAKDOWN")
    print("=" * 70)
    for sq_data in result["sub_question_evidence"]:
        print(f"  [{sq_data['sub_question_id']}] {sq_data['sub_question']}")
        print(f"       Objective: {sq_data['objective']}")
        print(f"       Retrieved Chunks: {sq_data['evidence_count']}")
        for ev in sq_data["evidence"][:2]:
            print(f"         - {ev['source']} | p. {ev['page']} | Section: {ev['section']} | Score: {ev['score']:.4f}")

    print("\n" + "=" * 70)
    print("                     CLAIM VERIFICATION REPORT")
    print("=" * 70)
    ver = result["verification_report"]
    print(f"  Total Claims: {ver['total_claims']}")
    print(f"  Supported ✅: {ver['supported_count']}")
    print(f"  Partially Supported ⚠️: {ver['partially_supported_count']}")
    print(f"  Unsupported ❌: {ver['unsupported_count']}")
    print(f"  Groundedness Score: {ver['groundedness_score']}")

    # Assertions for bounded workflow requirements
    assert len(result["plan"]["sub_questions"]) <= 4, "Exceeded maximum sub-question limit!"
    assert len(result["sub_question_evidence"]) > 0, "No sub-question evidence collected!"
    assert len(result["report"]) > 200, "Research report is too short!"
    assert "AI-Suggested Hypotheses" in result["report"] or "Potential Research Gaps" in result["report"], "Research gaps section missing!"

    print("\n[PASS] Multi-Step Research Workflow integration test completed successfully!")


if __name__ == "__main__":
    test_research_workflow_full()
