"""LLM-as-a-judge automated scorer using Ollama (local).

Same output shape as manual.py so the two can be compared in calibration.
Calls Ollama REST API at http://localhost:11434 — no external API key needed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .schemas import TicketScore

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

SYSTEM_PROMPT = """
You are an expert AI Evaluation System for Customer Support Ticket Summaries.

TASK
Grade the candidate summary against the reference summary. Identify the facts in the reference, judge whether each is preserved, and score three dimensions. Output ONLY valid JSON — no markdown fences, no introductory text, no explanations outside the JSON.

CRITICAL GATE RULE (knockout — non-negotiable)
1. Identify the product name(s) mentioned in the REFERENCE.
2. If the candidate summary does NOT mention the product name(s), the gate is automatically FAIL.
3. A FAIL gate overrides every other score. Do not let high precision, recall, or specificity override a missing product.
4. If product_kept is false, gate MUST be "FAIL".

EVALUATION DIMENSIONS (score each 0.0 to 5.0, one decimal allowed)
1. Precision (weight 35%): Are all facts in the summary supported by the reference? Penalize hallucinations, invented root causes, or overstatements.
2. Recall (weight 40%): Are all key diagnostic facts from the reference preserved? Penalize missing product, missing trigger, missing stage, or missing symptom.
3. Specificity (weight 25%): Does it include specific product names, error causes, and technical details? Generic phrases score lower.

OUTPUT JSON SCHEMA (exact keys, no extra keys):
{
  "product_kept": boolean,
  "facts_kept": [list of reference facts preserved in the summary],
  "facts_lost": [list of reference facts missing from the summary],
  "invented_claims": [list of claims in the summary NOT supported by the reference],
  "precision_score": float (0.0-5.0),
  "precision_reasoning": string,
  "recall_score": float (0.0-5.0),
  "recall_reasoning": string,
  "specificity_score": float (0.0-5.0),
  "specificity_reasoning": string,
  "gate": "PASS" or "FAIL",
  "verdict": string,
  "reason": string
}

FEW-SHOT EXAMPLES

Example 1 — PASS, incomplete recall
Reference: "Customer locked out of CloudSync after resetting their password."
Candidate Summary: "User cannot log in to CloudSync."
Expected output:
{
  "product_kept": true,
  "facts_kept": ["CloudSync", "cannot log in / locked out"],
  "facts_lost": ["after resetting password"],
  "invented_claims": [],
  "precision_score": 5.0,
  "precision_reasoning": "Product named and symptom accurate. No false claims.",
  "recall_score": 3.0,
  "recall_reasoning": "Captures product and symptom but drops the password-reset trigger.",
  "specificity_score": 5.0,
  "specificity_reasoning": "Names the product correctly; symptom is specific to lockout.",
  "gate": "PASS",
  "verdict": "PASS - incomplete",
  "reason": "Product kept; 1 of 3 reference facts lost."
}

Example 2 — FAIL, product missing (knockout)
Reference: "CloudSync sync process hangs near completion."
Candidate Summary: "Sync is stuck."
Expected output:
{
  "product_kept": false,
  "facts_kept": ["sync", "hangs / stuck"],
  "facts_lost": ["CloudSync", "near completion"],
  "invented_claims": [],
  "precision_score": 4.0,
  "precision_reasoning": "Symptom is accurate but product is missing.",
  "recall_score": 2.0,
  "recall_reasoning": "Drops product name and completion stage; major recall loss.",
  "specificity_score": 2.0,
  "specificity_reasoning": "Vague. No product name, no process stage.",
  "gate": "FAIL",
  "verdict": "FAIL",
  "reason": "Product not named — definitionally unactionable."
}

Example 3 — PASS with invention
Reference: "InvoicePro-generated PDFs are missing invoice line items."
Candidate Summary: "PDF export has a missing items bug in InvoicePro."
Expected output:
{
  "product_kept": true,
  "facts_kept": ["InvoicePro", "PDF", "missing items / line items"],
  "facts_lost": [],
  "invented_claims": ["bug"],
  "precision_score": 4.0,
  "precision_reasoning": "All facts supported, but 'bug' asserts a root cause not in reference.",
  "recall_score": 5.0,
  "recall_reasoning": "All reference facts preserved.",
  "specificity_score": 4.0,
  "specificity_reasoning": "Names product, format, and defect; specific and actionable.",
  "gate": "PASS",
  "verdict": "PASS with invention",
  "reason": "Product kept; invented claim 'bug' reduces precision slightly."
}

