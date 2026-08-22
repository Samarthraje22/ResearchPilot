import os
from dotenv import load_dotenv
from core.rag.pipeline import ResearchRAG


def test_multi_paper():
    load_dotenv()
    paper1 = "data/test_fixtures/research_paper.pdf"
    paper2 = "data/test_fixtures/test_fixture_quantum_error_correction.pdf"

    print("\n" + "=" * 70)
    print("       ResearchPilot - Multi-Paper Research Integration Test")
    print("=" * 70)

    rag = ResearchRAG()

    # 1. Ingest Paper 1
    chunks1 = rag.ingest_pdf(paper1)
    print(f"Paper 1 ({os.path.basename(paper1)}): {chunks1} chunks ingested.")

    # 2. Ingest Paper 2
    chunks2 = rag.ingest_pdf(paper2)
    print(f"Paper 2 ({os.path.basename(paper2)}): {chunks2} chunks ingested.")

    # 3. Test Duplicate Detection
    dup_chunks = rag.ingest_pdf(paper1)
    print(f"Duplicate Test ({os.path.basename(paper1)} re-ingest): {dup_chunks} chunks ingested (Expected: 0).")
    assert dup_chunks == 0, "Duplicate detection failed! Ingested identical paper again."

    # Print ingestion summary
    print("\nIngested Document Summary:")
    for src, count in rag.paper_chunk_counts.items():
        print(f"  - {os.path.basename(src)}: {count} chunks")

    # 4. Relevance-First Retrieval Test (Single Paper Query)
    single_q = "What is the Fisher information spectrum in quantum neural networks?"
    print("\n" + "=" * 70)
    print(f"SINGLE PAPER QUERY: {single_q}")
    print("=" * 70)

    res_single = rag.answer_question(single_q, top_k=3)
    print("\nRetrieved Evidence:")
    for ev in res_single["evidence"]:
        print(f"  [{ev['citation_id']}] {os.path.basename(ev['source'])} | Page {ev['page']} | Section: {ev['section']} | Score: {ev['score']:.4f}")

    # 5. Multi-Paper Comparative Query
    comp_q = "Compare the approaches used by these papers for improving quantum neural networks."
    print("\n" + "=" * 70)
    print(f"COMPARATIVE QUERY: {comp_q}")
    print("=" * 70)

    res_comp = rag.answer_question(comp_q, top_k=4)

    print("\n--- RETRIEVED MULTI-PAPER EVIDENCE ---")
    sources_in_evidence = set()
    for ev in res_comp["evidence"]:
        src_name = os.path.basename(ev['source'])
        sources_in_evidence.add(src_name)
        print(f"  [{ev['citation_id']}] {src_name} | Page {ev['page']} | Section: {ev['section']} | ChunkID: {ev['chunk_id']}")
        print(f"       Preview: {ev['content'][:150]}...")

    print(f"\nUnique Papers in Retrieved Evidence: {list(sources_in_evidence)}")
    assert len(sources_in_evidence) >= 2, f"Expected evidence from multiple papers, got: {sources_in_evidence}"

    print("\n--- GROUNDED COMPARATIVE SYNTHESIS ---")
    print(res_comp["answer"])

    print("\n[PASS] Multi-paper research integration test completed successfully!")


if __name__ == "__main__":
    test_multi_paper()
