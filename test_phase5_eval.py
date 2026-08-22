import json
import unittest
from core.rag.document import Document
from core.rag.pipeline import ResearchRAG
from core.workflow.engine import ResearchWorkflow
from eval.evaluator import BenchmarkEvaluator


class TestPhase5Evaluation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rag = ResearchRAG()
        doc = Document(content="Fisher information spectrum in quantum neural networks shows barren plateaus.", source="data/test_fixtures/research_paper.pdf", page=7, published_year=2020)
        cls.rag._index_documents([doc], source_key="test_paper")
        cls.workflow = ResearchWorkflow(rag=cls.rag)
        cls.evaluator = BenchmarkEvaluator(rag=cls.rag, workflow=cls.workflow)

    def test_dataset_json_structure(self):
        with open("eval/dataset.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("version", data)
        self.assertIn("test_cases", data)
        self.assertGreaterEqual(len(data["test_cases"]), 5)

        for tc in data["test_cases"]:
            self.assertIn("id", tc)
            self.assertIn("query", tc)
            self.assertIn("type", tc)
            self.assertIn("expected_sources", tc)
            self.assertIn("requires_recency", tc)
            self.assertIn("requires_multi_source", tc)

    def test_baseline_rag_evaluation(self):
        tc = {
            "id": "TC1_test",
            "type": "factual",
            "query": "What is the Fisher information spectrum?",
            "expected_sources": ["data/test_fixtures/research_paper.pdf"],
            "expected_keywords": ["Fisher", "spectrum"],
            "requires_recency": False,
            "requires_multi_source": False,
            "is_negative_case": False
        }

        res = self.evaluator.evaluate_test_case(tc, system_type="baseline")
        self.assertEqual(res["system"], "baseline")
        self.assertIn("retrieval_precision", res)
        self.assertIn("claim_groundedness", res)
        self.assertGreaterEqual(res["retrieval_precision"], 0.0)
        self.assertGreaterEqual(res["claim_groundedness"], 0.0)

    def test_negative_case_evaluation(self):
        neg_tc = {
            "id": "TC_NEG",
            "type": "negative_insufficient_evidence",
            "query": "What is the specific performance impact of 1000-qubit topological braiding?",
            "expected_sources": [],
            "expected_keywords": [],
            "requires_recency": False,
            "requires_multi_source": False,
            "is_negative_case": True,
            "expected_claim_status": "Unsupported ❌"
        }

        res = self.evaluator.evaluate_test_case(neg_tc, system_type="baseline")
        self.assertIn("retrieval_precision", res)
        self.assertIn("unsupported_claim_rate", res)


if __name__ == "__main__":
    unittest.main()
