import os
from dotenv import load_dotenv
from core.rag.pipeline import ResearchRAG


def test_pipeline():
    load_dotenv()
    pdf_path = "data/test_fixtures/research_paper.pdf"

    print("\n" + "=" * 70)
    print("       ResearchPilot - RAG Grounded Answer Test")
    print("=" * 70)

    rag = ResearchRAG()
    num_chunks = rag.ingest_pdf(pdf_path)
    print(f"Ingested PDF: {num_chunks} chunks created.")

    queries = [
        "What problem are the authors trying to solve?",
        "What is the main idea of this paper?"
    ]

    for q in queries:
        print("\n" + "=" * 70)
        print(f"QUESTION: {q}")
        print("=" * 70)

        result = rag.answer_question(q, top_k=3)

        print("\n--- GROUNDED ANSWER ---")
        print(result["answer"])

        print("\n--- RETRIEVED EVIDENCE ---")
        for ev in result["evidence"]:
            print(f"[{ev['citation_id']}] {ev['source']} | Page {ev['page']} | Section: {ev['section']} | Score: {ev['score']:.4f}")
            print(f"     Preview: {ev['content'][:150]}...")


if __name__ == "__main__":
    test_pipeline()
