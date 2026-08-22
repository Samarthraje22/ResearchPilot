from core.rag.pdf_loader import PDFLoader


if __name__ == "__main__":
    pdf_path = "data/test_fixtures/research_paper.pdf"
    loader = PDFLoader()
    documents = loader.load(pdf_path)

    print(f"\nPages loaded: {len(documents)}\n")

    for document in documents[:3]:
        print("=" * 60)
        print("Page:", document.page)
        print("Source:", document.source)
        print("Text preview:")
        print(document.content[:500])
        print()






