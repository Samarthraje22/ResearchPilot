import os
import re
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from core.rag.pipeline import ResearchRAG
from core.workflow.planner import ResearchPlanner
from core.verification.claim_verifier import ClaimVerifier


class ResearchWorkflow:

    RECENCY_KEYWORDS = ["recent", "latest", "current", "state of the art", "up-to-date", "sota", "2024", "2025", "2026"]
    STOP_WORDS = {
        # Basic English stop words
        "what", "is", "the", "of", "on", "in", "and", "or", "to", "a", "an", "for", "with",
        "across", "are", "this", "that", "these", "those", "from", "about", "into", "between",
        "through", "does", "will", "would", "could", "should", "have", "has", "had", "been",
        "being", "were", "was", "not", "also", "more", "most", "some", "any", "each", "every",
        "both", "such", "than", "then", "when", "where", "which", "while", "after", "before",
        "other", "only", "very", "just", "over", "under",
        # Common question/conversational words (NOT technical terms)
        "how", "does", "compare", "specific", "performance", "impact", "classical",
        "what", "why", "explain", "describe", "discuss", "tell", "give", "show", "list",
        "basic", "idea", "ideas", "main", "key", "primary", "general", "overall", "brief",
        "summary", "summarize", "overview", "introduction", "paper", "papers", "document",
        "research", "study", "work", "example", "examples", "detail", "details", "detailed",
        "please", "help", "find", "provide", "write", "make", "using", "used", "based",
        "approach", "method", "methods", "result", "results", "finding", "findings",
        "topic", "concept", "concepts", "point", "points", "important", "can", "like",
    }

    def __init__(
        self,
        rag: Optional[ResearchRAG] = None,
        max_sub_questions: int = 4,
        max_searches_per_sq: int = 2,
        max_docs_per_sq: int = 2,
        max_synthesis_chunks: int = 8,
        recent_years_window: int = 3,
        current_year: int = 2026,
        sufficiency_threshold: float = 0.35
    ):
        self.rag = rag or ResearchRAG()
        self.planner = ResearchPlanner(llm=self.rag.llm, max_sub_questions=max_sub_questions)
        self.verifier = ClaimVerifier()
        self.max_sub_questions = max_sub_questions
        self.max_searches_per_sq = max_searches_per_sq
        self.max_docs_per_sq = max_docs_per_sq
        self.max_synthesis_chunks = max_synthesis_chunks
        self.recent_years_window = recent_years_window
        self.current_year = current_year
        self.min_recent_year = current_year - recent_years_window
        self.sufficiency_threshold = sufficiency_threshold
        self.ingested_source_keys: set = set()

        # LLM Profiling Metrics
        self.total_llm_calls = 0
        self.llm_calls_by_stage: Dict[str, int] = {}
        self.stage_latencies_sec: Dict[str, float] = {}

    def _fetch_arxiv_sq(self, sq: Dict[str, Any], auto_ingest_arxiv: bool) -> tuple[str, int]:
        sq_text = sq["sub_question"]
        pref = sq.get("source_preference", "arxiv")
        if auto_ingest_arxiv and pref == "arxiv":
            query_key = f"arXiv:{sq_text[:40]}"
            if query_key not in self.ingested_source_keys:
                try:
                    print(f"  - Searching arXiv for SQ '{sq['id']}': {sq_text[:50]}...", flush=True)
                    chunks_cnt = self.rag.ingest_arxiv(sq_text, max_results=self.max_docs_per_sq)
                    self.ingested_source_keys.add(query_key)
                    return query_key, chunks_cnt
                except Exception as e:
                    print(f"  - [WARNING] arXiv ingestion failed for '{sq_text}': {e}. Continuing with existing corpus...", flush=True)
        return "", 0

    def _assess_evidence_sufficiency(self, topic: str, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate Evidence Sufficiency considering:
        - Critical entities/terms (words with digits, hyphens, or domain proper nouns)
        - Evidence similarity/relevance scores
        - Topic concept coverage
        """
        if not evidence_list:
            return {
                "is_sufficient": False,
                "coverage_score": 0.0,
                "avg_relevance_score": 0.0,
                "max_relevance_score": 0.0,
                "missing_terms": [topic],
                "matched_terms": []
            }

        # Extract critical topic terms/entities
        raw_words = re.findall(r'\b[a-zA-Z0-9\-]+\b', topic.lower())
        critical_terms = [w for w in raw_words if len(w) >= 4 and w not in self.STOP_WORDS and not w.endswith('.pdf')]

        # If no critical terms remain (or very few), the query is a general/overview
        # question — pass through to synthesis instead of gating
        if len(critical_terms) <= 2:
            return {"is_sufficient": True, "coverage_score": 1.0, "missing_terms": []}

        all_evidence_text = " ".join([ev.get("content", "").lower() for ev in evidence_list])
        matched_terms = [t for t in critical_terms if t in all_evidence_text]
        missing_terms = [t for t in critical_terms if t not in all_evidence_text]

        term_coverage = len(matched_terms) / float(len(critical_terms))

        # Check average and max retriever relevance score
        scores = [float(ev.get("score", 0.0)) for ev in evidence_list]
        avg_score = sum(scores) / float(len(scores)) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        # High-weight penalty for specific numerical/entity terms missing (e.g. '1000-qubit', 'braiding')
        specific_entities_missing = any(re.search(r'\d+', term) or '-' in term for term in missing_terms)

        is_sufficient = (
            (term_coverage >= self.sufficiency_threshold or avg_score >= 0.70 or max_score >= 0.70)
            and not specific_entities_missing
        )

        return {
            "is_sufficient": is_sufficient,
            "coverage_score": round(term_coverage, 3),
            "avg_relevance_score": round(avg_score, 3),
            "max_relevance_score": round(max_score, 3),
            "missing_terms": missing_terms,
            "matched_terms": matched_terms
        }

    def run(self, topic: str, auto_ingest_arxiv: bool = True, selected_sources: Optional[List[str]] = None) -> Dict[str, Any]:
        start_time = time.time()
        self.total_llm_calls = 0
        self.llm_calls_by_stage = {"planning": 0, "discovery": 0, "synthesis": 0, "verification": 0}
        self.stage_latencies_sec = {}

        print("\n" + "=" * 70)
        print("       ResearchPilot - Bounded Multi-Step Research Workflow")
        print("=" * 70)
        print(f"[STAGE 1/6] Topic: '{topic}'")

        topic_lower = topic.lower()
        is_recency_query = any(kw in topic_lower for kw in self.RECENCY_KEYWORDS)
        if is_recency_query:
            print(f"[RECENCY POLICY ACTIVE] Target publication window: {self.min_recent_year}–{self.current_year} (Last {self.recent_years_window} years).")

        # STAGE 1: Generate Plan
        s1_start = time.time()
        plan = self.planner.create_plan(topic)
        self.total_llm_calls += 1
        self.llm_calls_by_stage["planning"] += 1
        self.stage_latencies_sec["planning"] = round(time.time() - s1_start, 2)

        sub_questions = plan.get("sub_questions", [])[:self.max_sub_questions]
        print(f"[STAGE 1/6] Research Plan created with {len(sub_questions)} sub-questions.")

        # STAGE 2: Source Discovery & Ingestion per Sub-Question
        s2_start = time.time()
        print("\n[STAGE 2/6] Source Discovery & Ingestion...")
        ingested_summary = {}

        if selected_sources:
            try:
                self.rag.ingest_documents(selected_sources)
            except Exception as e:
                print(f"  - [WARNING] Failed to ingest selected sources: {e}")

        if auto_ingest_arxiv:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_sub_questions) as executor:
                future_to_sq = {
                    executor.submit(self._fetch_arxiv_sq, sq, auto_ingest_arxiv): sq["id"]
                    for sq in sub_questions
                }
                for future in concurrent.futures.as_completed(future_to_sq):
                    qk, cnt = future.result()
                    if qk:
                        ingested_summary[qk] = cnt
        self.stage_latencies_sec["discovery"] = round(time.time() - s2_start, 2)

        # STAGE 3: Sub-Question Evidence Collection
        s3_start = time.time()
        print("\n[STAGE 3/6] Evidence Collection per Sub-Question...")
        evidence_by_sq: List[Dict[str, Any]] = []
        all_retrieved_chunks: List[tuple[Any, float]] = []

        for sq in sub_questions:
            sq_text = sq["sub_question"]
            sq_id = sq["id"]
            try:
                retrieved = self.rag.retriever.retrieve(sq_text, top_k=self.max_docs_per_sq, filter_references=True, selected_sources=selected_sources) if self.rag.retriever else []
                sq_evidence = []
                for doc, score in retrieved:
                    all_retrieved_chunks.append((doc, score))
                    sq_evidence.append({
                        "source": doc.source,
                        "published_year": getattr(doc, 'published_year', None),
                        "page": doc.page,
                        "section": doc.section,
                        "chunk_id": doc.chunk_id,
                        "content": doc.content,
                        "score": float(score)
                    })

                evidence_by_sq.append({
                    "sub_question_id": sq_id,
                    "sub_question": sq_text,
                    "objective": sq["objective"],
                    "evidence_count": len(sq_evidence),
                    "evidence": sq_evidence
                })
                print(f"  - [{sq_id}] Retrieved {len(sq_evidence)} evidence chunks.")
            except Exception as e:
                print(f"  - [WARNING] Retrieval failed for sub-question '{sq_id}': {e}")

        # Deduplicate retrieved chunks by chunk_id
        unique_chunks_dict = {}
        for doc, score in all_retrieved_chunks:
            key = doc.chunk_id if doc.chunk_id else f"{doc.source}_p{doc.page}_{doc.content[:50]}"
            if key not in unique_chunks_dict or score > unique_chunks_dict[key][1]:
                unique_chunks_dict[key] = (doc, score)

        deduped_chunks = list(unique_chunks_dict.values())

        # Recency sorting & filtering if recency query active
        recent_chunks = []
        older_chunks = []
        if is_recency_query:
            for doc, score in deduped_chunks:
                py = getattr(doc, 'published_year', None)
                if py and py >= self.min_recent_year:
                    recent_chunks.append((doc, score))
                else:
                    older_chunks.append((doc, score))

            recent_chunks.sort(key=lambda x: x[1], reverse=True)
            older_chunks.sort(key=lambda x: x[1], reverse=True)

            if recent_chunks:
                top_synthesis_results = (recent_chunks + older_chunks)[:self.max_synthesis_chunks]
            else:
                print(f"  - [RECENCY NOTICE] No academic sources from {self.min_recent_year}–{self.current_year} were retrieved. Using established literature baseline.")
                top_synthesis_results = older_chunks[:self.max_synthesis_chunks]
        else:
            deduped_chunks.sort(key=lambda x: x[1], reverse=True)
            top_synthesis_results = deduped_chunks[:self.max_synthesis_chunks]

        context_str, evidence_list = self.rag._build_context(top_synthesis_results)
        self.stage_latencies_sec["retrieval"] = round(time.time() - s3_start, 2)

        # EVIDENCE SUFFICIENCY GATE (BEFORE SYNTHESIS)
        sufficiency = self._assess_evidence_sufficiency(topic, evidence_list)

        s4_start = time.time()
        if not sufficiency["is_sufficient"]:
            print(f"\n[EVIDENCE SUFFICIENCY GATE] Result: INSUFFICIENT EVIDENCE (Coverage Score: {sufficiency['coverage_score']}, Missing: {sufficiency['missing_terms']})")
            print("  - Skipping speculative factual synthesis. Generating concise insufficient-evidence response...")

            missing_str = ", ".join([f"'{t}'" for t in sufficiency['missing_terms']])
            sources_str = ", ".join(list({e['source'] for e in evidence_list})) if evidence_list else "None"

            report_text = (
                f"# Executive Summary (Insufficient Evidence Notice)\n"
                f"[INSUFFICIENT EVIDENCE NOTICE]: The retrieved literature corpus does not contain documented empirical evidence or research findings regarding '{topic}'.\n\n"
                f"## Missing Evidence Details\n"
                f"- **Missing Requested Terms/Entities**: {missing_str}\n"
                f"- **Available Literature Sources**: {sources_str}\n\n"
                f"## Available Context Findings\n"
                f"The available corpus does not provide sufficient data for the specific requested terms. No speculative claims are asserted.\n"
            )
        else:
            print(f"\n[EVIDENCE SUFFICIENCY GATE] Result: SUFFICIENT EVIDENCE (Coverage Score: {sufficiency['coverage_score']})")
            print("[STAGE 4/6] Synthesizing Multi-Step Research Report...")

            recency_disclaimer_prompt = ""
            if is_recency_query and not recent_chunks:
                recency_disclaimer_prompt = f"\n[RECENCY NOTICE]: Note that no academic papers from the recent window ({self.min_recent_year}–{self.current_year}) were retrieved for this topic. Findings rely on established historical literature baseline (2019-2020).\n"

            synthesis_prompt = (
                "You are ResearchPilot, an expert AI research assistant. Synthesize a comprehensive, cited research report based strictly on the provided context.\n"
                "CRITICAL EVIDENCE-FIRST RULES:\n"
                "- Every substantive factual or scientific claim MUST map to one or more retrieved evidence passages with an inline citation [1], [2].\n"
                "- Do NOT add ungrounded background essays, speculative theories, or decorative fluff.\n"
                "- Do NOT infer or invent specific metrics, qubit counts, hardware parameters, or benchmark numbers unless they appear VERBATIM in the context.\n"
                "- Structural headings, section titles, and meta explanations do not require citations, but ALL scientific statements must be cited.\n"
                f"{recency_disclaimer_prompt}\n"
                "Required Report Sections:\n"
                "# Executive Summary\n<High-level summary of findings with citations>\n\n"
                "# Sub-Question Findings\n<Detailed findings per sub-question with citations>\n\n"
                "# Comparative Analysis\n<Comparison of approaches, advantages, and limitations with citations>\n\n"
                "# Potential Research Gaps & Suggested Directions (AI-Suggested Hypotheses)\n"
                "*(Note: The following potential gaps are AI-suggested research directions derived strictly from literature limitations, not asserted facts.)*\n"
                "For EACH suggested research gap, provide:\n"
                "- **Gap Title**: [AI-Suggested Hypothesis] <descriptive title>\n"
                "- **Supporting Source(s)**: <citation [1], [2]>\n"
                "- **Supporting Evidence Quote**: <verbatim quote from context>\n"
                "- **Stated Literature Limitation**: <exact limitation stated in quote>\n"
                "- **Proposed Direction**: <logical future direction directly addressing that stated limitation>\n\n"
                f"Context Passages:\n{context_str}\n\n"
                f"Research Topic: {topic}\n\n"
                "Structured Cited Research Report:"
            )

            try:
                report_text = self.rag.llm.generate(synthesis_prompt)
                self.total_llm_calls += 1
                self.llm_calls_by_stage["synthesis"] += 1
                if is_recency_query and not recent_chunks:
                    report_text = f"[RECENCY NOTICE]: No academic sources from {self.min_recent_year}–{self.current_year} were retrieved. Findings rely on established literature baseline.\n\n" + report_text
            except Exception as e:
                print(f"[ResearchWorkflow ERROR] Report synthesis failed: {e}")
                report_text = "Report synthesis unavailable due to LLM error."

        self.stage_latencies_sec["synthesis"] = round(time.time() - s4_start, 2)

        # STAGE 5: Claim Verification & Audit
        s5_start = time.time()
        print("\n[STAGE 5/6] Verifying Claims against Evidence...")
        verification_report = self.verifier.verify_answer(report_text, evidence_list)
        print(f"  - Claims Evaluated: {verification_report['total_claims']} | Supported: {verification_report['supported_count']} | Partially Supported: {verification_report['partially_supported_count']} | Unsupported: {verification_report['unsupported_count']} | Score: {verification_report['groundedness_score']}")
        self.stage_latencies_sec["verification"] = round(time.time() - s5_start, 2)

        total_elapsed = round(time.time() - start_time, 2)
        print(f"\n[STAGE 6/6] Workflow Complete in {total_elapsed}s (Total LLM Calls: {self.total_llm_calls}).")

        unique_sources = list({ev["source"] for ev in evidence_list})

        return {
            "topic": topic,
            "execution_time_sec": total_elapsed,
            "is_evidence_sufficient": sufficiency["is_sufficient"],
            "sufficiency_details": sufficiency,
            "plan": plan,
            "sub_questions": sub_questions,
            "evidence": evidence_list,
            "evidence_by_sq": evidence_by_sq,
            "report": report_text,
            "verification_report": verification_report,
            "sources": unique_sources,
            "total_llm_calls": self.total_llm_calls,
            "llm_calls_by_stage": self.llm_calls_by_stage,
            "stage_latencies_sec": self.stage_latencies_sec
        }
