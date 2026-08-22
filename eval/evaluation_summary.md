# ResearchPilot Phase 5.3 Quantitative Evaluation Report

**Dataset Version**: 1.0  
**Execution Timestamp**: 2026-08-16 16:16:53 UTC  
**LLM Provider**: `huggingface`  
**Test Suite**: 6 Curated Ground-Truth Research Cases (4 Answerable, 2 Gated)  

---

## 1. Answerable Cases Evaluation Metrics (4 Cases)

| Metric | Baseline RAG | ResearchPilot Full Pipeline | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Retrieval Precision** | `1.000` | `0.950` | `+-0.050` |
| **Retrieval Recall** | `0.600` | `0.750` | `+0.150` |
| **Citation Accuracy (Answerable)** | `1.000` | `0.938` | `+-0.062` |
| **Claim Groundedness** | `0.877` | `0.887` | `+0.010` |
| **Unsupported Claim Rate** | `0.050` | `0.029` | `-0.021` |
| **Relevant Source Diversity** | `1.40` | `1.50` | `+0.10` |
| **Recency Compliance** | `0.800` | `1.000` | `+0.200` |
| **Mean Latency (Seconds)** | `6.64s` | `43.65s` | `+37.01s` |
| **Mean Total LLM Calls** | `1.0` | `2.0` | `+1.0` |

---

## 2. Insufficient-Evidence (Gated) Cases Evaluation Metrics (2 Cases)

| Metric | ResearchPilot Gated Performance | Expected Optimal Target |
| :--- | :---: | :---: |
| **Insufficiency Detection Accuracy** | `1.000` | `1.000 (100%)` |
| **Unsupported Claim Rate (Gated)** | `0.000` | `0.000 (0%)` |
| **Fabricated Citation Rate** | `0.000` | `0.000 (0%)` |
| **Refusal Notice Correctness** | `1.000` | `1.000 (100%)` |
| **Gated Case Mean Latency** | `19.64s` | `< 25.0s` |
| **Gated Case Mean LLM Calls** | `1.0` | `1.0 Call (Synthesis Skipped)` |

---

## 3. Overall System Summary (All 6 Cases Combined)

| Metric | Baseline RAG | ResearchPilot Full Pipeline | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Overall Citation Accuracy** | `1.000` | `0.938` | `+-0.062` |
| **Overall Claim Groundedness** | `0.780` | `0.924` | `+0.144` |
| **Overall Unsupported Claim Rate** | `0.142` | `0.020` | `-0.122` |
| **Overall Mean Latency** | `6.31s` | `35.65s` | `+29.34s` |
| **Overall Mean Total LLM Calls** | `1.0` | `1.7` | `+0.7` |

---

## 4. Per-Test-Case Detailed Breakdown

### [TC1] [ANSWERABLE] What is the Fisher information spectrum in quantum neural networks?
- **Type**: `factual` | **Is Gated**: `False`
- **Baseline RAG**: Precision=1.0, Groundedness=1.0, Latency=3.26s, LLM Calls=1
- **ResearchPilot**: Precision=1.0, Groundedness=0.929, Latency=40.76s, Sources=1, LLM Calls=2

### [TC2] [ANSWERABLE] How does quantum neural network capacity compare to classical neural network capacity?
- **Type**: `conceptual` | **Is Gated**: `False`
- **Baseline RAG**: Precision=1.0, Groundedness=1.0, Latency=2.3s, LLM Calls=1
- **ResearchPilot**: Precision=0.8, Groundedness=0.875, Latency=39.9s, Sources=2, LLM Calls=2

### [TC3] [ANSWERABLE] Compare quantum neural network capacity analysis with surface-code hybrid quantum error correction techniques.
- **Type**: `comparative` | **Is Gated**: `False`
- **Baseline RAG**: Precision=1.0, Groundedness=0.75, Latency=6.64s, LLM Calls=1
- **ResearchPilot**: Precision=1.0, Groundedness=0.978, Latency=44.25s, Sources=2, LLM Calls=2

### [TC4] [GATED] Analyze recent 2024-2026 approaches to quantum neural networks and identify research gaps.
- **Type**: `recency` | **Is Gated**: `True`
- **Baseline RAG**: Precision=1.0, Groundedness=0.8, Latency=10.95s, LLM Calls=1
- **ResearchPilot**: Precision=1.0, Groundedness=1.0, Latency=20.43s, Sources=2, LLM Calls=1

### [TC5] [ANSWERABLE] What are the theoretical foundations of quantum neural networks across academic literature?
- **Type**: `multi_source` | **Is Gated**: `False`
- **Baseline RAG**: Precision=1.0, Groundedness=0.833, Latency=10.07s, LLM Calls=1
- **ResearchPilot**: Precision=1.0, Groundedness=0.765, Latency=49.7s, Sources=1, LLM Calls=2

### [TC6] [GATED] What is the specific performance impact of 1000-qubit topological braiding on classical image classification in research_paper.pdf?
- **Type**: `negative_insufficient_evidence` | **Is Gated**: `True`
- **Baseline RAG**: Precision=1.0, Groundedness=0.3, Latency=4.64s, LLM Calls=1
- **ResearchPilot**: Precision=1.0, Groundedness=1.0, Latency=18.86s, Sources=1, LLM Calls=1

