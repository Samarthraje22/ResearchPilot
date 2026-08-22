import hashlib
import os
from typing import List, Dict, Set, Tuple
from .document import Document
from .pdf_loader import PDFLoader


class MultiPDFLoader:

    def __init__(self):
        self.single_loader = PDFLoader()
        self.ingested_hashes: Set[str] = set()
        self.ingested_files: Set[str] = set()

    def _compute_file_hash(self, file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def load_pdf(self, file_path: str) -> Tuple[List[Document], bool]:

        if not os.path.exists(file_path):
            print(f"[MultiPDFLoader WARNING] File does not exist: {file_path}")
            return [], False

        try:
            file_hash = self._compute_file_hash(file_path)
        except Exception as e:
            print(f"[MultiPDFLoader ERROR] Unable to compute hash for {file_path}: {e}")
            return [], False

        if file_hash in self.ingested_hashes:
            print(f"[MultiPDFLoader NOTICE] Duplicate file skipped (hash match): {file_path}")
            return [], True  # Was duplicate

        try:
            docs = self.single_loader.load(file_path)
            self.ingested_hashes.add(file_hash)
            self.ingested_files.add(file_path)
            return docs, False
        except Exception as e:
            print(f"[MultiPDFLoader ERROR] Failed to load PDF {file_path}: {e}")
            return [], False

    def load_directory(self, dir_path: str) -> Dict[str, List[Document]]:

        results = {}
        if not os.path.exists(dir_path):
            print(f"[MultiPDFLoader WARNING] Directory does not exist: {dir_path}")
            return results

        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    full_path = os.path.join(root, file)
                    docs, is_dup = self.load_pdf(full_path)
                    if docs:
                        results[full_path] = docs

        return results
