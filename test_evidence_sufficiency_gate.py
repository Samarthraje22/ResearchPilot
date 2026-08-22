import unittest
from core.workflow.engine import ResearchWorkflow


class TestEvidenceSufficiencyGate(unittest.TestCase):

    def setUp(self):
        self.workflow = ResearchWorkflow(sufficiency_threshold=0.35)

    def test_clearly_sufficient_evidence(self):
        topic = "What is the Fisher information spectrum in quantum neural networks?"
        evidence_list = [
            {
                "content": "We analyze the Fisher information spectrum and capacity of quantum neural networks compared to classical models.",
                "score": 0.85
            }
        ]
        result = self.workflow._assess_evidence_sufficiency(topic, evidence_list)
        self.assertTrue(result["is_sufficient"], "Clearly matching evidence must pass the gate!")
        self.assertGreaterEqual(result["coverage_score"], 0.35)

    def test_clearly_insufficient_evidence(self):
        topic = "What is the specific performance impact of 1000-qubit topological braiding on classical image classification?"
        evidence_list = [
            {
                "content": "Quantum neural networks analyze effective dimension and capacity bounds on standard bar-and-stripe datasets.",
                "score": 0.45
            }
        ]
        result = self.workflow._assess_evidence_sufficiency(topic, evidence_list)
        self.assertFalse(result["is_sufficient"], "Missing specific 1000-qubit topological braiding terms must fail the gate!")
        self.assertIn("1000-qubit", result["missing_terms"])

    def test_relevant_evidence_different_terminology(self):
        topic = "Analyze expressibility and trainability bounds in variational quantum algorithms."
        evidence_list = [
            {
                "content": "Parameter efficiency, gradient variance, barren plateaus, and capacity limits in parameterized quantum circuits.",
                "score": 0.90
            }
        ]
        result = self.workflow._assess_evidence_sufficiency(topic, evidence_list)
        # Even if specific wording varies, high relevance/coverage allows sufficient assessment
        self.assertTrue(result["is_sufficient"], "Semantically relevant evidence must be recognized as sufficient!")

    def test_borderline_evidence(self):
        topic = "Surface-code hybrid error correction scalability."
        evidence_list = [
            {
                "content": "Surface-code error mitigation is discussed briefly.",
                "score": 0.30
            }
        ]
        result = self.workflow._assess_evidence_sufficiency(topic, evidence_list)
        self.assertIn("is_sufficient", result)
        self.assertIn("coverage_score", result)


if __name__ == "__main__":
    unittest.main()
