import os
from dotenv import load_dotenv
from core.rag.pipeline import ResearchRAG


def test_phase3_full():
    load_dotenv()

    print("\n" + "=" * 70)
    print("       ResearchPilot - Phase 3 Real Academic & Web Research Test")
    print("=" * 70)

    rag = ResearchRAG()

    # 1. Ingest Real Local PDF
    pdf_path = "data/test_fixtures/research_paper.pdf"
    pdf_chunks = rag.ingest_pdf(pdf_path)
    print(f"[1] Ingested Local Paper ({os.path.basename(pdf_path)}): {pdf_chunks} chunks.")

    # 2. Ingest Real arXiv Paper
    arxiv_query = "2011.00027"
    arxiv_chunks = rag.ingest_arxiv(arxiv_query, max_results=1)
    print(f"[2] Ingested arXiv Paper ({arxiv_query}): {arxiv_chunks} chunks.")

    # 3. Ingest Real Web Page
    web_url = "https://en.wikipedia.org/wiki/Quantum_neural_network"
    web_chunks = rag.ingest_web_page(web_url)
    print(f"[3] Ingested Web Source ({web_url}): {web_chunks} chunks.")

    print("\nIngested Sources Summary:")
    for src, count in rag.paper_chunk_counts.items():
        print(f"  - {src}: {count} chunks")

    # 4. Perform Grounded Research Answer with Verification
    q = "What is a quantum neural network and what advantages does it offer?"
    print("\n" + "=" * 70)
    print(f"RESEARCH QUESTION: {q}")
    print("=" * 70)

    res = rag.answer_question(q, top_k=4, verify_claims=True)

    print("\n--- GROUNDED RESPONSE ---")
    print(res["answer"])

    print("\n--- RETRIEVED EVIDENCE SOURCES ---")
    for ev in res["evidence"]:
        print(f"  [{ev['citation_id']}] Source: {ev['source']} | Page {ev['page']} | Section: {ev['section']} | Score: {ev['score']:.4f}")

    print("\n--- CLAIM VERIFICATION REPORT ---")
    report = res["verification_report"]
    print(f"  Total Claims Evaluated: {report['total_claims']}")
    print(f"  Supported ✅: {report['supported_count']}")
    print(f"  Partially Supported ⚠️: {report['partially_supported_count']}")
    print(f"  Unsupported ❌: {report['unsupported_count']}")
    print(f"  Groundedness Score: {report['groundedness_score']}")

    for c in report["claims"]:
        print(f"  [{c['status']}] Claim: {c['claim'][:120]}... (Overlap: {c['overlap_score']})")

    assert len(res["evidence"]) > 0, "No evidence retrieved!"
    assert report["total_claims"] > 0, "No claims verified!"

    print("\n[PASS] Phase 3 integration test completed successfully!")


if __name__ == "__main__":
    test_phase3_full()
