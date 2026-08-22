from core.rag.document import Document
from core.rag.chunker import TextChunker


document = Document(
    content=(
        "Machine learning allows computers to learn from data. "
        "Deep learning uses neural networks to learn complex patterns. "
        "Natural language processing allows computers to work with human language."
    ),
    source="test",
    title="AI Basics"
)


chunker = TextChunker(
    chunk_size=50,
    overlap=10
)


chunks = chunker.split(document)


print(f"\nCreated {len(chunks)} chunks:\n")


for i, chunk in enumerate(chunks, 1):

    print(f"--- Chunk {i} ---")
    print(chunk.content)
    print()