import unittest
from core.rag.document import Document
from core.rag.pipeline import ResearchRAG
from core.verification.claim_verifier import ClaimVerifier
from core.workflow.engine import ResearchWorkflow


class TestAuditFixes(unittest.TestCase):

    def test_disclaimer_and_meta_exclusion(self):
        verifier = ClaimVerifier()
        sample_report = """
# Executive Summary
Quantum neural networks outperform classical networks in capacity metrics [1].

# Potential Research Gaps & Suggested Directions (AI-Suggested Hypotheses)
Note: The potential research gaps and suggested directions are AI-suggested research directions derived from literature limitations, not asserted facts.
Disclaimer: This is not an established scientific finding.

- **Gap Title**: [AI-Suggested Hypothesis] Quantum Error Mitigation
- **Supporting Source(s)**: [1]
- **Supporting Evidence**: Hardware noise causes loss decay degradation.
- **Explanation**: Noise analysis suggests future research directions.

References:
[1] Source: arXiv:2401.12345 (2024), Page 1
"""
        claims = verifier._extract_claims(sample_report)
        
        # Verify that disclaimers, headers, meta notes, and citation listings are excluded
        for claim in claims:
            self.assertFalse(claim.startswith("Note:"), f"Disclaimer note should be excluded: {claim}")
            self.assertFalse(claim.startswith("Disclaimer:"), f"Disclaimer tag should be excluded: {claim}")
            self.assertFalse("AI-suggested research directions" in claim and "asserted facts" in claim, f"Meta disclaimer text should be excluded: {claim}")
            self.assertFalse(claim.startswith("References:"), f"References header should be excluded: {claim}")
            self.assertFalse(claim.startswith("[1] Source:"), f"Citation listing should be excluded: {claim}")

        # Ensure valid substantive claims ARE present
        has_substantive = any("capacity metrics" in c for c in claims)
        self.assertTrue(has_substantive, "Substantive claim should be preserved.")

    def test_citation_deduplication(self):
        rag = ResearchRAG()
        doc1 = Document(content="Chunk A content about quantum capacity.", source="paper1.pdf", page=1, chunk_id="chunk_A_123", published_year=2024)
        doc2 = Document(content="Chunk A content about quantum capacity.", source="paper1.pdf", page=1, chunk_id="chunk_A_123", published_year=2024)
        doc3 = Document(content="Chunk B content about error mitigation.", source="paper2.pdf", page=5, chunk_id="chunk_B_456", published_year=2025)

        retrieved = [(doc1, 0.90), (doc2, 0.88), (doc3, 0.75)]
        context_str, evidence_list = rag._build_context(retrieved)

        # Ensure deduplicated to exactly 2 evidence entries (chunk_A and chunk_B)
        self.assertEqual(len(evidence_list), 2, f"Expected 2 unique evidence entries, got {len(evidence_list)}")
        self.assertEqual(evidence_list[0]["citation_id"], 1)
        self.assertEqual(evidence_list[1]["citation_id"], 2)
        self.assertEqual(evidence_list[0]["chunk_id"], "chunk_A_123")
        self.assertEqual(evidence_list[1]["chunk_id"], "chunk_B_456")

    def test_recency_policy_detection(self):
        workflow = ResearchWorkflow(recent_years_window=3, current_year=2026)
        self.assertEqual(workflow.min_recent_year, 2023)

        doc_old = Document(content="Old 2020 paper", source="old.pdf", page=1, chunk_id="c_old", published_year=2020)
        doc_recent = Document(content="Recent 2024 paper", source="recent.pdf", page=1, chunk_id="c_recent", published_year=2024)

        deduped = [(doc_old, 0.85), (doc_recent, 0.80)]
        recent_chunks = [d for d in deduped if getattr(d[0], 'published_year', None) and d[0].published_year >= workflow.min_recent_year]
        
        self.assertEqual(len(recent_chunks), 1)
        self.assertEqual(recent_chunks[0][0].published_year, 2024)


if __name__ == "__main__":
    unittest.main()
