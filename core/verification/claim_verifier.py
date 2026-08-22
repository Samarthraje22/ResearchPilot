import re
from typing import List, Dict, Any


class ClaimVerifier:

    def _extract_claims(self, text: str) -> List[str]:
        # Filter out meta sections, disclaimers, audit log blocks, tables, and citation listings line by line
        lines = text.split('\n')
        substantive_lines = []

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            # Ignore markdown headers, disclaimers, meta notes, section titles, tables, citation lists
            l_lower = line_clean.lower()
            if line_clean.startswith(('#', '|', '>', '*', '[')) or '---' in line_clean:
                if any(kw in l_lower for kw in ['note:', 'disclaimer:', 'audit log', 'reference', '---', 'gap title:', 'supporting source', 'supporting evidence', 'explanation:', '|']):
                    continue

            if any(l_lower.startswith(kw) for kw in [
                'note:', 'disclaimer:', '*(note:', '*(disclaimer:', 'references:',
                'gap title:', 'supporting source:', 'supporting evidence:', 'explanation:',
                'executive summary', 'sub-question findings', 'comparative analysis',
                'potential research gaps', 'claim verification audit log', 'sub-question findings:'
            ]):
                continue

            # Ignore line if it's purely citation metadata list like "[1] Source: ..."
            if re.match(r'^\[\d+\]\s*(Source:|http|arXiv|data/papers)', line_clean, re.IGNORECASE):
                continue

            substantive_lines.append(line_clean)

        filtered_text = " ".join(substantive_lines)
        cleaned = re.sub(r'#+\s*', '', filtered_text)
        cleaned = re.sub(r'\*+\s*', '', cleaned)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', cleaned)

        claims = []
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) <= 25:
                continue
            s_lower = s_clean.lower()
            if any(s_lower.startswith(kw) or kw in s_lower for kw in [
                'note:', 'disclaimer:', '*(note:', '*(disclaimer:', 'references:',
                'gap title:', 'supporting source:', 'supporting evidence:', 'explanation:',
                'paper 1:', 'paper 2:', 'summary:', 'paper analysis:', 'comparison:',
                'similarities:', 'differences:', 'trade-offs:', '[insufficient evidence notice]:',
                '[recency notice]:', 'missing requested terms', 'available literature sources',
                'no speculative claims are asserted'
            ]):
                continue
            claims.append(s_clean)

        return claims

    def verify_answer(self, answer: str, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        claims = self._extract_claims(answer)
        if not claims:
            return {
                "total_claims": 0,
                "supported_count": 0,
                "partially_supported_count": 0,
                "unsupported_count": 0,
                "groundedness_score": 1.0,
                "claims": []
            }

        verified_claims = []
        supported_cnt = 0
        partially_cnt = 0
        unsupported_cnt = 0

        for claim in claims:
            # Extract keywords from claim
            words = set(re.findall(r'\b[a-zA-Z0-9]{4,}\b', claim.lower()))
            if not words:
                continue

            best_match_id = None
            best_overlap = 0.0

            for ev in evidence_list:
                ev_text = ev.get("content", "").lower()
                ev_words = set(re.findall(r'\b[a-zA-Z0-9]{4,}\b', ev_text))
                if not ev_words:
                    continue

                overlap = len(words.intersection(ev_words)) / float(len(words))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match_id = ev.get("citation_id")

            # Determine verification status based strictly on substantive evidence text overlap
            if best_overlap >= 0.40:
                status = "Supported ✅"
                supported_cnt += 1
            elif best_overlap >= 0.20:
                status = "Partially supported ⚠️"
                partially_cnt += 1
            else:
                status = "Unsupported ❌"
                unsupported_cnt += 1

            verified_claims.append({
                "claim": claim,
                "status": status,
                "matched_citation_id": best_match_id,
                "best_overlap": round(best_overlap, 3)
            })

        total = len(verified_claims)
        groundedness = (supported_cnt + 0.5 * partially_cnt) / float(total) if total > 0 else 1.0

        return {
            "total_claims": total,
            "supported_count": supported_cnt,
            "partially_supported_count": partially_cnt,
            "unsupported_count": unsupported_cnt,
            "groundedness_score": round(groundedness, 3),
            "claims": verified_claims
        }
