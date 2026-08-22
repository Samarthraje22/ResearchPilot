import os
import io
import unittest
from fastapi.testclient import TestClient
from api.main import app, REPO_ROOT


class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        uploads_dir = os.path.join(REPO_ROOT, "data", "uploads")
        for fname in ["api_test_upload.pdf", "api_test_upload2.pdf"]:
            fpath = os.path.join(uploads_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    def setUp(self):
        self.client = TestClient(app)
        # Ensure a test PDF is uploaded for API query tests
        pdf_path = os.path.join(REPO_ROOT, "data", "test_fixtures", "research_paper.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            up_resp = self.client.post(
                "/api/sources/upload",
                files={"file": ("api_test_upload.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            )
            if up_resp.status_code == 200:
                doc_id = up_resp.json().get("id")
                if doc_id:
                    self.client.post("/api/sources/select", json={"selected_ids": [doc_id]})

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "ResearchPilot API")

    def test_sources_list_and_suggested_questions(self):
        response = self.client.get("/api/sources")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        docs = data.get("documents", [])
        self.assertGreater(len(docs), 0)
        doc_id = docs[0]["id"]

        sugg_resp = self.client.get(f"/api/sources/{doc_id}/suggested-questions")
        self.assertEqual(sugg_resp.status_code, 200)
        sugg_data = sugg_resp.json()
        self.assertIn("suggested_questions", sugg_data)
        self.assertGreater(len(sugg_data["suggested_questions"]), 0)

    def test_valid_research_query(self):
        sources_resp = self.client.get("/api/sources")
        docs = sources_resp.json().get("documents", [])
        doc_id = docs[0]["id"] if docs else None
        if docs:
            self.client.post("/api/sources/select", json={"selected_ids": [d["id"] for d in docs]})

        payload = {
            "query": "What is the Fisher information spectrum in quantum neural networks?",
            "auto_ingest_arxiv": False,
            "sufficiency_threshold": 0.10,
            "selected_document_ids": [doc_id] if doc_id else None
        }
        response = self.client.post("/api/research/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("topic", data)
        self.assertIn("report", data)
        self.assertIn("is_evidence_sufficient", data)
        self.assertIn("verification_report", data)
        self.assertGreater(data["total_llm_calls"], 0)

    def test_invalid_empty_query(self):
        payload = {
            "query": "  ",
            "auto_ingest_arxiv": False
        }
        response = self.client.post("/api/research/query", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Please enter a research question", response.json()["detail"])

    def test_insufficient_evidence_response(self):
        payload = {
            "query": "What is the specific performance impact of 1000-qubit topological braiding on classical image classification?",
            "auto_ingest_arxiv": False,
            "sufficiency_threshold": 0.35
        }
        response = self.client.post("/api/research/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_evidence_sufficient"])
        self.assertIn("[INSUFFICIENT EVIDENCE NOTICE]", data["report"])
        self.assertEqual(data["verification_report"]["unsupported_count"], 0)

    def test_malformed_upload(self):
        fake_file = io.BytesIO(b"This is a text file, not a PDF.")
        response = self.client.post(
            "/api/sources/upload",
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only PDF files (.pdf) are supported", response.json()["detail"])

    def test_valid_pdf_upload(self):
        pdf_path = os.path.join(REPO_ROOT, "data", "test_fixtures", "research_paper.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            response = self.client.post(
                "/api/sources/upload",
                files={"file": ("api_test_upload2.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["filename"], "api_test_upload2.pdf")
            self.assertGreaterEqual(data["chunks_created"], 0)
            self.assertIn("Successfully uploaded", data["message"])

    def test_benchmark_endpoint(self):
        response = self.client.get("/api/eval/benchmark")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("researchpilot_pipeline_aggregates", data)
        self.assertIn("baseline_rag_aggregates", data)


if __name__ == "__main__":
    unittest.main()
