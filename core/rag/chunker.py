import hashlib
import re
from typing import Optional, List
from .document import Document

REFERENCE_KEYWORDS = {
    "references", "reference", "bibliography", "works cited",
    "literature cited", "appendix", "appendices"
}

MAIN_SECTION_KEYWORDS = {
    "abstract", "introduction", "background", "related work",
    "literature review", "method", "methods", "methodology",
    "proposed method", "model", "architecture", "experimental setup",
    "experiments", "results", "evaluation", "discussion",
    "conclusion", "conclusions", "future work", "acknowledgements",
    "acknowledgments"
}


class TextChunker:

    def __init__(self, chunk_size: int = 700, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._current_section: Optional[str] = None
        self._is_reference_section: bool = False

    def reset_state(self):
        """Reset state when starting a new document stream if needed."""
        self._current_section = None
        self._is_reference_section = False

    def _detect_section_header(self, line: str) -> Optional[tuple[str, bool]]:
        clean_line = line.strip()
        if not clean_line or len(clean_line) > 65:
            return None

        if clean_line.endswith('.') and not re.match(r'^\d+\.$', clean_line):
            return None
        if clean_line.endswith(',') or clean_line.endswith(';'):
            return None

        # 1. Numbered section header pattern: '1 Introduction', '3.1 The Fisher information', 'B.1 Proof'
        m_num = re.match(r'^\s*([0-9]+(?:\.[0-9]+)*|[A-Z]\.|[I|V|X]+\.|\bSection\s+\d+)\s+([A-Z].*)', clean_line)
        if m_num:
            num_part = m_num.group(1)
            title_part = m_num.group(2)
            # Exclude footnote numbers (single integer > 15 without dot)
            if num_part.isdigit() and int(num_part) > 15:
                return None
            is_ref = any(rk in title_part.lower() for rk in REFERENCE_KEYWORDS) or ('appendix' in num_part.lower())
            return (clean_line, is_ref)

        # 2. Keyword section header pattern: 'Abstract', 'References'
        m_kw = re.match(
            r'^\s*(Abstract|Introduction|Background|Related Work|Literature Review|Method|Methods|Methodology|'
            r'Proposed Method|Model|Architecture|Experimental Setup|Experiments|Results|Evaluation|Discussion|'
            r'Conclusion|Conclusions|Future Work|Acknowledgements|References|Bibliography|Works Cited|Appendix)\b',
            clean_line, re.IGNORECASE
        )
        if m_kw:
            kw = m_kw.group(1).lower()
            return (clean_line, kw in REFERENCE_KEYWORDS)

        return None

    def _split_into_sentences(self, text: str) -> List[str]:
        # Handle linebreaks inside text
        cleaned = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if not cleaned:
            return []

        # Split on sentence end punctuation followed by space and uppercase/quote
        sentence_end_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"])')
        raw_sentences = sentence_end_pattern.split(cleaned)

        # Merge sentences that were split on common abbreviations
        abbrevs = {'e.g.', 'i.e.', 'et al.', 'fig.', 'figs.', 'tab.', 'eq.', 'ref.', 'refs.', 'dr.', 'prof.', 'vs.', 'vol.', 'no.'}
        sentences = []
        buffer = ""

        for s in raw_sentences:
            if buffer:
                buffer += " " + s
            else:
                buffer = s

            last_word = buffer.split()[-1].lower() if buffer.split() else ""
            if last_word in abbrevs or (len(last_word) == 2 and last_word.endswith('.')):
                continue

            sentences.append(buffer.strip())
            buffer = ""

        if buffer:
            sentences.append(buffer.strip())

        return [s for s in sentences if s]

    def split(self, document: Document) -> list[Document]:
        text = document.content.strip()
        if not text:
            return []

        lines = text.split('\n')
        # Scan lines to detect inline section headers and section segments
        line_sections = []
        active_sec = document.section or self._current_section
        active_ref = document.is_reference or self._is_reference_section

        for line in lines:
            hdr = self._detect_section_header(line)
            if hdr:
                active_sec, active_ref = hdr
                self._current_section = active_sec
                self._is_reference_section = active_ref
            line_sections.append((line, active_sec, active_ref))

        # Check heuristic citation density on the page
        if not active_ref:
            citation_matches = len(re.findall(r'\[\d+\]\s+[A-Z]', text)) + len(re.findall(r'DOI:\s*10\.', text, re.IGNORECASE))
            if citation_matches >= 3:
                active_ref = True
                active_sec = "References"
                self._is_reference_section = True
                line_sections = [(l, active_sec, active_ref) for l, _, _ in line_sections]

        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk_sentences = []
        current_length = 0

        for sentence in sentences:
            # Match sentence back to closest line section
            sentence_sec = active_sec
            sentence_ref = active_ref

            # Find matching line section if sentence starts with line
            for l_text, l_sec, l_ref in line_sections:
                if l_text.strip() and l_text.strip() in sentence:
                    if l_sec:
                        sentence_sec = l_sec
                        sentence_ref = l_ref
                        break

            sentence_len = len(sentence)

            if current_length + sentence_len > self.chunk_size and current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences).strip()
                chunk_hash = hashlib.md5(f"{document.source}_{document.page}_{len(chunks)}_{chunk_text[:50]}".encode()).hexdigest()[:12]
                chunk_id = f"{document.source}_p{document.page}_{chunk_hash}"
                chunks.append(
                    Document(
                        content=chunk_text,
                        source=document.source,
                        title=document.title,
                        page=document.page,
                        section=sentence_sec,
                        is_reference=sentence_ref,
                        chunk_id=chunk_id
                    )
                )

                overlap_sentences = []
                overlap_len = 0
                for s in reversed(current_chunk_sentences):
                    if overlap_len + len(s) <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break

                current_chunk_sentences = overlap_sentences
                current_length = overlap_len

            current_chunk_sentences.append(sentence)
            current_length += sentence_len + 1

        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences).strip()
            chunk_hash = hashlib.md5(f"{document.source}_{document.page}_{len(chunks)}_{chunk_text[:50]}".encode()).hexdigest()[:12]
            chunk_id = f"{document.source}_p{document.page}_{chunk_hash}"
            chunks.append(
                Document(
                    content=chunk_text,
                    source=document.source,
                    title=document.title,
                    page=document.page,
                    section=active_sec,
                    is_reference=active_ref,
                    chunk_id=chunk_id
                )
            )

        return chunks