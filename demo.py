import argparse
import os
import sys
import time
from typing import Optional
from dotenv import load_dotenv
from core.rag.pipeline import ResearchRAG
from core.workflow.engine import ResearchWorkflow


def print_banner():
    banner = """
======================================================================
                  RESEARCHPILOT AI ASSISTANT CLI
        Grounded Academic Research, Verification & Synthesis Engine
======================================================================
"""
    print(banner)


def run_cli_demo(topic: Optional[str] = None):
    load_dotenv()
    print_banner()

    default_topic = "Analyze recent approaches to quantum neural networks, compare their advantages and limitations, and identify potential research gaps."

    if not topic:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            topic = sys.argv[1]
        else:
            print("Enter your research question below (Press Enter to use default demo query):")
            user_in = input(f"Query [{default_topic[:55]}...]: ").strip()
            topic = user_in if user_in else default_topic

    print(f"\n[RESEARCH TOPIC]: {topic}\n")

    # 1. Initialize RAG pipeline
    print("Initializing ResearchPilot Engine...")
    rag = ResearchRAG()

    # Pre-ingest local research PDF if available
    local_pdf = "data/test_fixtures/research_paper.pdf"
    if os.path.exists(local_pdf):
        cnt = rag.ingest_pdf(local_pdf)
        print(f"Loaded local paper ({os.path.basename(local_pdf)}): {cnt} chunks.")

    # 2. Initialize Bounded Workflow Engine
    workflow = ResearchWorkflow(
        rag=rag,
        max_sub_questions=3,
        max_searches_per_sq=2,
        max_docs_per_sq=2,
        max_synthesis_chunks=8
    )

    # 3. Execute Workflow
    print("\nStarting Multi-Step Research Workflow...")
    result = workflow.run(topic, auto_ingest_arxiv=True)

    # 4. Render Formatted Output
    print("\n" + "=" * 70)
    print("                    RESEARCHPILOT FINAL REPORT")
    print("=" * 70)
    print(result["report"])

    print("\n" + "=" * 70)
    print("                   SUB-QUESTION RESEARCH PLAN")
    print("=" * 70)
    for sq in result["plan"].get("sub_questions", []):
        print(f"  [{sq['id']}] {sq['sub_question']}")
        print(f"       Objective: {sq['objective']}")
        print(f"       Source Preference: {sq.get('source_preference', 'arxiv')}\n")

    print("=" * 70)
    print("                   EVIDENCE & CITATION TRACE")
    print("=" * 70)
    for ev in result["evidence"]:
        sec = f" ({ev['section']})" if ev.get('section') else ""
        year_str = f" ({ev['published_year']})" if ev.get('published_year') else ""
        cid = ev.get('chunk_id') or f"chunk_{ev['citation_id']}"
        print(f"  [{ev['citation_id']}] {ev['source']}{year_str} | Page {ev['page']}{sec} | Score: {ev['score']:.4f}")
        print(f"       ChunkID: {cid}")
        print(f"       Preview: {ev['content'][:130]}...\n")

    print("=" * 70)
    print("                CLAIM VERIFICATION & GROUNDEDNESS")
    print("=" * 70)
    ver = result["verification_report"]
    print(f"  Groundedness Score: {ver['groundedness_score']} (Pass Criterion >= 0.70)")
    print(f"  Total Claims Evaluated: {ver['total_claims']}")
    print(f"  Supported Claims ✅: {ver['supported_count']}")
    print(f"  Partially Supported ⚠️: {ver['partially_supported_count']}")
    print(f"  Unsupported Claims ❌: {ver['unsupported_count']}\n")

    for c in ver["claims"]:
        print(f"  [{c['status']}] Claim: {c['claim'][:110]}...")
        print(f"       Matched Ref: [{c['matched_citation_id']}] | Overlap Score: {c['overlap_score']}\n")

    print("=" * 70)
    print(f"Workflow completed successfully in {result['execution_time_sec']} seconds.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ResearchPilot CLI Demonstration")
    parser.add_argument("--topic", type=str, help="Research topic or question to investigate")
    args = parser.parse_args()
    run_cli_demo(topic=args.topic)
