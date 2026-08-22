import os
import re
import time
import hashlib
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from core.utils.cache import suggested_questions_cache, general_cache
from core.llm.router import LLMRouter


class UserSourceManager:
    def __init__(self, uploads_dir: str = "data/uploads"):
        self.uploads_dir = os.path.abspath(uploads_dir)
        os.makedirs(self.uploads_dir, exist_ok=True)
        # Selection state dictionary: { doc_id: bool }
        self.selection_state: Dict[str, bool] = {}

    def get_document_id(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        return hashlib.md5(filename.encode('utf-8')).hexdigest()[:12]

    def list_documents(self) -> List[Dict[str, Any]]:
        docs = []
        if not os.path.exists(self.uploads_dir):
            return docs

        for fname in sorted(os.listdir(self.uploads_dir)):
            if fname.lower().endswith(".pdf"):
                fpath = os.path.join(self.uploads_dir, fname)
                doc_id = self.get_document_id(fpath)
                stat = os.stat(fpath)
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                size_formatted = f"{size_mb} MB" if size_mb >= 0.1 else f"{round(stat.st_size / 1024, 1)} KB"

                # Extract page count
                page_count = 1
                try:
                    reader = PdfReader(fpath)
                    page_count = len(reader.pages)
                except Exception:
                    page_count = 1

                # Default selection to True if new document
                if doc_id not in self.selection_state:
                    self.selection_state[doc_id] = True

                docs.append({
                    "id": doc_id,
                    "filename": fname,
                    "filepath": fpath,
                    "pages": page_count,
                    "size_bytes": stat.st_size,
                    "size_formatted": size_formatted,
                    "upload_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                    "selected": self.selection_state.get(doc_id, True)
                })

        return docs

    def get_selected_filepaths(self) -> List[str]:
        docs = self.list_documents()
        return [d["filepath"] for d in docs if d["selected"]]

    def set_selection(self, selected_ids: List[str]):
        docs = self.list_documents()
        for d in docs:
            doc_id = d["id"]
            self.selection_state[doc_id] = (doc_id in selected_ids)

    def delete_document(self, doc_id: str) -> bool:
        docs = self.list_documents()
        matching_doc = next((d for d in docs if d["id"] == doc_id), None)
        if not matching_doc:
            return False

        fpath = matching_doc["filepath"]
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

        if doc_id in self.selection_state:
            del self.selection_state[doc_id]

        return True

    def reset_all(self):
        """Clear all uploaded user documents and reset selection state"""
        self.selection_state.clear()
        if os.path.exists(self.uploads_dir):
            for fname in os.listdir(self.uploads_dir):
                if fname.lower().endswith(".pdf"):
                    fpath = os.path.join(self.uploads_dir, fname)
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass

    def get_suggested_questions(self, doc_id: str) -> List[str]:
        docs = self.list_documents()
        matching_doc = next((d for d in docs if d["id"] == doc_id), None)
        if not matching_doc:
            return [
                "What problem does this research document address?",
                "What methodology is proposed in this paper?",
                "What are the main findings and experimental results?",
                "What limitations or future work directions are identified?"
            ]

        fpath = matching_doc["filepath"]
        
        # Check cache
        try:
            mtime = os.path.getmtime(fpath)
            cache_key = f"questions:{doc_id}:{mtime}"
            cached_q = suggested_questions_cache.get(cache_key)
            if cached_q:
                return cached_q
        except Exception:
            cache_key = None

        # Extract text from first 3 pages for title/abstract/content analysis
        first_pages_text = ""
        try:
            reader = PdfReader(fpath)
            for i, page in enumerate(reader.pages[:3]):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    first_pages_text += page_text + " "
        except Exception:
            first_pages_text = ""

        if not first_pages_text.strip():
            fallback_res = [
                "What problem does this research document address?",
                "What methodology is proposed in this paper?",
                "What are the main findings and experimental results?",
                "What limitations or future work directions are identified?"
            ]
            if cache_key:
                suggested_questions_cache.set(cache_key, fallback_res)
            return fallback_res

        # Extract actual paper title from PDF metadata or content
        paper_label = self._extract_paper_title(fpath, first_pages_text)

        # Try Smart LLM Question Generation
        llm_questions = self._generate_llm_questions(paper_label, first_pages_text[:2500])
        if llm_questions and len(llm_questions) >= 3:
            if cache_key:
                suggested_questions_cache.set(cache_key, llm_questions)
            return llm_questions

        # Fallback to Heuristic Generation
        text_lower = first_pages_text.lower()
        questions = [
            f"What primary research problem or methodology does '{paper_label}' address?",
            f"What are the key empirical findings and results presented in '{paper_label}'?",
            f"How does the approach in '{paper_label}' compare to existing methods?",
            f"What limitations, assumptions, or future research gaps are identified in '{paper_label}'?"
        ]

        if "algorithm" in text_lower or "architecture" in text_lower:
            questions[0] = f"What specific model architecture or algorithm is proposed in '{paper_label}'?"
        elif "dataset" in text_lower or "evaluation" in text_lower or "benchmark" in text_lower:
            questions[1] = f"What datasets and experimental evaluation metrics are used in '{paper_label}'?"

        if cache_key:
            suggested_questions_cache.set(cache_key, questions)
        return questions

    def _generate_llm_questions(self, paper_title: str, context_snippet: str) -> Optional[List[str]]:
        """Use LLMRouter to generate 4 precise, content-specific research questions."""
        try:
            prompt = (
                f"You are a research assistant. Below is the opening text (abstract and introduction) "
                f"from a scientific research paper titled '{paper_title}'.\n\n"
                f"--- PAPER CONTENT ---\n{context_snippet}\n--- END CONTENT ---\n\n"
                f"Generate exactly 4 insightful, specific research questions that a researcher would ask about this specific paper's "
                f"methodology, findings, models, datasets, or conclusions.\n"
                f"Requirements:\n"
                f"1. Directly reference the specific concepts, methods, or models from the paper.\n"
                f"2. Never use generic filler or file names like '1062' or '.pdf'.\n"
                f"3. Return ONLY a numbered list from 1 to 4 with the question text, no preamble or extra text."
            )
            llm = LLMRouter()
            raw_output = llm.generate(prompt)
            if not raw_output:
                return None

            lines = [l.strip() for l in raw_output.split("\n") if l.strip()]
            questions = []
            for line in lines:
                cleaned = re.sub(r"^\d+[\.\)\-]\s*", "", line).strip()
                cleaned = cleaned.strip("\"'")
                if cleaned.endswith("?") and len(cleaned) >= 15:
                    questions.append(cleaned)
                elif len(cleaned) >= 20 and not cleaned.startswith(("#", "-", "*")):
                    questions.append(cleaned if cleaned.endswith("?") else cleaned + "?")

            if len(questions) >= 3:
                return questions[:4]
            return None
        except Exception as e:
            print(f"[UserSourceManager WARNING] LLM question generation failed: {e}")
            return None



    def _extract_paper_title(self, filepath: str, first_pages_text: str) -> str:
        """Extract the actual paper title from PDF metadata or content, never from the filename."""
        # Try PDF metadata first
        try:
            reader = PdfReader(filepath)
            metadata = reader.metadata
            if metadata:
                title = getattr(metadata, "title", None) or metadata.get("/Title", "")
                if title:
                    title = str(title).strip()
                    # Filter out software template / tool-generated junk titles
                    title_lower = title.lower()
                    is_junk = any(kw in title_lower for kw in [
                        "microsoft word", "untitled", "document1", "unnamed",
                        ".docx", ".doc", ".tex", ".pdf", "latex",
                    ])
                    if not is_junk and 10 <= len(title) <= 300:
                        return title
        except Exception:
            pass

        # Try to extract title from visible text (first non-trivial long line)
        lines = [line.strip() for line in first_pages_text.split("\n") if line.strip()]
        for line in lines[:30]:
            if len(line) < 15 or len(line) > 300:
                continue
            if re.match(r"(?i)^(abstract|keywords?|introduction|citation|doi|received|accepted|published)\b", line):
                continue
            if "@" in line:
                continue
            if re.search(r"(?i)\b(university|department|institute|college|faculty)\b", line):
                continue
            # Skip journal header lines (Vol., ISSN, page numbers)
            if re.search(r"(?i)\b(vol\.\s*\d|issn|journal of)\b", line):
                continue
            # Skip URLs and DOI lines
            if re.match(r"(?i)\s*(https?://|doi\s*:|orcid)", line):
                continue
            # Skip lines that are mostly numbers/dates
            letters = len(re.findall(r"[a-zA-Z]", line))
            if letters < 10:
                continue
            return line[:120]

        # Try extracting from abstract header match
        match = re.search(r'(?i)(?:title|abstract)[:\s]+([^\n]+)', first_pages_text)
        if match and len(match.group(1).strip()) > 10:
            return match.group(1).strip()[:120]

        return "this paper"
