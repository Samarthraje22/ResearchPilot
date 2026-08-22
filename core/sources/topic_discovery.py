import os
import re
from collections import Counter
from typing import List, Dict, Any, Optional

from pypdf import PdfReader

from core.sources.arxiv_source import ArxivSource
from core.utils.cache import topic_profile_cache, related_papers_cache


class TopicDiscoveryEngine:

    # ---------------------------------------------------------------
    # Words that do not describe a research topic.
    # ---------------------------------------------------------------

    STOPWORDS = {
        "about", "above", "after", "again", "against", "all", "also",
        "although", "among", "and", "another", "any", "are", "around",
        "as", "at", "because", "been", "before", "being", "below",
        "between", "both", "but", "by", "can", "could", "data",
        "during", "each", "few", "for", "from", "further", "given",
        "had", "has", "have", "having", "here", "how", "however",
        "into", "its", "itself", "just", "may", "more", "most",
        "much", "must", "new", "not", "now", "of", "off", "often",
        "on", "once", "one", "only", "or", "other", "our", "out",
        "over", "own", "same", "should", "since", "some", "such",
        "than", "that", "the", "their", "them", "then", "there",
        "therefore", "these", "they", "this", "those", "through",
        "to", "too", "under", "until", "up", "upon", "use", "used",
        "using", "very", "was", "were", "what", "when", "where",
        "which", "while", "who", "why", "will", "with", "within",
        "without", "would", "we", "our", "us", "you", "your",
        "than", "thus", "via"
    }

    # Generic academic words.
    GENERIC_TERMS = {
        "paper",
        "papers",
        "study",
        "studies",
        "research",
        "researcher",
        "researchers",
        "work",
        "works",
        "method",
        "methods",
        "approach",
        "approaches",
        "model",
        "models",
        "system",
        "systems",
        "framework",
        "frameworks",
        "analysis",
        "analyses",
        "result",
        "results",
        "experiment",
        "experiments",
        "performance",
        "problem",
        "problems",
        "solution",
        "solutions",
        "application",
        "applications",
        "process",
        "processes",
        "function",
        "functions",
        "based",
        "using",
        "used",
        "proposed",
        "present",
        "presented",
        "provide",
        "provides",
        "develop",
        "developed",
        "development",
        "existing",
        "different",
        "various",
        "general",
        "information",
        "important",
        "effective",
        "novel",
        "network",
        "networks",
        "learning",
        "machine",
        "deep"
    }

    # Words normally coming from references / publication metadata.
    BAD_TERMS = {
        "citation",
        "citations",
        "reference",
        "references",
        "author",
        "authors",
        "doi",
        "arxiv",
        "copyright",
        "license",
        "received",
        "accepted",
        "published",
        "journal",
        "volume",
        "issue",
        "university",
        "department",
        "institute",
        "school",
        "faculty"
    }

    # ---------------------------------------------------------------
    # Dynamic concept extraction.
    #
    # These are NOT topics. They are common technical constructions
    # found in scientific papers. They help identify phrases without
    # hardcoding PINN, NLP, CV, cybersecurity, etc.
    # ---------------------------------------------------------------

    TECHNICAL_SUFFIXES = (
        "algorithm",
        "algorithms",
        "architecture",
        "architectures",
        "classifier",
        "classification",
        "clustering",
        "computation",
        "computational",
        "convergence",
        "detection",
        "estimation",
        "forecasting",
        "identification",
        "inference",
        "optimization",
        "prediction",
        "regression",
        "representation",
        "simulation",
        "solver",
        "solvers",
        "training",
        "validation",
        "segmentation",
        "generation",
        "embedding",
        "embeddings",
        "attention",
        "transformer",
        "transformers",
        "encoding",
        "decoding",
        "sampling",
        "refinement",
        "decomposition",
        "regularization",
        "generalization",
        "stability",
        "robustness",
        "uncertainty",
        "differential",
        "equation",
        "equations",
        "optimization",
        "optimization",
        "loss",
        "activation",
        "gradient",
        "boundary",
        "condition",
        "conditions",
        "operator",
        "operators"
    )

    def __init__(
        self,
        arxiv_source: Optional[ArxivSource] = None
    ):
        self.arxiv_source = (
            arxiv_source
            if arxiv_source is not None
            else ArxivSource()
        )

    # ===============================================================
    # PDF EXTRACTION
    # ===============================================================

    def _extract_pdf_text(
        self,
        filepath: str
    ) -> str:

        if not filepath or not os.path.exists(filepath):
            return ""

        try:
            reader = PdfReader(filepath)

            page_texts = []

            for page in reader.pages:

                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""

                if page_text.strip():
                    page_texts.append(page_text)

            return self._normalize_pdf_text(
                "\n\n".join(page_texts)
            )

        except Exception as e:

            print(
                f"[TopicDiscovery ERROR] "
                f"PDF extraction failed: {e}"
            )

            return ""

    def _normalize_pdf_text(
        self,
        text: str
    ) -> str:

        if not text:
            return ""

        text = (
            text
            .replace("\x00", " ")
            .replace("ﬁ", "fi")
            .replace("ﬂ", "fl")
            .replace("ﬀ", "ff")
            .replace("ﬃ", "ffi")
            .replace("ﬄ", "ffl")
            .replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("–", "-")
            .replace("—", "-")
        )

        # Repair PDF line-break hyphenation.
        #
        # physics-
        # informed
        #
        # -> physics-informed
        text = re.sub(
            r"([A-Za-z]{2,})-\s*\n\s*([A-Za-z]{2,})",
            r"\1-\2",
            text
        )

        text = re.sub(
            r"[ \t]*\n[ \t]*",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ===============================================================
    # CLEANING
    # ===============================================================

    def _remove_noise(
        self,
        text: str
    ) -> str:

        if not text:
            return ""

        # URLs.
        text = re.sub(
            r"https?://\S+",
            " ",
            text,
            flags=re.IGNORECASE
        )

        # DOI.
        text = re.sub(
            r"\bdoi\s*:\s*\S+",
            " ",
            text,
            flags=re.IGNORECASE
        )

        # Numeric citations.
        text = re.sub(
            r"\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\]",
            " ",
            text
        )

        text = re.sub(
            r"\(\s*\d+(?:\s*[-,]\s*\d+)*\s*\)",
            " ",
            text
        )

        # Broken reference fragments.
        text = re.sub(
            r"\b\d+\]\.?",
            " ",
            text
        )

        # Common PDF extraction artifact.
        text = re.sub(
            r"\bhow-\s*ever\b",
            "however",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ===============================================================
    # ABSTRACT
    # ===============================================================

    def _extract_abstract(
        self,
        pdf_text: str
    ) -> str:

        if not pdf_text:
            return ""

        match = re.search(
            r"(?is)"
            r"\babstract\b"
            r"\s*[:.]?\s*"
            r"(.*?)"
            r"(?="
            r"\bkeywords?\b"
            r"|\b1[\.\s]+introduction\b"
            r"|\bintroduction\b"
            r"|\bbackground\b"
            r"|$"
            r")",
            pdf_text
        )

        if not match:
            return ""

        abstract = self._remove_noise(
            match.group(1)
        )

        if len(abstract) < 50:
            return ""

        return abstract[:6000]

    # ===============================================================
    # KEYWORDS
    # ===============================================================

    def _extract_explicit_keywords(
        self,
        pdf_text: str
    ) -> List[str]:

        if not pdf_text:
            return []

        match = re.search(
            r"(?is)"
            r"\bkeywords?\b"
            r"\s*[:\-]\s*"
            r"(.*?)"
            r"(?="
            r"\b1[\.\s]+introduction\b"
            r"|\bintroduction\b"
            r"|\bbackground\b"
            r"|$"
            r")",
            pdf_text
        )

        if not match:
            return []

        raw = self._remove_noise(
            match.group(1)
        )

        result = []

        for item in re.split(
            r"[,;|]",
            raw
        ):

            item = re.sub(
                r"\s+",
                " ",
                item.strip().lower()
            )

            if not item:
                continue

            if len(item) > 100:
                continue

            if item in self.STOPWORDS:
                continue

            if item in self.BAD_TERMS:
                continue

            if item not in result:
                result.append(item)

        return result[:20]

    # ===============================================================
    # TITLE
    # ===============================================================
    #
    # Title is metadata only.
    # It does NOT participate in concept extraction.
    # ===============================================================

    def _extract_title(
        self,
        pdf_text: str,
        filepath: str
    ) -> str:

        if not pdf_text:
            return ""

        # Try PDF metadata first.
        try:
            reader = PdfReader(filepath)

            metadata = reader.metadata

            if metadata:

                title = (
                    getattr(
                        metadata,
                        "title",
                        None
                    )
                    or metadata.get(
                        "/Title",
                        ""
                    )
                )

                if title:
                    title = str(title).strip()
                    title_lower = title.lower()
                    is_junk = any(kw in title_lower for kw in [
                        "microsoft word", "untitled", "document1", "unnamed",
                        ".docx", ".doc", ".tex", ".pdf", "latex",
                    ])

                    if not is_junk and 10 <= len(title) <= 300:
                        return title

        except Exception:
            pass

        # Try visible beginning of document using raw page text
        # (pdf_text is normalized with all newlines collapsed, so we
        #  must re-read raw page text for line-based title detection)
        try:
            reader = PdfReader(filepath)
            raw_text = ""
            for page in reader.pages[:2]:
                raw_text += (page.extract_text() or "") + "\n"
        except Exception:
            raw_text = ""

        if not raw_text.strip():
            return ""

        lines = [
            line.strip()
            for line in raw_text.split("\n")
            if line.strip()
        ]

        for line in lines[:50]:

            if len(line) < 15:
                continue

            if len(line) > 300:
                continue

            if re.match(
                r"(?i)^(abstract|keywords?|"
                r"introduction|citation|doi|"
                r"received|accepted|published)\b",
                line
            ):
                continue

            if "@" in line:
                continue

            if re.search(
                r"(?i)\b(university|department|"
                r"institute|college|faculty)\b",
                line
            ):
                continue

            # Skip journal header lines
            if re.search(
                r"(?i)\b(vol\.\s*\d|issn|journal of)\b",
                line
            ):
                continue

            # Skip URLs and DOI lines
            if re.match(
                r"(?i)\s*(https?://|doi\s*:|orcid)",
                line
            ):
                continue

            # Skip lines that are mostly numbers/dates
            letters = len(re.findall(r"[a-zA-Z]", line))
            if letters < 10:
                continue

            return line

        return ""

    # ===============================================================
    # TOKENIZATION
    # ===============================================================

    def _tokenize(
        self,
        text: str
    ) -> List[str]:

        return re.findall(
            r"\b[a-z][a-z0-9\-]{3,40}\b",
            text.lower()
        )

    def _valid_term(
        self,
        term: str
    ) -> bool:

        term = term.strip().lower()

        if len(term) < 4:
            return False

        if term in self.STOPWORDS:
            return False

        if term in self.GENERIC_TERMS:
            return False

        if term in self.BAD_TERMS:
            return False

        if re.fullmatch(
            r"\d+",
            term
        ):
            return False

        return True

    # ===============================================================
    # DYNAMIC TECHNICAL PHRASES
    # ===============================================================

    def _extract_dynamic_phrases(
        self,
        text: str
    ) -> List[str]:

        tokens = [
            token
            for token in self._tokenize(text)
            if self._valid_term(token)
        ]

        if len(tokens) < 2:
            return []

        bigrams = Counter()
        trigrams = Counter()

        for i in range(
            len(tokens) - 1
        ):

            a = tokens[i]
            b = tokens[i + 1]

            phrase = f"{a} {b}"

            if (
                a in self.GENERIC_TERMS
                or b in self.GENERIC_TERMS
            ):
                continue

            bigrams[phrase] += 1

        for i in range(
            len(tokens) - 2
        ):

            a = tokens[i]
            b = tokens[i + 1]
            c = tokens[i + 2]

            phrase = f"{a} {b} {c}"

            if (
                a in self.GENERIC_TERMS
                or b in self.GENERIC_TERMS
                or c in self.GENERIC_TERMS
            ):
                continue

            trigrams[phrase] += 1

        phrases = []

        # A phrase appearing several times is much more likely
        # to represent an actual research concept.
        for phrase, count in trigrams.most_common(50):

            if count >= 2:
                phrases.append(phrase)

        for phrase, count in bigrams.most_common(80):

            if count >= 2:
                phrases.append(phrase)

        return phrases

    # ===============================================================
    # CONTENT-BASED CONCEPT EXTRACTION
    # ===============================================================

    def _extract_terms(
        self,
        title: str,
        abstract: str,
        pdf_text: str
    ) -> List[str]:

        if not pdf_text:
            return []

        clean_full = self._remove_noise(
            pdf_text
        ).lower()

        clean_abstract = self._remove_noise(
            abstract
        ).lower()

        # -----------------------------------------------------------
        # IMPORTANT:
        #
        # Title is deliberately NOT included here.
        # -----------------------------------------------------------

        frequencies = Counter()

        full_tokens = self._tokenize(
            clean_full
        )

        for token in full_tokens:

            if self._valid_term(token):
                frequencies[token] += 1

        # Abstract receives extra weight because it summarizes
        # the actual research problem/contribution.
        abstract_tokens = self._tokenize(
            clean_abstract
        )

        for token in abstract_tokens:

            if self._valid_term(token):
                frequencies[token] += 5

        # -----------------------------------------------------------
        # Explicit keywords from PDF.
        # -----------------------------------------------------------

        explicit_keywords = (
            self._extract_explicit_keywords(
                pdf_text
            )
        )

        # -----------------------------------------------------------
        # Dynamic multi-word phrases from FULL PDF.
        # -----------------------------------------------------------

        dynamic_phrases = (
            self._extract_dynamic_phrases(
                clean_full
            )
        )

        # -----------------------------------------------------------
        # Build candidate concepts.
        # -----------------------------------------------------------

        candidates = []

        # Explicit keywords are strongest because the authors
        # explicitly declared them as keywords.
        for keyword in explicit_keywords:

            if keyword not in candidates:
                candidates.append(keyword)

        # Repeated technical phrases.
        for phrase in dynamic_phrases:

            words = phrase.split()

            if any(
                word in self.BAD_TERMS
                for word in words
            ):
                continue

            if phrase not in candidates:
                candidates.append(phrase)

        # Frequent meaningful terms.
        for term, count in frequencies.most_common(100):

            if count < 2:
                continue

            if term not in candidates:
                candidates.append(term)

        # -----------------------------------------------------------
        # Score concepts.
        #
        # This prevents random frequent words from dominating.
        # -----------------------------------------------------------

        scored = []

        for concept in candidates:

            concept = concept.strip().lower()

            if not concept:
                continue

            words = concept.split()

            if all(
                word in self.STOPWORDS
                for word in words
            ):
                continue

            frequency = 0

            if len(words) == 1:
                frequency = frequencies.get(
                    concept,
                    0
                )
            else:
                frequency = (
                    clean_full.count(
                        concept
                    )
                )

            if frequency <= 0:
                continue

            score = float(frequency)

            # Multi-word concepts are more informative.
            if len(words) >= 2:
                score *= 2.5

            if len(words) >= 3:
                score *= 1.5

            # Explicit author keywords get a substantial boost.
            if concept in explicit_keywords:
                score *= 4.0

            # Terms ending in common technical suffixes get
            # a modest boost, without hardcoding a domain.
            if any(
                word.endswith(
                    self.TECHNICAL_SUFFIXES
                )
                for word in words
            ):
                score *= 1.5

            scored.append(
                (
                    score,
                    concept
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        result = []

        for _, concept in scored:

            # Avoid returning a single word when an existing
            # stronger phrase contains that same word.
            if len(concept.split()) == 1:

                covered_by_phrase = False

                for existing in result:

                    if (
                        len(existing.split()) >= 2
                        and concept in existing.split()
                    ):
                        covered_by_phrase = True
                        break

                if covered_by_phrase:
                    continue

            if concept not in result:
                result.append(concept)

            if len(result) >= 20:
                break

        return result

    # ===============================================================
    # SEARCH QUERY GENERATION
    # ===============================================================

    def _build_search_queries(
        self,
        terms: List[str]
    ) -> List[str]:

        if not terms:
            return []

        queries = []

        multi_word = [
            term
            for term in terms
            if len(term.split()) >= 2
        ]

        single_word = [
            term
            for term in terms
            if len(term.split()) == 1
        ]

        # ArxivSource itself limits queries to five terms.
        # Therefore we deliberately construct compact queries.

        # Query 1: strongest multi-word concepts.
        if multi_word:

            query = " ".join(
                multi_word[:3]
            )

            if query:
                queries.append(query)

        # Query 2: mix strongest concepts.
        mixed = []

        for term in multi_word[:2]:
            mixed.append(term)

        for term in single_word[:2]:

            if term not in mixed:
                mixed.append(term)

        if mixed:

            queries.append(
                " ".join(mixed[:4])
            )

        # Query 3: alternate concepts.
        alternate = []

        for term in multi_word[3:6]:

            if term not in alternate:
                alternate.append(term)

        for term in single_word[2:4]:

            if term not in alternate:
                alternate.append(term)

        if alternate:

            queries.append(
                " ".join(alternate[:4])
            )

        # Query 4: strongest individual technical concepts.
        if single_word:

            query = " ".join(
                single_word[:5]
            )

            if query:
                queries.append(query)

        # Deduplicate.
        result = []

        for query in queries:

            query = re.sub(
                r"\s+",
                " ",
                query
            ).strip()

            if not query:
                continue

            if query.lower() not in [
                item.lower()
                for item in result
            ]:
                result.append(query)

        return result[:4]

    # ===============================================================
    # TOPIC PROFILE
    # ===============================================================

    def extract_topic_profile(
        self,
        filepath: str
    ) -> Dict[str, Any]:

        empty_profile = {
            "title": "",
            "abstract": "",
            "authors": [],
            "published_year": None,
            "key_terms": [],
            "search_query": "",
            "search_queries": []
        }

        if not filepath or not os.path.exists(filepath):
            return empty_profile

        # Check cache by filepath and modification time
        try:
            cache_key = f"profile:{filepath}:{os.path.getmtime(filepath)}"
            cached_res = topic_profile_cache.get(cache_key)
            if cached_res:
                return cached_res
        except Exception:
            cache_key = None

        # -----------------------------------------------------------
        # FULL PDF.
        # -----------------------------------------------------------

        pdf_text = self._extract_pdf_text(
            filepath
        )

        if not pdf_text:
            return empty_profile

        title = self._extract_title(
            pdf_text,
            filepath
        )

        abstract = self._extract_abstract(
            pdf_text
        )

        # -----------------------------------------------------------
        # CONTENT ONLY.
        #
        # Title is NOT passed as a topic signal.
        # -----------------------------------------------------------

        key_terms = self._extract_terms(
            title="",
            abstract=abstract,
            pdf_text=pdf_text
        )

        search_queries = (
            self._build_search_queries(
                key_terms
            )
        )

        profile = {
            "title": title,
            "abstract": abstract,
            "authors": [],
            "published_year": None,
            "key_terms": key_terms[:15],
            "search_query": (
                search_queries[0]
                if search_queries
                else ""
            ),
            "search_queries": search_queries
        }

        if cache_key:
            topic_profile_cache.set(cache_key, profile)

        return profile

    # ===============================================================
    # PAPER TEXT
    # ===============================================================

    def _paper_text(
        self,
        doc: Any
    ) -> str:

        title = str(
            getattr(
                doc,
                "title",
                ""
            ) or ""
        )

        content = str(
            getattr(
                doc,
                "content",
                ""
            ) or ""
        )

        return (
            title
            + " "
            + content
        ).lower()

    # ===============================================================
    # RELEVANCE SCORING
    # ===============================================================

    def _relevance_score(
        self,
        profile: Dict[str, Any],
        doc: Any
    ) -> float:

        terms = [
            str(term).strip().lower()
            for term in profile.get(
                "key_terms",
                []
            )
            if str(term).strip()
        ]

        if not terms:
            return 0.0

        paper_title = str(
            getattr(
                doc,
                "title",
                ""
            ) or ""
        ).lower()

        paper_content = str(
            getattr(
                doc,
                "content",
                ""
            ) or ""
        ).lower()

        meaningful_terms = [
            term
            for term in terms
            if (
                term not in self.STOPWORDS
                and term not in self.GENERIC_TERMS
                and term not in self.BAD_TERMS
            )
        ]

        if not meaningful_terms:
            return 0.0

        total_weight = 0.0
        matched_weight = 0.0

        for term in meaningful_terms:

            # Phrases are more informative than individual words.
            weight = (
                3.0
                if len(term.split()) >= 2
                else 1.0
            )

            total_weight += weight

            if term in paper_content:
                matched_weight += weight

        content_score = (
            matched_weight / total_weight
            if total_weight
            else 0.0
        )

        # -----------------------------------------------------------
        # Explicit keyword / abstract concepts dominate.
        #
        # arXivSource returns title + abstract as `content`.
        # -----------------------------------------------------------

        abstract_score = content_score

        # -----------------------------------------------------------
        # Title is intentionally tiny.
        # -----------------------------------------------------------

        title_weight = 0.0
        title_matches = 0.0

        for term in meaningful_terms:

            weight = (
                1.0
                if len(term.split()) >= 2
                else 0.25
            )

            title_weight += weight

            if term in paper_title:
                title_matches += weight

        title_score = (
            title_matches / title_weight
            if title_weight
            else 0.0
        )

        # -----------------------------------------------------------
        # Exact phrase bonus.
        # -----------------------------------------------------------

        phrase_matches = 0

        for term in meaningful_terms:

            if len(term.split()) < 2:
                continue

            if term in paper_content:
                phrase_matches += 1

        phrase_bonus = min(
            phrase_matches * 0.03,
            0.15
        )

        # -----------------------------------------------------------
        # Final score.
        #
        # Content = 85%
        # Candidate title = 5%
        # Exact technical concepts = 10%
        #
        # Uploaded filename is never involved.
        # -----------------------------------------------------------

        score = (
            content_score * 0.85
            + title_score * 0.05
            + phrase_bonus * 0.10
        )

        return round(
            min(
                max(
                    score,
                    0.0
                ),
                1.0
            ),
            3
        )

    # ===============================================================
    # RELATED PAPERS
    # ===============================================================

    def discover_related_papers(
        self,
        filepath: str,
        min_relevance: float = 0.15,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:

        # Check cache
        try:
            cache_key = f"related:{filepath}:{os.path.getmtime(filepath)}:{min_relevance}:{max_results}"
            cached_res = related_papers_cache.get(cache_key)
            if cached_res is not None:
                return cached_res
        except Exception:
            cache_key = None

        profile = self.extract_topic_profile(
            filepath
        )

        terms = profile.get(
            "key_terms",
            []
        )

        queries = profile.get(
            "search_queries",
            []
        )

        if not terms or not queries:
            return []

        all_documents = []

        # -----------------------------------------------------------
        # Search using CONTENT-derived queries only.
        # -----------------------------------------------------------

        for query in queries:

            try:

                print(
                    "[TopicDiscovery] "
                    f"Searching arXiv from PDF content: "
                    f"{query}",
                    flush=True
                )

                documents = self.arxiv_source.fetch(
                    query,
                    max_results=10
                )

                if documents:
                    all_documents.extend(
                        documents
                    )

            except Exception as e:

                print(
                    "[TopicDiscovery ERROR] "
                    f"Search failed for '{query}': {e}",
                    flush=True
                )

        if not all_documents:
            return []

        # -----------------------------------------------------------
        # Deduplicate.
        # -----------------------------------------------------------

        unique_documents = {}

        for doc in all_documents:

            source = str(
                getattr(
                    doc,
                    "source",
                    ""
                ) or ""
            ).strip()

            title = str(
                getattr(
                    doc,
                    "title",
                    ""
                ) or ""
            ).strip().lower()

            key = source or title

            if key and key not in unique_documents:
                unique_documents[key] = doc

        # -----------------------------------------------------------
        # Rank.
        # -----------------------------------------------------------

        ranked = []

        for doc in unique_documents.values():

            score = self._relevance_score(
                profile,
                doc
            )

            if score < min_relevance:
                continue

            title = str(
                getattr(
                    doc,
                    "title",
                    ""
                ) or "Untitled Paper"
            ).strip()

            content = str(
                getattr(
                    doc,
                    "content",
                    ""
                ) or ""
            ).strip()

            source = str(
                getattr(
                    doc,
                    "source",
                    ""
                ) or "arXiv"
            ).strip()

            published_year = getattr(
                doc,
                "published_year",
                None
            )

            # -------------------------------------------------------
            # Explain why this paper matched.
            # -------------------------------------------------------

            paper_text = (
                title
                + " "
                + content
            ).lower()

            matched_terms = []

            for term in terms:

                term = str(
                    term
                ).strip().lower()

                if not term:
                    continue

                if (
                    term in self.STOPWORDS
                    or term in self.GENERIC_TERMS
                    or term in self.BAD_TERMS
                ):
                    continue

                if term in paper_text:

                    if term not in matched_terms:
                        matched_terms.append(
                            term
                        )

            matched_terms = matched_terms[:5]

            if matched_terms:

                reason = (
                    "Matches research concepts extracted "
                    "from the uploaded PDF: "
                    + ", ".join(matched_terms)
                    + "."
                )

            else:

                reason = (
                    "Ranked using content-derived "
                    "research concept similarity."
                )

            arxiv_id = source

            if arxiv_id.lower().startswith(
                "arxiv:"
            ):
                arxiv_id = arxiv_id[
                    len("arxiv:"):
                ]

            ranked.append(
                {
                    "title": title,
                    "authors": [],
                    "published_year": published_year,
                    "arxiv_id": source,
                    "abstract": content[:1200],
                    "relevance_score": round(
                        score * 100
                    ),
                    "source_url": (
                        f"https://arxiv.org/abs/{arxiv_id}"
                        if arxiv_id
                        else "https://arxiv.org"
                    ),
                    "reason_for_relevance": reason
                }
            )

        ranked.sort(
            key=lambda item: item[
                "relevance_score"
            ],
            reverse=True
        )

        final_results = ranked[:max_results]
        if cache_key:
            related_papers_cache.set(cache_key, final_results)

        return final_results