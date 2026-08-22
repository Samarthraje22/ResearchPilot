import sys
from core.rag.pdf_loader import PDFLoader
from core.rag.chunker import TextChunker
from core.rag.embedder import Embedder
from core.rag.vector_store import VectorStore
from core.rag.retriever import Retriever


def test_retrieval():
    pdf_path = "data/test_fixtures/research_paper.pdf"
    loader = PDFLoader()
    documents = loader.load(pdf_path)
    print(f"Loaded {len(documents)} pages")

    chunker = TextChunker(chunk_size=1000, overlap=200)
    chunks = []
    for document in documents:
        chunks.extend(chunker.split(document))

    ref_chunks = [c for c in chunks if c.is_reference]
    print(f"Created {len(chunks)} chunks (References marked: {len(ref_chunks)})")

    embedder = Embedder()
    texts = [chunk.content for chunk in chunks]
    embeddings = embedder.embed(texts)
    print(f"Created {len(embeddings)} embeddings")

    vector_store = VectorStore(dimension=len(embeddings[0]))
    vector_store.add(chunks, embeddings)
    print("Vector store ready")

    retriever = Retriever(vector_store)

    test_queries = [
        "What problem are the authors trying to solve?",
        "What is the main idea of this paper?"
    ]

    if len(sys.argv) > 1 and sys.argv[1].strip():
        test_queries = [sys.argv[1].strip()]

    for query in test_queries:
        print("\n" + "=" * 70)
        print(f"QUERY: {query}")
        print("=" * 70)

        results = retriever.retrieve(query, top_k=3, filter_references=True)

        for i, (doc, score) in enumerate(results, start=1):
            print(f"\n--- Result {i} ---")
            print(f"Page: {doc.page}")
            print(f"Section: {doc.section}")
            print(f"Is Reference: {doc.is_reference}")
            print(f"Similarity Score: {score:.4f}")
            print("Preview:")
            print(doc.content[:300] + ("..." if len(doc.content) > 300 else ""))


if __name__ == "__main__":
    test_retrieval()