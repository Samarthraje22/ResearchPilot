import re
import urllib.request
import urllib.parse
from typing import List
from .base_source import BaseSource
from core.rag.document import Document


class WebSource(BaseSource):

    def _clean_html(self, html: str) -> tuple[str, str]:
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Web Page"

        # Remove script and style tags
        cleaned = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', cleaned)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return title, text

    def fetch(self, url: str, max_results: int = 1) -> List[Document]:
        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            print(f"[WebSource WARNING] Invalid URL: {url}")
            return []

        try:
            req = urllib.request.Request(
                clean_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ResearchPilot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html_bytes = response.read()

            html_text = html_bytes.decode('utf-8', errors='ignore')
            title, clean_text = self._clean_html(html_text)

            if not clean_text or len(clean_text) < 50:
                return []

            doc = Document(
                content=clean_text[:4000],  # cap long web page previews
                source=clean_url,
                title=title,
                page=1,
                section="Web Content",
                is_reference=False
            )
            return [doc]

        except Exception as e:
            print(f"[WebSource ERROR] Failed to fetch web page '{url}': {e}")
            return []
