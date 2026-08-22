import re
import os
from typing import List, Tuple, Optional
from .document import Document
from .embedder import Embedder
from .vector_store import VectorStore


class Retriever:

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.embedder = Embedder()

    def _is_reference_query(self, query: str) -> bool:
        q_lower = query.lower()
        ref_triggers = ["reference", "references", "bibliography", "citation", "cited", "author", "authors"]
        return any(trig in q_lower for trig in ref_triggers)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filter_references: bool = True,
        selected_sources: Optional[List[str]] = None
    ) -> List[Tuple[Document, float]]:

        # Over-sample to get a good candidate pool for reranking/filtering
        candidate_k = max(top_k * 5, 20)
        query_embedding = self.embedder.embed([query])[0]

        candidates = self.vector_store.search(
            query_embedding,
            top_k=candidate_k
        )

        if not candidates:
            return []

        # Filter by selected sources if provided
        if selected_sources:
            norm_selected = [os.path.basename(s).lower() for s in selected_sources]
            candidates = [
                (doc, score) for doc, score in candidates
                if (doc.source.startswith("arXiv:") or any(ns in doc.source.lower() for ns in norm_selected))
            ]

        if not candidates:
            return []

        is_ref_q = self._is_reference_query(query)
        should_filter_refs = filter_references and not is_ref_q

        filtered_candidates = []
        for doc, score in candidates:
            if should_filter_refs and doc.is_reference:
                continue
            filtered_candidates.append((doc, score))

        # Fallback to candidates including references if no non-reference candidates match
        if not filtered_candidates:
            filtered_candidates = candidates

        # Rerank candidates with lightweight section score adjustment
        scored_results = []
        q_lower = query.lower()
        is_broad_q = any(w in q_lower for w in ["main idea", "problem", "contribution", "overview", "summary", "propose", "solve", "abstract"])

        for doc, sim_score in filtered_candidates:
            final_score = float(sim_score)
            sec_lower = (doc.section or "").lower()

            if is_broad_q:
                if "abstract" in sec_lower:
                    final_score += 0.15
                elif "introduction" in sec_lower:
                    final_score += 0.10
                elif "conclusion" in sec_lower:
                    final_score += 0.05

            scored_results.append((doc, final_score))

        # Sort descending by adjusted score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        is_comparative = any(w in q_lower for w in ["compare", "comparison", "versus", "vs", "both", "different", "papers", "approaches"])
        
        # Source-aware diversification (relevance-first)
        if len(scored_results) > top_k and (is_comparative or top_k >= 4):
            top_score = scored_results[0][1]
            relevance_threshold = max(0.15, top_score * 0.65)
            
            selected = []
            seen_sources = set()
            
            # First pass: take highest scoring chunk from each relevant source above threshold
            for doc, score in scored_results:
                if score >= relevance_threshold and doc.source not in seen_sources:
                    selected.append((doc, score))
                    seen_sources.add(doc.source)
                    if len(selected) >= top_k:
                        break
                        
            # Second pass: fill remaining slots with highest remaining overall scores
            if len(selected) < top_k:
                for item in scored_results:
                    if item not in selected:
                        selected.append(item)
                        if len(selected) >= top_k:
                            break
                            
            # Sort final selected list by score descending
            selected.sort(key=lambda x: x[1], reverse=True)
            return selected[:top_k]

        return scored_results[:top_k]