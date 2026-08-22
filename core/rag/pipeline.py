import os
from typing import List, Dict, Any, Optional
from .document import Document
from .multi_pdf_loader import MultiPDFLoader
from .chunker import TextChunker
from .embedder import Embedder
from .vector_store import VectorStore
from .retriever import Retriever
from core.llm.base import LLM
from core.llm.router import LLMRouter
from core.sources.arxiv_source import ArxivSource
from core.sources.web_source import WebSource
from core.verification.claim_verifier import ClaimVerifier


class ResearchRAG:

    def __init__(
        self,
        llm: Optional[LLM] = None,
        chunk_size: int = 800,
        overlap: int = 150
    ):
        self.llm = llm or LLMRouter()
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        self.multi_loader = MultiPDFLoader()
        self.arxiv_source = ArxivSource()
        self.web_source = WebSource()
        self.claim_verifier = ClaimVerifier()
        self.embedder = Embedder()
        self.vector_store: Optional[VectorStore] = None
        self.retriever: Optional[Retriever] = None
        self.indexed_documents: List[Document] = []
        self.paper_chunk_counts: Dict[str, int] = {}

    def _index_documents(self, docs: List[Document], source_key: str) -> int:
        if not docs:
            return 0

        self.chunker.reset_state()
        chunks = []
        for doc in docs:
            chunks.extend(self.chunker.split(doc))

        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        embeddings = self.embedder.embed(texts)

        if self.vector_store is None:
            self.vector_store = VectorStore(dimension=len(embeddings[0]))

        self.vector_store.add(chunks, embeddings)
        self.retriever = Retriever(self.vector_store)
        self.indexed_documents.extend(chunks)

        self.paper_chunk_counts[source_key] = len(chunks)
        return len(chunks)

    def ingest_pdf(self, pdf_path: str) -> int:
        docs, is_dup = self.multi_loader.load_pdf(pdf_path)
        if is_dup or not docs:
            return 0
        return self._index_documents(docs, source_key=pdf_path)

    def ingest_documents(self, filepaths: List[str]) -> int:
        total = 0
        for fp in filepaths:
            if fp and os.path.exists(fp) and fp.endswith('.pdf'):
                total += self.ingest_pdf(fp)
        return total

    def ingest_directory(self, dir_path: str) -> Dict[str, int]:
        docs_by_file = self.multi_loader.load_directory(dir_path)
        summary = {}

        for file_path, docs in docs_by_file.items():
            cnt = self._index_documents(docs, source_key=file_path)
            if cnt > 0:
                summary[file_path] = cnt

        return summary

    def ingest_arxiv(self, query_or_id: str, max_results: int = 2) -> int:
        docs = self.arxiv_source.fetch(query_or_id, max_results=max_results)
        return self._index_documents(docs, source_key=f"arXiv:{query_or_id}")

    def ingest_web_page(self, url: str) -> int:
        docs = self.web_source.fetch(url)
        return self._index_documents(docs, source_key=url)

    def _build_context(self, retrieved_results: List[tuple[Document, float]]) -> tuple[str, List[Dict[str, Any]]]:
        context_blocks = []
        evidence_list = []
        seen_keys = set()
        citation_id = 1

        for doc, score in retrieved_results:
            key = doc.chunk_id if doc.chunk_id else f"{doc.source}_p{doc.page}_{doc.content[:50]}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            sec_info = f" ({doc.section})" if doc.section else ""
            year_info = f" ({doc.published_year})" if getattr(doc, 'published_year', None) else ""
            cid = doc.chunk_id or f"chunk_{citation_id}"
            header = f"[{citation_id}] Source: {doc.source}{year_info}, Page: {doc.page}{sec_info} [ChunkID: {cid}]"
            block = f"{header}\n{doc.content}"
            context_blocks.append(block)

            evidence_list.append({
                "citation_id": citation_id,
                "source": doc.source,
                "published_year": getattr(doc, 'published_year', None),
                "page": doc.page,
                "section": doc.section,
                "chunk_id": doc.chunk_id,
                "content": doc.content,
                "score": float(score)
            })
            citation_id += 1

        full_context = "\n\n".join(context_blocks)
        return full_context, evidence_list

    def answer_question(
        self,
        query: str,
        top_k: int = 4,
        verify_claims: bool = True,
        selected_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not self.retriever:
            raise ValueError("No documents have been ingested yet.")

        retrieved_results = self.retriever.retrieve(query, top_k=top_k, filter_references=True, selected_sources=selected_sources)
        context_str, evidence_list = self._build_context(retrieved_results)

        q_lower = query.lower()
        is_comparative = any(w in q_lower for w in ["compare", "comparison", "versus", "vs", "both", "different", "papers", "approaches"])

        if is_comparative:
            prompt = (
                "You are ResearchPilot, an AI research assistant. Provide a structured, source-grounded comparative synthesis.\n"
                "Do NOT use external knowledge or fabricate statements. Ground every claim strictly in the context.\n"
                "Format your response as follows:\n\n"
                "Summary:\n<Overall synthesis>\n\n"
                "Paper Analysis:\n- <Paper 1>: <approach, findings, limitations>\n- <Paper 2>: <approach, findings, limitations>\n\n"
                "Comparison:\n<Detailed comparative analysis of similarities, differences, and trade-offs>\n\n"
                "Support key claims with inline citations using [1], [2], etc., matching the exact context passages.\n\n"
                f"Context:\n{context_str}\n\n"
                f"Research Question: {query}\n\n"
                "Grounded Response:"
            )
        else:
            prompt = (
                "You are ResearchPilot, an AI research assistant. Answer the user's research question based strictly on the provided context.\n"
                "Do NOT use external knowledge or fabricate evidence. Always support key claims with inline citations using [1], [2], etc., corresponding to the context passages.\n\n"
                f"Context:\n{context_str}\n\n"
                f"Research Question: {query}\n\n"
                "Provide a comprehensive, source-grounded answer:"
            )

        answer = self.llm.generate(prompt)

        verification_report = None
        if verify_claims:
            verification_report = self.claim_verifier.verify_answer(answer, evidence_list)

        return {
            "query": query,
            "answer": answer,
            "evidence": evidence_list,
            "sources": list({f"{e['source']} (Page {e['page']})" for e in evidence_list}),
            "paper_chunk_counts": dict(self.paper_chunk_counts),
            "verification_report": verification_report
        }
