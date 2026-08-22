import unittest
from core.verification.claim_verifier import ClaimVerifier


class TestClaimVerifier(unittest.TestCase):

    def setUp(self):
        self.verifier = ClaimVerifier()

    def test_citation_masking_regression(self):
        """Verify that a claim containing [1] is NOT marked supported merely because [1] exists."""
        sample_answer = "This is an unsupported claim about 1000-qubit topological braiding [1]."
        sample_evidence = [
            {
                "citation_id": 1,
                "source": "data/test_fixtures/research_paper.pdf",
                "page": 1,
                "section": "Introduction",
                "content": "Quantum neural networks use variational quantum circuits for classification tasks."
            }
        ]

        report = self.verifier.verify_answer(sample_answer, sample_evidence)
        self.assertEqual(report['total_claims'], 1)
        self.assertEqual(report['unsupported_count'], 1, "Claim with [1] but low text overlap must NOT be marked supported!")
        self.assertNotEqual(report['claims'][0]['status'], "Supported ✅")

    def test_claim_verifier_extraction_and_scoring(self):
        sample_answer = (
            "The authors investigate the effective dimension of quantum neural networks [1]. "
            "They find that quantum neural networks achieve higher capacity than classical models [1]. "
            "The paper was published in the year 1850 on Mars by alien scientists."
        )
        sample_evidence = [
            {
                "citation_id": 1,
                "source": "data/test_fixtures/research_paper.pdf",
                "page": 1,
                "section": "1 Introduction",
                "content": "We investigate the effective dimension and capacity of quantum neural networks compared to classical models."
            }
        ]

        report = self.verifier.verify_answer(sample_answer, sample_evidence)
        self.assertGreaterEqual(report['total_claims'], 3)
        self.assertGreaterEqual(report['supported_count'], 2)
        self.assertGreaterEqual(report['unsupported_count'], 1)


if __name__ == "__main__":
    unittest.main()
