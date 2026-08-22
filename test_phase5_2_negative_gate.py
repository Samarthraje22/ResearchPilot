import unittest
from core.workflow.engine import ResearchWorkflow


class TestPhase52NegativeGate(unittest.TestCase):

    def test_tc6_insufficient_evidence_gate(self):
        topic = "What is the specific performance impact of 1000-qubit topological braiding on classical image classification in research_paper.pdf?"
        workflow = ResearchWorkflow(sufficiency_threshold=0.35)

        # Run workflow with auto_ingest_arxiv=False so it searches only local research_paper.pdf corpus
        res = workflow.run(topic, auto_ingest_arxiv=False)

        # 1. Gate must flag evidence as insufficient
        self.assertFalse(res["is_evidence_sufficient"], "TC6 query must trigger evidence sufficiency gate (is_evidence_sufficient=False)")

        # 2. Report must explicitly contain insufficient evidence notice
        self.assertIn("[INSUFFICIENT EVIDENCE NOTICE]", res["report"], "Report must explicitly declare insufficient evidence notice!")

        # 3. Report must identify missing information
        self.assertIn("1000-qubit", res["report"], "Report must explicitly list missing requested term '1000-qubit'")

        # 4. Total LLM calls should be 1 (planning only, synthesis skipped!)
        self.assertEqual(res["total_llm_calls"], 1, "Synthesis LLM call must be skipped when evidence is insufficient!")

        # 5. Verification must confirm 0 unsupported factual claims
        ver = res["verification_report"]
        self.assertEqual(ver["unsupported_count"], 0, "Zero unsupported factual claims allowed in negative response!")


if __name__ == "__main__":
    unittest.main()
