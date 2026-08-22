import os
import io
import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from api.main import app, REPO_ROOT
from core.sources.topic_discovery import TopicDiscoveryEngine
from core.sources.user_source_manager import UserSourceManager
from core.rag.document import Document


class TestTopicDiscoveryAndRelatedPapers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_pdf = os.path.join(REPO_ROOT, "data", "test_fixtures", "research_paper.pdf")
        cls.engine = TopicDiscoveryEngine()

    @classmethod
    def tearDownClass(cls):
        uploads_dir = os.path.join(REPO_ROOT, "data", "uploads")
        fpath = os.path.join(uploads_dir, "topic_test.pdf")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    def test_1_uploaded_pdf_topic_extraction(self):
        profile = self.engine.extract_topic_profile(self.test_pdf)
        self.assertIn("title", profile)
        self.assertIn("abstract", profile)
        self.assertIn("key_terms", profile)
        self.assertIn("search_query", profile)
        self.assertGreater(len(profile["key_terms"]), 0)
        self.assertGreater(len(profile["search_query"]), 0)

    def test_2_related_paper_discovery(self):
        # Mock ArxivSource to return deterministic docs
        mock_arxiv = MagicMock()
        mock_arxiv.fetch.return_value = [
            Document(
                content="Title: Quantum Error Mitigation with Surface Codes\narXiv ID: 2304.00001\n\nAbstract:\nWe study surface code error mitigation.",
                source="arXiv:2304.00001",
                title="Quantum Error Mitigation with Surface Codes",
                published_year=2023
            )
        ]
        engine = TopicDiscoveryEngine(arxiv_source=mock_arxiv)
        discovered = engine.discover_related_papers(self.test_pdf, min_relevance=0.0)
        self.assertGreater(len(discovered), 0)
        self.assertIn("relevance_score", discovered[0])
        self.assertIn("source_url", discovered[0])
        self.assertIn("reason_for_relevance", discovered[0])

    def test_3_relevance_ranking(self):
        mock_arxiv = MagicMock()
        doc_high = Document(
            content="Title: Fisher Information Spectrum in Quantum Neural Networks\narXiv ID: 2304.00002\n\nAbstract:\nFisher information spectrum and capacity analysis.",
            source="arXiv:2304.00002",
            title="Fisher Information Spectrum in Quantum Neural Networks",
            published_year=2023
        )
        doc_low = Document(
            content="Title: General Overview of Machine Learning\narXiv ID: 2304.00003\n\nAbstract:\nA general study.",
            source="arXiv:2304.00003",
            title="General Overview of Machine Learning",
            published_year=2022
        )
        mock_arxiv.fetch.return_value = [doc_low, doc_high]

        engine = TopicDiscoveryEngine(arxiv_source=mock_arxiv)
        discovered = engine.discover_related_papers(self.test_pdf, min_relevance=0.0)
        if len(discovered) >= 2:
            self.assertGreaterEqual(discovered[0]["relevance_score"], discovered[1]["relevance_score"])

    def test_4_no_hardcoded_quantum_for_unrelated_pdfs(self):
        # For a non-quantum profile, ensure quantum terms are not injected
        fake_path = os.path.join(REPO_ROOT, "data", "test_fixtures", "fake_cv_paper.pdf")
        profile = self.engine.extract_topic_profile(fake_path)
        self.assertNotIn("quantum neural network", profile["search_query"].lower())

    def test_5_suggested_questions_based_on_content(self):
        mgr = UserSourceManager(uploads_dir=os.path.join(REPO_ROOT, "data", "test_fixtures"))
        questions = mgr.get_suggested_questions("test_doc")
        self.assertEqual(len(questions), 4)
        for q in questions:
            self.assertTrue(q.endswith("?"))

    def test_6_duplicate_related_paper_removal(self):
        mock_arxiv = MagicMock()
        doc1 = Document(content="Title: Duplicate Paper\narXiv ID: 2304.00010\n\nAbstract:\nTest.", source="arXiv:2304.00010", title="Duplicate Paper", published_year=2023)
        doc2 = Document(content="Title: Duplicate Paper\narXiv ID: 2304.00010\n\nAbstract:\nTest.", source="arXiv:2304.00010", title="Duplicate Paper", published_year=2023)
        mock_arxiv.fetch.return_value = [doc1, doc2]

        engine = TopicDiscoveryEngine(arxiv_source=mock_arxiv)
        discovered = engine.discover_related_papers(self.test_pdf, min_relevance=0.0)
        titles = [d["title"] for d in discovered]
        self.assertEqual(len(titles), len(set(titles)))

    def test_7_valid_metadata_preservation(self):
        profile = self.engine.extract_topic_profile(self.test_pdf)
        self.assertIsInstance(profile["published_year"], int)
        self.assertIsInstance(profile["key_terms"], list)

    def test_8_api_endpoint_related_papers(self):
        # First upload test PDF
        with open(self.test_pdf, "rb") as f:
            pdf_bytes = f.read()

        up_resp = self.client.post(
            "/api/sources/upload",
            files={"file": ("topic_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )
        self.assertEqual(up_resp.status_code, 200)

        sources_resp = self.client.get("/api/sources")
        data = sources_resp.json()
        docs = data.get("documents", [])
        self.assertGreater(len(docs), 0)
        doc_id = docs[0]["id"]

        rel_resp = self.client.get(f"/api/sources/{doc_id}/related-papers")
        self.assertEqual(rel_resp.status_code, 200)
        rel_data = rel_resp.json()
        self.assertIn("document_id", rel_data)
        self.assertIn("related_papers", rel_data)

    def test_9_existing_upload_validation(self):
        bad_resp = self.client.post(
            "/api/sources/upload",
            files={"file": ("bad.txt", io.BytesIO(b"Not a PDF"), "text/plain")}
        )
        self.assertEqual(bad_resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
