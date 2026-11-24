"""
Planner service (Unit II: Planning & Reasoning).

Parses the user's free-form request text into a structured RequestIntent
that the Orchestrator uses to decide which optional stages a run needs
(e.g. "flag anything over 5000" → Anomaly Detection, "compare to last
month" → Period Comparison), instead of always running a single fixed
sequence regardless of what was asked.

A deterministic keyword/regex pass always runs first so the planner works
fully offline. When GROQ_API_KEY is configured, an LLM pass refines the
result for phrasing the regex rules don't anticipate. The LLM can only
*add* to or override specific fields with valid values; if it fails or
returns something unparseable, the deterministic result stands untouched.
"""
import os
import re
import json

from app.state.blackboard import RequestIntent
from app.services.guardrails import PlannerIntentOutput, sanitize_for_prompt

_THRESHOLD_PATTERN = re.compile(
    r"(?:flag|highlight|show|list)[^.\n]*?(?:over|above|exceeding|greater than|more than)"
    r"\s*(?:inr|₹|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
)
_THRESHOLD_FALLBACK_PATTERN = re.compile(
    r"(?:over|above|exceeding|greater than|more than)\s*(?:inr|₹|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
)
_COMPARE_PATTERN = re.compile(
    r"\bcompar(?:e|ison)\b|\bvs\.?\b|\bversus\b|previous month|last month'?s|"
    r"month[- ]over[- ]month|change (?:since|from) (?:last|previous)",
)


def _parse_deterministic(text: str) -> RequestIntent:
    intent = RequestIntent(planning_mode="deterministic")
    lower = (text or "").lower()

    match = _THRESHOLD_PATTERN.search(lower) or _THRESHOLD_FALLBACK_PATTERN.search(lower)
    if match:
        try:
            intent.anomaly_threshold = float(match.group(1).replace(",", ""))
        except ValueError:
            pass

    if _COMPARE_PATTERN.search(lower):
        intent.compare_to_previous = True

    return intent


def _refine_with_llm(text: str, intent: RequestIntent) -> RequestIntent:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "test_key":
        return intent

    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import PromptTemplate

        llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.0, api_key=api_key)
        prompt = PromptTemplate(
            input_variables=["text"],
            template=(
                "Extract planning intent for an expense-reporting agent from this request.\n"
                "Request: {text}\n\n"
                "Respond with ONLY a JSON object, no explanation, with exactly these keys:\n"
                '  "anomaly_threshold": a number, or null if the user did not ask to flag '
                "expenses above some amount,\n"
                '  "compare_to_previous": true if the user wants this period compared against '
                "the previous period/month, otherwise false.\n"
            ),
        )
        chain = prompt | llm
        result = chain.invoke({"text": sanitize_for_prompt(text, max_length=500)})
        content = re.sub(r"```(?:json)?|```", "", result.content).strip()
        # Schema-validate before trusting anything the model returned; a
        # response that doesn't fit the schema raises and is caught below,
        # leaving the deterministic result from _parse_deterministic intact.
        validated = PlannerIntentOutput.model_validate(json.loads(content))

        # Only override a field the LLM actually extracted a value for;
        # an omitted/null field leaves the deterministic pass's result in
        # place rather than silently clearing it.
        if validated.anomaly_threshold is not None:
            intent.anomaly_threshold = validated.anomaly_threshold
        if validated.compare_to_previous is not None:
            intent.compare_to_previous = validated.compare_to_previous
        intent.planning_mode = "llm"
    except Exception as e:
        # The deterministic result already parsed above stands; only the
        # provenance label and diagnostic differ.
        intent.planner_error = str(e)

    return intent


def parse_intent(request_text: str) -> RequestIntent:
    """Parse a RequestIntent out of the user's free-form request text."""
    intent = _parse_deterministic(request_text)
    return _refine_with_llm(request_text, intent)
