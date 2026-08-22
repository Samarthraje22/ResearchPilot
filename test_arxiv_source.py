from core.sources.arxiv_source import ArxivSource
from core.sources.web_source import WebSource


def test_sources():
    print("\n" + "=" * 70)
    print("       ResearchPilot - External Sources Integration Test")
    print("=" * 70)

    # 1. Test arXiv Source
    arxiv = ArxivSource()
    print("\n[1] Fetching real arXiv papers for query: 'quantum neural networks'...")
    arxiv_docs = arxiv.fetch("quantum neural networks", max_results=2)
    print(f"Fetched {len(arxiv_docs)} arXiv papers:")

    for i, doc in enumerate(arxiv_docs, 1):
        print(f"  {i}. Source: {doc.source}")
        print(f"     Title: {doc.title}")
        print(f"     Section: {doc.section}")
        print(f"     Content Preview: {doc.content[:150]}...\n")

    assert len(arxiv_docs) > 0, "ArxivSource failed to fetch papers!"

    # 2. Test Web Source
    web = WebSource()
    print("\n[2] Fetching web content from Wikipedia arXiv page...")
    web_docs = web.fetch("https://en.wikipedia.org/wiki/ArXiv")
    print(f"Fetched {len(web_docs)} web documents:")

    for doc in web_docs:
        print(f"  Source: {doc.source}")
        print(f"  Title: {doc.title}")
        print(f"  Content Preview: {doc.content[:150]}...\n")

    assert len(web_docs) > 0, "WebSource failed to fetch web page!"

    print("[PASS] External sources test completed successfully!")


if __name__ == "__main__":
    test_sources()
