import json
import re
from typing import List, Dict, Any, Optional
from core.llm.base import LLM
from core.llm.router import LLMRouter


class ResearchPlanner:

    def __init__(self, llm: Optional[LLM] = None, max_sub_questions: int = 4):
        self.llm = llm or LLMRouter()
        self.max_sub_questions = max_sub_questions

    def create_plan(self, topic: str) -> Dict[str, Any]:
        prompt = (
            "You are an expert academic research planner. Decompose the following research topic into targeted sub-questions.\n"
            f"Topic: {topic}\n\n"
            f"Requirements:\n"
            f"1. Generate between 2 and {self.max_sub_questions} sub-questions.\n"
            "2. Each sub-question must focus on a distinct aspect (e.g. theoretical foundations, methodology/architectures, practical performance/advantages, limitations/challenges).\n"
            "3. Output MUST be valid JSON only, matching this exact structure:\n"
            "{\n"
            '  "main_topic": "<topic>",\n'
            '  "sub_questions": [\n'
            "    {\n"
            '      "id": "SQ1",\n'
            '      "sub_question": "<specific question>",\n'
            '      "objective": "<research objective>",\n'
            '      "source_preference": "arxiv"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "JSON Response:"
        )

        response = self.llm.generate(prompt)
        plan = self._parse_json_response(response, topic)

        # Enforce max sub-questions constraint
        if len(plan.get("sub_questions", [])) > self.max_sub_questions:
            plan["sub_questions"] = plan["sub_questions"][:self.max_sub_questions]

        return plan

    def _parse_json_response(self, text: str, fallback_topic: str) -> Dict[str, Any]:
        try:
            # Look for JSON markdown block or raw JSON object
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if "sub_questions" in data and isinstance(data["sub_questions"], list):
                    return data
        except Exception as e:
            print(f"[ResearchPlanner WARNING] JSON parsing failed: {e}. Using rule-based fallback plan.")

        # Heuristic fallback plan if LLM did not return strict JSON
        return {
            "main_topic": fallback_topic,
            "sub_questions": [
                {
                    "id": "SQ1",
                    "sub_question": f"What are the primary theoretical foundations of {fallback_topic}?",
                    "objective": "Understand foundational principles and mathematical frameworks.",
                    "source_preference": "arxiv"
                },
                {
                    "id": "SQ2",
                    "sub_question": f"What are the major methods and performance advantages of {fallback_topic}?",
                    "objective": "Analyze architectural approaches and performance metrics.",
                    "source_preference": "arxiv"
                },
                {
                    "id": "SQ3",
                    "sub_question": f"What limitations, noise challenges, or open questions exist for {fallback_topic}?",
                    "objective": "Identify current bottlenecks and limitations in existing literature.",
                    "source_preference": "arxiv"
                }
            ]
        }
