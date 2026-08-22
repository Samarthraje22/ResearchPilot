from core.rag.pdf_loader import PDFLoader
from core.rag.chunker import TextChunker


def test_section_transitions():
    pdf_path = "data/test_fixtures/research_paper.pdf"
    loader = PDFLoader()
    documents = loader.load(pdf_path)

    chunker = TextChunker(chunk_size=800, overlap=150)
    chunks = []
    for doc in documents:
        chunks.extend(chunker.split(doc))

    print(f"\nLoaded {len(documents)} pages, created {len(chunks)} chunks.")

    # Collect unique sections in chronological order
    sections_seen = []
    for c in chunks:
        sec = c.section
        if sec and (not sections_seen or sections_seen[-1] != sec):
            sections_seen.append(sec)

    print("\nChronological Sections Detected:")
    for i, sec in enumerate(sections_seen, start=1):
        print(f"  {i}. {sec}")

    # Verify key sections are present and transitioning beyond "1 Introduction"
    expected_key_sections = [
        "1 Introduction",
        "3.1 The Fisher information",
        "4.1 The Fisher information spectrum",
        "5 Conclusion"
    ]

    missing = []
    for expected in expected_key_sections:
        if not any(expected.lower() in s.lower() for s in sections_seen):
            missing.append(expected)

    if missing:
        print(f"\n[FAIL] Missing expected section transitions: {missing}")
        assert False, f"Missing section transitions: {missing}"
    else:
        print("\n[PASS] All expected section transitions verified successfully!")


if __name__ == "__main__":
    test_section_transitions()
