import re
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import List
from .base_source import BaseSource
from core.rag.document import Document


class ArxivSource(BaseSource):

    RECENCY_KEYWORDS = ["recent", "latest", "current", "state of the art", "sota", "2024", "2025", "2026"]

    def __init__(self):
        self.stats = {
            "total_searches": 0,
            "retries": 0,
            "timeouts": 0,
            "successes": 0,
            "failures": 0,
            "total_latency_sec": 0.0
        }

    def _execute_http_request(self, api_url: str, max_retries: int = 2) -> bytes:
        for attempt in range(max_retries + 1):
            start_t = time.time()
            try:
                req = urllib.request.Request(
                    api_url,
                    headers={"User-Agent": "ResearchPilot/1.0"}
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    xml_bytes = response.read()
                    self.stats["total_latency_sec"] += round(time.time() - start_t, 2)
                    return xml_bytes
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                self.stats["total_latency_sec"] += round(time.time() - start_t, 2)
                is_429 = isinstance(e, urllib.error.HTTPError) and e.code == 429
                is_timeout = isinstance(e, (TimeoutError, urllib.error.URLError)) and "timed out" in str(e).lower()

                if is_timeout:
                    self.stats["timeouts"] += 1

                if (is_429 or is_timeout) and attempt < max_retries:
                    self.stats["retries"] += 1
                    retry_after = 1.0
                    if is_429 and hasattr(e, 'headers') and e.headers and 'Retry-After' in e.headers:
                        try:
                            retry_after = float(e.headers['Retry-After'])
                        except ValueError:
                            retry_after = 1.0 * (attempt + 1)
                    else:
                        retry_after = 1.0 * (attempt + 1)

                    print(f"  - [ArxivSource RETRY] Transient error ({e}). Retrying in {retry_after}s (Attempt {attempt+1}/{max_retries})...", flush=True)
                    time.sleep(retry_after)
                else:
                    raise e
        raise TimeoutError("ArXiv request failed after retries")

    def fetch(self, query_or_id: str, max_results: int = 3) -> List[Document]:
        clean_q = query_or_id.strip()
        if not clean_q:
            return []

        self.stats["total_searches"] += 1
        q_lower = clean_q.lower()
        is_recency = any(kw in q_lower for kw in self.RECENCY_KEYWORDS)

        clean_id = clean_q.replace("arXiv:", "").strip()
        if clean_id.replace(".", "").replace("v", "").isdigit() or "abs/" in clean_q:
            api_url = f"http://export.arxiv.org/api/query?id_list={clean_id}&start=0&max_results=1"
        else:
            # Clean query terms for optimal REST search
            terms = [w for w in re.findall(r'\b[a-zA-Z0-9\-]+\b', clean_q) if len(w) >= 3 and not w.endswith('.pdf')][:5]
            search_str = " ".join(terms) if terms else clean_q
            encoded_q = urllib.parse.quote(search_str)

            if is_recency:
                api_url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_q}&sortBy=submittedDate&sortOrder=descending&start=0&max_results={max_results}"
            else:
                api_url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_q}&start=0&max_results={max_results}"

        try:
            xml_data = self._execute_http_request(api_url)
            root = ET.fromstring(xml_data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            documents = []

            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                id_elem = entry.find('atom:id', ns)
                published_elem = entry.find('atom:published', ns)

                if title_elem is None or summary_elem is None:
                    continue

                title = title_elem.text.strip().replace("\n", " ")
                summary = summary_elem.text.strip().replace("\n", " ")
                raw_id = id_elem.text.strip() if id_elem is not None else "arXiv"
                arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

                pub_year = None
                if published_elem is not None and published_elem.text:
                    year_match = re.search(r'(\d{4})', published_elem.text)
                    if year_match:
                        pub_year = int(year_match.group(1))

                year_str = f" ({pub_year})" if pub_year else ""
                content = f"Title: {title}\narXiv ID: {arxiv_id}{year_str}\n\nAbstract:\n{summary}"

                doc = Document(
                    content=content,
                    source=f"arXiv:{arxiv_id}",
                    title=title,
                    page=1,
                    section="Abstract",
                    is_reference=False,
                    published_year=pub_year
                )
                documents.append(doc)

            self.stats["successes"] += 1
            return documents

        except Exception as e:
            self.stats["failures"] += 1
            print(f"[ArxivSource ERROR] Failed to query arXiv for '{query_or_id}': {e}")
            return []

