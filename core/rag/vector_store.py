import faiss
import numpy as np

from .document import Document


class VectorStore:

    def __init__(self, dimension: int):
        self.index = faiss.IndexFlatIP(dimension)
        self.documents = []

    def add(self, documents: list[Document], embeddings):

        vectors = np.array(embeddings).astype("float32")

        faiss.normalize_L2(vectors)

        self.index.add(vectors)
        self.documents.extend(documents)

    def search(self, query_embedding, top_k: int = 3):

        query_vector = np.array(
            [query_embedding]
        ).astype("float32")

        faiss.normalize_L2(query_vector)

        scores, indices = self.index.search(
            query_vector,
            top_k
        )

        results = []

        for score, index in zip(
            scores[0],
            indices[0]
        ):
            if index != -1:
                results.append(
                    (self.documents[index], score)
                )

        return results