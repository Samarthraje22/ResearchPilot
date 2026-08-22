import csv
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.rag.pipeline import ResearchRAG
from core.workflow.engine import ResearchWorkflow
from eval.evaluator import BenchmarkEvaluator


def run_benchmark():
    print("\n======================================================================")
    print("       ResearchPilot Phase 5 - Quantitative Evaluation & Benchmark")
    print("======================================================================\n")

    dataset_path = "eval/dataset.json"
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Initialize RAG and Workflow
    rag = ResearchRAG()
    pdf1 = "data/test_fixtures/research_paper.pdf"
    pdf2 = "data/test_fixtures/test_fixture_quantum_error_correction.pdf"
    if os.path.exists(pdf1):
        rag.ingest_pdf(pdf1)
    if os.path.exists(pdf2):
        rag.ingest_pdf(pdf2)

    workflow = ResearchWorkflow(
        rag=rag,
        max_sub_questions=3,
        max_searches_per_sq=2,
        max_docs_per_sq=2,
        max_synthesis_chunks=8,
        recent_years_window=3,
        current_year=2026
    )

    evaluator = BenchmarkEvaluator(rag=rag, workflow=workflow)
    test_cases = dataset["test_cases"]

    baseline_results = []
    pipeline_results = []

    print(f"Loaded {len(test_cases)} curated test cases from {dataset_path}.", flush=True)
    print("Starting evaluation runs...\n", flush=True)

    for tc in test_cases:
        tc_id = tc["id"]
        tc_type = tc["type"]
        print(f"--- Evaluating [{tc_id}] ({tc_type}): '{tc['query'][:55]}...' ---", flush=True)

        # Run Baseline RAG
        print("  Running Baseline RAG...", flush=True)
        b_res = evaluator.evaluate_test_case(tc, system_type="baseline")
        baseline_results.append(b_res)
        print(f"    Baseline -> Latency: {b_res['latency_sec']}s | Groundedness: {b_res['claim_groundedness']} | Precision: {b_res['retrieval_precision']}", flush=True)

        # Run ResearchPilot Pipeline
        print("  Running ResearchPilot Full Pipeline...", flush=True)
        p_res = evaluator.evaluate_test_case(tc, system_type="researchpilot_full")
        pipeline_results.append(p_res)
        print(f"    ResearchPilot -> Latency: {p_res['latency_sec']}s | Groundedness: {p_res['claim_groundedness']} | Precision: {p_res['retrieval_precision']}\n", flush=True)

    # Calculate separate aggregate metrics for Answerable vs Gated cases
    def aggregate_metrics(results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results_list:
            return {}
        
        answerable = [r for r in results_list if not r.get("is_gated", False)]
        gated = [r for r in results_list if r.get("is_gated", False)]
        n_all = float(len(results_list))
        n_ans = float(len(answerable)) if answerable else 0.0
        n_gate = float(len(gated)) if gated else 0.0

        # Answerable Aggregates
        c_acc_list = [r["citation_accuracy"] for r in answerable if r.get("citation_accuracy") is not None]
        ans_agg = {
            "count": len(answerable),
            "mean_latency_sec": round(sum(r["latency_sec"] for r in answerable) / n_ans, 2) if n_ans > 0 else 0.0,
            "mean_total_llm_calls": round(sum(r.get("total_llm_calls", 1) for r in answerable) / n_ans, 2) if n_ans > 0 else 0.0,
            "mean_retrieval_precision": round(sum(r["retrieval_precision"] for r in answerable) / n_ans, 3) if n_ans > 0 else 0.0,
            "mean_retrieval_recall": round(sum(r["retrieval_recall"] for r in answerable) / n_ans, 3) if n_ans > 0 else 0.0,
            "mean_citation_accuracy": round(sum(c_acc_list) / float(len(c_acc_list)), 3) if c_acc_list else 1.0,
            "mean_claim_groundedness": round(sum(r["claim_groundedness"] for r in answerable) / n_ans, 3) if n_ans > 0 else 0.0,
            "mean_unsupported_claim_rate": round(sum(r["unsupported_claim_rate"] for r in answerable) / n_ans, 3) if n_ans > 0 else 0.0,
            "mean_source_diversity": round(sum(r["source_diversity"] for r in answerable) / n_ans, 2) if n_ans > 0 else 0.0,
            "mean_recency_compliance": round(sum(r["recency_compliance"] for r in answerable) / n_ans, 3) if n_ans > 0 else 0.0
        }

        # Gated Aggregates
        gate_agg = {
            "count": len(gated),
            "mean_latency_sec": round(sum(r["latency_sec"] for r in gated) / n_gate, 2) if n_gate > 0 else 0.0,
            "mean_total_llm_calls": round(sum(r.get("total_llm_calls", 1) for r in gated) / n_gate, 2) if n_gate > 0 else 0.0,
            "mean_insufficiency_detection_accuracy": round(sum(r.get("insufficiency_detection_accuracy", 1.0) for r in gated) / n_gate, 3) if n_gate > 0 else 1.0,
            "mean_unsupported_claim_rate": round(sum(r["unsupported_claim_rate"] for r in gated) / n_gate, 3) if n_gate > 0 else 0.0,
            "mean_fabricated_citation_rate": round(sum(r.get("fabricated_citation_rate", 0.0) for r in gated) / n_gate, 3) if n_gate > 0 else 0.0,
            "mean_refusal_notice_correctness": round(sum(r.get("refusal_notice_correctness", 1.0) for r in gated) / n_gate, 3) if n_gate > 0 else 1.0
        }

        # Overall Aggregates
        all_c_acc = [r["citation_accuracy"] for r in results_list if r.get("citation_accuracy") is not None]
        overall_agg = {
            "count": len(results_list),
            "mean_latency_sec": round(sum(r["latency_sec"] for r in results_list) / n_all, 2),
            "mean_total_llm_calls": round(sum(r.get("total_llm_calls", 1) for r in results_list) / n_all, 2),
            "mean_retrieval_precision": round(sum(r["retrieval_precision"] for r in results_list) / n_all, 3),
            "mean_retrieval_recall": round(sum(r["retrieval_recall"] for r in results_list) / n_all, 3),
            "mean_citation_accuracy": round(sum(all_c_acc) / float(len(all_c_acc)), 3) if all_c_acc else 1.0,
            "mean_claim_groundedness": round(sum(r["claim_groundedness"] for r in results_list) / n_all, 3),
            "mean_unsupported_claim_rate": round(sum(r["unsupported_claim_rate"] for r in results_list) / n_all, 3),
            "mean_source_diversity": round(sum(r["source_diversity"] for r in results_list) / n_all, 2),
            "mean_recency_compliance": round(sum(r["recency_compliance"] for r in results_list) / n_all, 3)
        }

        return {
            "answerable_cases": ans_agg,
            "gated_cases": gate_agg,
            "overall": overall_agg
        }

    agg_baseline = aggregate_metrics(baseline_results)
    agg_pipeline = aggregate_metrics(pipeline_results)

    # 1. Export JSON: eval/results.json
    output_json = {
        "metadata": {
            "dataset_version": dataset.get("version", "1.0"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "llm_provider": getattr(rag.llm, "active_provider", "huggingface"),
            "retrieval_top_k": 4,
            "test_cases_count": len(test_cases)
        },
        "baseline_rag_aggregates": agg_baseline,
        "researchpilot_pipeline_aggregates": agg_pipeline,
        "detailed_results": {
            "baseline_rag": baseline_results,
            "researchpilot_pipeline": pipeline_results
        }
    }

    os.makedirs("eval", exist_ok=True)
    with open("eval/results.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2)
    print("Exported JSON results -> eval/results.json")

    # 2. Export CSV: eval/results.csv
    csv_file = "eval/results.csv"
    fieldnames = [
        "test_id", "type", "system", "is_gated", "query", "latency_sec", "total_llm_calls",
        "retrieval_precision", "retrieval_recall", "citation_accuracy",
        "claim_groundedness", "unsupported_claim_rate", "source_diversity",
        "recency_compliance", "total_claims", "supported_claims", "unsupported_claims"
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in baseline_results:
            row = {k: r.get(k, "") for k in fieldnames}
            writer.writerow(row)
        for r in pipeline_results:
            row = {k: r.get(k, "") for k in fieldnames}
            writer.writerow(row)
    print("Exported CSV results -> eval/results.csv")

    # 3. Export Summary: eval/evaluation_summary.md
    bp_ans = agg_pipeline["answerable_cases"]
    bb_ans = agg_baseline["answerable_cases"]
    bp_gate = agg_pipeline["gated_cases"]
    bp_over = agg_pipeline["overall"]
    bb_over = agg_baseline["overall"]

    summary_md = f"""# ResearchPilot Phase 5.3 Quantitative Evaluation Report

**Dataset Version**: {dataset.get("version", "1.0")}  
**Execution Timestamp**: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}  
**LLM Provider**: `{getattr(rag.llm, "active_provider", "huggingface")}`  
**Test Suite**: 6 Curated Ground-Truth Research Cases (4 Answerable, 2 Gated)  

---

## 1. Answerable Cases Evaluation Metrics (4 Cases)

| Metric | Baseline RAG | ResearchPilot Full Pipeline | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Retrieval Precision** | `{bb_ans.get("mean_retrieval_precision", 0.0):.3f}` | `{bp_ans.get("mean_retrieval_precision", 0.0):.3f}` | `+{(bp_ans.get("mean_retrieval_precision", 0.0) - bb_ans.get("mean_retrieval_precision", 0.0)):.3f}` |
| **Retrieval Recall** | `{bb_ans.get("mean_retrieval_recall", 0.0):.3f}` | `{bp_ans.get("mean_retrieval_recall", 0.0):.3f}` | `+{(bp_ans.get("mean_retrieval_recall", 0.0) - bb_ans.get("mean_retrieval_recall", 0.0)):.3f}` |
| **Citation Accuracy (Answerable)** | `{bb_ans.get("mean_citation_accuracy", 0.0):.3f}` | `{bp_ans.get("mean_citation_accuracy", 0.0):.3f}` | `+{(bp_ans.get("mean_citation_accuracy", 0.0) - bb_ans.get("mean_citation_accuracy", 0.0)):.3f}` |
| **Claim Groundedness** | `{bb_ans.get("mean_claim_groundedness", 0.0):.3f}` | `{bp_ans.get("mean_claim_groundedness", 0.0):.3f}` | `+{(bp_ans.get("mean_claim_groundedness", 0.0) - bb_ans.get("mean_claim_groundedness", 0.0)):.3f}` |
| **Unsupported Claim Rate** | `{bb_ans.get("mean_unsupported_claim_rate", 0.0):.3f}` | `{bp_ans.get("mean_unsupported_claim_rate", 0.0):.3f}` | `{(bp_ans.get("mean_unsupported_claim_rate", 0.0) - bb_ans.get("mean_unsupported_claim_rate", 0.0)):.3f}` |
| **Relevant Source Diversity** | `{bb_ans.get("mean_source_diversity", 0.0):.2f}` | `{bp_ans.get("mean_source_diversity", 0.0):.2f}` | `+{(bp_ans.get("mean_source_diversity", 0.0) - bb_ans.get("mean_source_diversity", 0.0)):.2f}` |
| **Recency Compliance** | `{bb_ans.get("mean_recency_compliance", 0.0):.3f}` | `{bp_ans.get("mean_recency_compliance", 0.0):.3f}` | `+{(bp_ans.get("mean_recency_compliance", 0.0) - bb_ans.get("mean_recency_compliance", 0.0)):.3f}` |
| **Mean Latency (Seconds)** | `{bb_ans.get("mean_latency_sec", 0.0):.2f}s` | `{bp_ans.get("mean_latency_sec", 0.0):.2f}s` | `+{(bp_ans.get("mean_latency_sec", 0.0) - bb_ans.get("mean_latency_sec", 0.0)):.2f}s` |
| **Mean Total LLM Calls** | `{bb_ans.get("mean_total_llm_calls", 0.0):.1f}` | `{bp_ans.get("mean_total_llm_calls", 0.0):.1f}` | `+{(bp_ans.get("mean_total_llm_calls", 0.0) - bb_ans.get("mean_total_llm_calls", 0.0)):.1f}` |

---

## 2. Insufficient-Evidence (Gated) Cases Evaluation Metrics (2 Cases)

| Metric | ResearchPilot Gated Performance | Expected Optimal Target |
| :--- | :---: | :---: |
| **Insufficiency Detection Accuracy** | `{bp_gate.get("mean_insufficiency_detection_accuracy", 1.0):.3f}` | `1.000 (100%)` |
| **Unsupported Claim Rate (Gated)** | `{bp_gate.get("mean_unsupported_claim_rate", 0.0):.3f}` | `0.000 (0%)` |
| **Fabricated Citation Rate** | `{bp_gate.get("mean_fabricated_citation_rate", 0.0):.3f}` | `0.000 (0%)` |
| **Refusal Notice Correctness** | `{bp_gate.get("mean_refusal_notice_correctness", 1.0):.3f}` | `1.000 (100%)` |
| **Gated Case Mean Latency** | `{bp_gate.get("mean_latency_sec", 0.0):.2f}s` | `< 25.0s` |
| **Gated Case Mean LLM Calls** | `{bp_gate.get("mean_total_llm_calls", 1.0):.1f}` | `1.0 Call (Synthesis Skipped)` |

---

## 3. Overall System Summary (All 6 Cases Combined)

| Metric | Baseline RAG | ResearchPilot Full Pipeline | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Overall Citation Accuracy** | `{bb_over.get("mean_citation_accuracy", 0.0):.3f}` | `{bp_over.get("mean_citation_accuracy", 0.0):.3f}` | `+{(bp_over.get("mean_citation_accuracy", 0.0) - bb_over.get("mean_citation_accuracy", 0.0)):.3f}` |
| **Overall Claim Groundedness** | `{bb_over.get("mean_claim_groundedness", 0.0):.3f}` | `{bp_over.get("mean_claim_groundedness", 0.0):.3f}` | `+{(bp_over.get("mean_claim_groundedness", 0.0) - bb_over.get("mean_claim_groundedness", 0.0)):.3f}` |
| **Overall Unsupported Claim Rate** | `{bb_over.get("mean_unsupported_claim_rate", 0.0):.3f}` | `{bp_over.get("mean_unsupported_claim_rate", 0.0):.3f}` | `{(bp_over.get("mean_unsupported_claim_rate", 0.0) - bb_over.get("mean_unsupported_claim_rate", 0.0)):.3f}` |
| **Overall Mean Latency** | `{bb_over.get("mean_latency_sec", 0.0):.2f}s` | `{bp_over.get("mean_latency_sec", 0.0):.2f}s` | `+{(bp_over.get("mean_latency_sec", 0.0) - bb_over.get("mean_latency_sec", 0.0)):.2f}s` |
| **Overall Mean Total LLM Calls** | `{bb_over.get("mean_total_llm_calls", 0.0):.1f}` | `{bp_over.get("mean_total_llm_calls", 0.0):.1f}` | `+{(bp_over.get("mean_total_llm_calls", 0.0) - bb_over.get("mean_total_llm_calls", 0.0)):.1f}` |

---

## 4. Per-Test-Case Detailed Breakdown

"""
    for tc, b_res, p_res in zip(test_cases, baseline_results, pipeline_results):
        gated_tag = " [GATED]" if p_res.get("is_gated") else " [ANSWERABLE]"
        summary_md += f"""### [{tc['id']}]{gated_tag} {tc['query']}
- **Type**: `{tc['type']}` | **Is Gated**: `{p_res.get('is_gated')}`
- **Baseline RAG**: Precision={b_res['retrieval_precision']}, Groundedness={b_res['claim_groundedness']}, Latency={b_res['latency_sec']}s, LLM Calls={b_res.get('total_llm_calls', 1)}
- **ResearchPilot**: Precision={p_res['retrieval_precision']}, Groundedness={p_res['claim_groundedness']}, Latency={p_res['latency_sec']}s, Sources={p_res['source_diversity']}, LLM Calls={p_res.get('total_llm_calls', 2)}

"""

    with open("eval/evaluation_summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)
    print("Exported Summary Report -> eval/evaluation_summary.md")
    print("\n[SUCCESS] Benchmark evaluation complete!")



if __name__ == "__main__":
    run_benchmark()
