from abc import ABC, abstractmethod
from typing import List
from core.rag.document import Document


class BaseSource(ABC):

    @abstractmethod
    def fetch(self, query_or_url: str, max_results: int = 3) -> List[Document]:
        pass