RULES
- Output exactly one JSON object. Do not wrap in ```json fences.
- gate must be exactly "PASS" or "FAIL".
- If product_kept is false, gate MUST be "FAIL".
- All scores must be floats between 0.0 and 5.0.
- Be strict: if a fact is only partially present, list it in facts_lost.
"""


def build_prompt(reference: str, summary: str) -> str:
    return (
        f"Reference: {reference}\n"
        f"Candidate Summary: {summary}\n"
        'Output JSON with keys: product_kept, facts_kept, facts_lost, '
        "invented_claims, precision_score, precision_reasoning, "
        "recall_score, recall_reasoning, specificity_score, "
        "specificity_reasoning, gate, verdict, reason."
    )


def _mock_llm(prompt: str) -> dict[str, Any]:
    """Deterministic stand-in for a real LLM call.

    Uses keyword heuristics so you can run the full pipeline end-to-end with
    no Ollama server running.
    """
    text = prompt.lower()

    if "cloudsync" in text and "cannot log in" in text:
        return {
            "product_kept": True,
            "facts_kept": ["CloudSync", "cannot log in / locked out"],
            "facts_lost": ["after resetting password"],
            "invented_claims": [],
            "precision_score": 5.0,
            "precision_reasoning": "Mock: product named, symptom captured, trigger dropped.",
            "recall_score": 3.0,
            "recall_reasoning": "Mock: missing password-reset trigger.",
            "specificity_score": 4.0,
            "specificity_reasoning": "Mock: names product, no invention.",
            "gate": "PASS",
            "verdict": "PASS - incomplete",
            "reason": "Mock T1",
        }

    if "sync is stuck" in text:
        return {
            "product_kept": False,
            "facts_kept": ["sync", "hangs / stuck"],
            "facts_lost": ["CloudSync", "near completion"],
            "invented_claims": [],
            "precision_score": 4.0,
            "precision_reasoning": "Mock: symptom captured, product dropped.",
            "recall_score": 2.0,
            "recall_reasoning": "Mock: missing product and completion stage.",
            "specificity_score": 2.0,
            "specificity_reasoning": "Mock: vague, no product or cause.",
            "gate": "FAIL",
            "verdict": "FAIL",
            "reason": "Mock T2",
        }

    if "invoicepro" in text and "missing items" in text:
        return {
            "product_kept": True,
            "facts_kept": ["InvoicePro", "PDF", "missing items / line items"],
            "facts_lost": [],
            "invented_claims": ["bug"],
            "precision_score": 4.0,
            "precision_reasoning": "Mock: complete facts, invents 'bug' root cause.",
            "recall_score": 5.0,
            "recall_reasoning": "Mock: all reference facts preserved.",
            "specificity_score": 4.0,
            "specificity_reasoning": "Mock: names product, format, and defect.",
            "gate": "PASS",
            "verdict": "PASS with invention",
            "reason": "Mock T3",
        }

    return {
        "product_kept": False,
        "facts_kept": [],
        "facts_lost": [],
        "invented_claims": [],
        "precision_score": 3.0,
        "precision_reasoning": "Mock: no real LLM wired yet.",
        "recall_score": 3.0,
        "recall_reasoning": "Mock: no real LLM wired yet.",
        "specificity_score": 3.0,
        "specificity_reasoning": "Mock: no real LLM wired yet.",
        "gate": "FAIL",
        "verdict": "FAIL",
        "reason": "Mock fallback",
    }


def call_llm(prompt: str) -> dict[str, Any]:
    """Call Ollama REST API and return parsed JSON."""
    use_mock = os.getenv("EVALUATION_FALLBACK_TO_MOCK", "0") == "1"
    if use_mock:
        return _mock_llm(prompt)

    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama API returned HTTP {e.code}: {detail}\n"
            f"Make sure Ollama is running at {OLLAMA_HOST} and model '{OLLAMA_MODEL}' is pulled."
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_HOST}. Is Ollama running?\n"
            f"Start it with: ollama serve\n"
            f"Pull the model with: ollama pull {OLLAMA_MODEL}\n"
            f"Original error: {e.reason}"
        ) from e
    except TimeoutError:
        raise RuntimeError(
            f"Ollama request timed out after 120 seconds. "
            f"Model '{OLLAMA_MODEL}' may be too large or system is overloaded."
        ) from e

    try:
        result = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama API returned invalid JSON: {body[:500]}") from e

    message = result.get("message", {})
    text = message.get("content", "")
    if not text:
        raise RuntimeError(f"Ollama returned no message content: {body[:500]}")

    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    return json.loads(text)


def score_llm(reference: str, summary: str, ticket_id: str) -> TicketScore:
    prompt = build_prompt(reference, summary)
    raw = call_llm(prompt)

    precision = float(raw.get("precision_score", 0.0))
    recall = float(raw.get("recall_score", 0.0))
    specificity = float(raw.get("specificity_score", 0.0))

    # Clamp to valid 0-5 range.
    precision = max(0.0, min(5.0, precision))
    recall = max(0.0, min(5.0, recall))
    specificity = max(0.0, min(5.0, specificity))

    weighted_total = TicketScore.compute_weighted(precision, recall, specificity)

    # Code-enforced gate (defense in depth; never trust LLM blindly).
    product_kept = bool(raw.get("product_kept", False))
    gate = "PASS" if product_kept else "FAIL"

    facts_kept = raw.get("facts_kept", [])
    facts_lost = raw.get("facts_lost", [])
    invented_claims = raw.get("invented_claims", [])

    total_facts = len(facts_kept) + len(facts_lost)
    coverage = round(len(facts_kept) / total_facts, 4) if total_facts else 0.0

    all_claims = len(facts_kept) + len(invented_claims)
    faithfulness = round(len(facts_kept) / all_claims, 4) if all_claims else 1.0

    reasons = []
    for key in ("precision_reasoning", "recall_reasoning", "specificity_reasoning"):
        if raw.get(key):
            reasons.append(f"{key}: {raw[key]}")

    return TicketScore(
        ticket_id=ticket_id,
        gate=gate,
        coverage=coverage,
        faithfulness=faithfulness,
        precision=precision,
        recall=recall,
        specificity=specificity,
        weighted_total=weighted_total,
        dimensions={
            "entity_grounding": precision,
            "completeness": recall,
            "faithfulness_5": specificity,
            "actionability": specificity,
        },
        verdict="PASS" if gate == "PASS" else "FAIL",
        reason=" | ".join(reasons) if reasons else "LLM judge returned no reasoning",
    )