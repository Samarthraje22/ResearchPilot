from core.rag.document import Document
from core.rag.chunker import TextChunker
from core.rag.embedder import Embedder
from core.rag.vector_store import VectorStore


# 1. Create documents
documents = [
    Document(
        content="Machine learning allows computers to learn patterns from data.",
        source="test",
        title="Machine Learning"
    ),
    Document(
        content="Deep learning uses neural networks with many layers.",
        source="test",
        title="Deep Learning"
    ),
    Document(
        content="The Earth revolves around the Sun.",
        source="test",
        title="Astronomy"
    )
]


# 2. Create embeddings
embedder = Embedder()

texts = [document.content for document in documents]

embeddings = embedder.embed(texts)


# 3. Create vector store
vector_store = VectorStore(
    dimension=len(embeddings[0])
)


# 4. Add documents
vector_store.add(
    documents,
    embeddings
)


# 5. Search
query = "How do computers learn from data?"

query_embedding = embedder.embed([query])[0]

results = vector_store.search(
    query_embedding,
    top_k=2
)


# 6. Display results
print("\nSearch query:")
print(query)

print("\nMost relevant documents:\n")

for document, distance in results:

    print("Title:", document.title)
    print("Content:", document.content)
    print("Distance:", distance)
    print("-" * 50)