from dataclasses import dataclass
from typing import Optional


@dataclass
class Document:
    content: str
    source: str
    title: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    is_reference: bool = False
    chunk_id: Optional[str] = None
    published_year: Optional[int] = None