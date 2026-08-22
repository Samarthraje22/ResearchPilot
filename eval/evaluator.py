import os
import sys
import time
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.rag.pipeline import ResearchRAG
from core.workflow.engine import ResearchWorkflow
from core.verification.claim_verifier import ClaimVerifier


class BenchmarkEvaluator:

    def __init__(self, rag: ResearchRAG, workflow: ResearchWorkflow):
        self.rag = rag
        self.workflow = workflow
        self.verifier = ClaimVerifier()

    def run_baseline_rag(self, query: str, top_k: int = 4) -> Dict[str, Any]:
        """
        Baseline RAG: Simple fixed system
        - FAISS vector store top-k retrieval
        - Single LLM generation prompt
        - No research planning, no multi-source REST discovery, no claim verification
        """
        start_time = time.time()
        retrieved = self.rag.retriever.retrieve(query, top_k=top_k, filter_references=True) if self.rag.retriever else []
        context_str, evidence_list = self.rag._build_context(retrieved)

        baseline_prompt = (
            "Answer the question based strictly on the provided context passages. "
            "Use inline citations [1], [2] to cite your sources.\n\n"
            f"Context Passages:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )

        try:
            raw_answer = self.rag.llm.generate(baseline_prompt)
        except Exception as e:
            raw_answer = f"Baseline generation error: {e}"

        elapsed = round(time.time() - start_time, 2)
        verification_report = self.verifier.verify_answer(raw_answer, evidence_list)

        return {
            "query": query,
            "latency_sec": elapsed,
            "answer": raw_answer,
            "evidence": evidence_list,
            "retrieved_chunks": [doc for doc, score in retrieved],
            "verification_report": verification_report,
            "llm_provider": getattr(self.rag.llm, "active_provider", "huggingface"),
            "sources": list({e["source"] for e in evidence_list})
        }

    def run_researchpilot_pipeline(self, query: str) -> Dict[str, Any]:
        """
        ResearchPilot Full Pipeline:
        - Research planning (sub-question decomposition)
        - Multi-source discovery (arXiv REST API + PDF vector store)
        - Traceable evidence retrieval per sub-question & deduplication
        - Evidence sufficiency gate & bounded recency policy
        - Grounded report synthesis & claim verification audit logging
        """
        res = self.workflow.run(query, auto_ingest_arxiv=True)
        return {
            "query": query,
            "latency_sec": res["execution_time_sec"],
            "answer": res["report"],
            "evidence": res["evidence"],
            "plan": res["plan"],
            "verification_report": res["verification_report"],
            "llm_provider": getattr(self.rag.llm, "active_provider", "huggingface"),
            "sources": res["sources"],
            "is_evidence_sufficient": res.get("is_evidence_sufficient", True),
            "total_llm_calls": res.get("total_llm_calls", 2),
            "llm_calls_by_stage": res.get("llm_calls_by_stage", {}),
            "stage_latencies_sec": res.get("stage_latencies_sec", {})
        }

    def evaluate_test_case(self, test_case: Dict[str, Any], system_type: str = "baseline") -> Dict[str, Any]:
        query = test_case["query"]
        if system_type == "baseline":
            output = self.run_baseline_rag(query)
        else:
            output = self.run_researchpilot_pipeline(query)

        evidence_list = output.get("evidence", [])
        answer_text = output.get("answer", "")
        ver = output.get("verification_report", {})

        # 1. Retrieval Precision & Recall against Curated Ground Truth Metadata
        expected_sources = test_case.get("expected_sources", [])
        expected_keywords = [kw.lower() for kw in test_case.get("expected_keywords", [])]
        is_negative = test_case.get("is_negative_case", False)

        retrieved_count = len(evidence_list)
        relevant_chunks_count = 0
        retrieved_sources_set = set()

        for ev in evidence_list:
            ev_source = ev.get("source", "")
            retrieved_sources_set.add(ev_source)
            content_lower = ev.get("content", "").lower()

            # A chunk is relevant if it matches expected sources or expected keywords
            matches_src = any(es.lower() in ev_source.lower() or ev_source.lower() in es.lower() for es in expected_sources)
            matches_kw = any(kw in content_lower for kw in expected_keywords) if expected_keywords else False

            if matches_src or matches_kw:
                relevant_chunks_count += 1

        # Determine if test case is a Gated Case or Answerable Case
        requires_recency = test_case.get("requires_recency", False)
        pub_window = test_case.get("publication_window", [2023, 2026])
        recent_sources_found = any(ev.get("published_year") and pub_window[0] <= ev["published_year"] <= pub_window[1] for ev in evidence_list)

        is_gated = is_negative or (requires_recency and not recent_sources_found and not output.get("is_evidence_sufficient", True))

        if is_negative:
            precision = 1.0 if ("unsupported" in answer_text.lower() or ver.get("unsupported_count", 0) > 0 or not evidence_list or not output.get("is_evidence_sufficient", True)) else 0.0
            recall = 1.0
        else:
            precision = round(relevant_chunks_count / float(retrieved_count), 3) if retrieved_count > 0 else 0.0
            matched_expected_sources = sum(1 for es in expected_sources if any(es.lower() in rs.lower() or rs.lower() in es.lower() for rs in retrieved_sources_set))
            recall = round(matched_expected_sources / float(len(expected_sources)), 3) if expected_sources else 1.0

        # Citations & Groundedness
        citations = set([int(c) for c in set(__import__("re").findall(r'\[(\d+)\]', answer_text))])
        valid_citation_ids = set([ev["citation_id"] for ev in evidence_list])

        if citations:
            accurate_citations = sum(1 for c in citations if c in valid_citation_ids)
            citation_accuracy = round(accurate_citations / float(len(citations)), 3)
            fabricated_citation_rate = round(sum(1 for c in citations if c not in valid_citation_ids) / float(len(citations)), 3)
        else:
            citation_accuracy = 1.0 if (not evidence_list and not is_gated) else (None if is_gated else 1.0)
            fabricated_citation_rate = 0.0

        groundedness = ver.get("groundedness_score", 1.0)
        total_claims = ver.get("total_claims", 0)
        unsupported_cnt = ver.get("unsupported_count", 0)
        unsupported_rate = round(unsupported_cnt / float(total_claims), 3) if total_claims > 0 else 0.0

        unique_sources_count = len(output.get("sources", []))

        # Recency Compliance & Insufficiency Notice Detection
        has_recency_notice = "[recency notice]" in answer_text.lower()
        has_insufficient_notice = "[insufficient evidence notice]" in answer_text.lower() or not output.get("is_evidence_sufficient", True)

        if requires_recency:
            recency_compliance = 1.0 if (recent_sources_found or has_recency_notice or has_insufficient_notice) else 0.0
        else:
            recency_compliance = 1.0

        insufficiency_detection_accuracy = 1.0 if (is_gated and (has_insufficient_notice or has_recency_notice)) else (1.0 if not is_gated else 0.0)
        refusal_notice_correctness = 1.0 if (has_insufficient_notice or has_recency_notice) else (1.0 if not is_gated else 0.0)

        return {
            "test_id": test_case["id"],
            "type": test_case["type"],
            "system": system_type,
            "is_gated": is_gated,
            "query": query,
            "latency_sec": output["latency_sec"],
            "retrieval_precision": precision,
            "retrieval_recall": recall,
            "citation_accuracy": citation_accuracy,
            "claim_groundedness": groundedness,
            "unsupported_claim_rate": unsupported_rate,
            "source_diversity": unique_sources_count,
            "recency_compliance": recency_compliance,
            "total_claims": total_claims,
            "supported_claims": ver.get("supported_count", 0),
            "unsupported_claims": unsupported_cnt,
            "llm_provider": output["llm_provider"],
            "total_llm_calls": output.get("total_llm_calls", 1 if system_type == "baseline" else 2),
            "is_evidence_sufficient": output.get("is_evidence_sufficient", True),
            "insufficiency_detection_accuracy": insufficiency_detection_accuracy,
            "fabricated_citation_rate": fabricated_citation_rate,
            "refusal_notice_correctness": refusal_notice_correctness
        }
