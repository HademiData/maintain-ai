from __future__ import annotations

import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from rag import (
    RetrievalIndex,
    build_retrieval_index,
    search_documents,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


HF_TOKEN = os.getenv("HF_TOKEN")

MODEL = os.getenv(
    "MAINTAIN_AI_MODEL",
    "deepseek-ai/DeepSeek-V3-0324",
)


# Keep a finite timeout so a stalled remote inference request
# does not hold the Render worker indefinitely.
HF_TIMEOUT = float(
    os.getenv(
        "HF_TIMEOUT",
        "90",
    )
)


# ============================================================
# HUGGING FACE CLIENT
# ============================================================

client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto",
    timeout=HF_TIMEOUT,
)


# ============================================================
# RETRIEVAL STATE
# ============================================================

_retrieval_index: RetrievalIndex | None = None


def get_retrieval_index() -> RetrievalIndex:
    """
    Lazily initialize the maintenance retrieval index.

    Building this index is intentionally deferred until the first
    organization-specific question. This keeps application startup
    lightweight and allows Render to bind to the HTTP port quickly.
    """

    global _retrieval_index

    if _retrieval_index is None:
        print(
            "Initializing maintenance retrieval index..."
        )

        _retrieval_index = (
            build_retrieval_index()
        )

    return _retrieval_index


# ============================================================
# CONFIGURATION
# ============================================================

def require_huggingface_token() -> None:
    """
    Ensure AI inference is configured before making an external call.
    """

    if not HF_TOKEN:
        raise RuntimeError(
            "HF_TOKEN is not configured. "
            "Add HF_TOKEN to the Render environment variables."
        )


def is_ai_configured() -> bool:
    """
    Used by the health endpoint.
    """

    return bool(HF_TOKEN)


# ============================================================
# JSON RESPONSE PARSING
# ============================================================

def parse_json_response(
    response_text: str,
) -> dict[str, Any]:
    """
    Parse JSON returned by the language model.

    Handles normal JSON and JSON wrapped in Markdown code fences.
    """

    if not response_text:
        raise ValueError(
            "The language model returned an empty response."
        )

    cleaned = response_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]

    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    parsed = json.loads(
        cleaned.strip()
    )

    if not isinstance(parsed, dict):
        raise ValueError(
            "The language model returned JSON, "
            "but the root value was not an object."
        )

    return parsed


# ============================================================
# QUESTION CLASSIFICATION
# ============================================================

ORGANIZATION_KEYWORDS = (
    "bc-01",
    "item number",
    "item no",
    "equipment record",
    "equipment history",
    "maintenance history",
    "maintenance interval",
    "maintenance schedule",
    "maintenance manual",
    "maintenance document",
    "inspection result",
    "inspection procedure",
    "spare part",
    "spare parts",
    "part number",
    "work order",
    "workorder",
    "inventory",
    "organization document",
)


MAINTENANCE_COMPONENTS = (
    "conveyor",
    "idler",
    "pulley",
    "bearing",
    "gearbox",
    "gear box",
    "scraper",
    "take-up",
    "take up",
    "drive motor",
)


def classify_question(
    question: str,
) -> str:
    """
    Classify questions without an additional LLM call.

    This deliberately uses deterministic rules because the project
    only needs two categories:

        organization-specific maintenance
        general engineering

    Removing the classifier LLM call gives us:
      - lower latency
      - lower API usage
      - fewer failure points
      - more predictable behavior
    """

    normalized = (
        question
        .strip()
        .lower()
    )

    for keyword in ORGANIZATION_KEYWORDS:
        if keyword in normalized:
            return "organization_maintenance"

    has_component = any(
        component in normalized
        for component in MAINTENANCE_COMPONENTS
    )

    maintenance_terms = (
        "maintain",
        "maintenance",
        "inspect",
        "inspection",
        "repair",
        "replace",
        "replacement",
        "troubleshoot",
        "troubleshooting",
        "fault",
        "failure",
        "damaged",
    )

    has_maintenance_term = any(
        term in normalized
        for term in maintenance_terms
    )

    if (
        has_component
        and has_maintenance_term
    ):
        return "organization_maintenance"

    return "general_engineering"


# ============================================================
# PROMPTS
# ============================================================

MAINTENANCE_SYSTEM_PROMPT = """
You are Maintain AI, an AI-powered maintenance planning and
operations assistant for industrial organizations.

Your role is to help maintenance planners, maintenance engineers,
and operations teams make practical, evidence-based maintenance
decisions.

The primary demonstration asset is industrial belt conveyor BC-01.

Relevant components may include:

- Conveyor belt
- Pulleys
- Idlers
- Bearings
- Drive motor
- Gearbox
- Scrapers
- Take-up system
- Safety equipment


SOURCE OF TRUTH

The retrieved maintenance documents are the primary source of truth
for organization-specific information.

Never invent:

- Equipment data
- Maintenance history
- Inspection results
- Costs
- Quantities
- Specifications
- Maintenance intervals
- Item numbers
- Priorities
- Operational impact


If the requested organization-specific information is not present,
say:

"Not specified in the available maintenance documents."


DOCUMENTED INFORMATION VS ENGINEERING JUDGMENT

Clearly distinguish information supported by the maintenance
documents from general engineering judgment.

Never present general engineering knowledge as though it came from
the organization's documents.


PRIORITY

Never assume HIGH, MEDIUM, or LOW priority.

Priority must be supported by the user's request or documented
evidence such as severity, safety risk, or operational impact.

If priority cannot be established:

"priority": null


REASON

The reason must describe only the condition stated by the user or
explicitly documented.

Do not invent production impact, downtime, failure consequences,
severity, or operational impact.


EQUIPMENT AND COMPONENT

Use exact equipment and component information supported by the
retrieved documents.

If BC-01 is the equipment identifier, use:

"name": "Belt Conveyor"
"item_number": "BC-01"

Do not replace an equipment name with an identifier.


ITEM NUMBERS

Never invent item numbers.

If an item number is unavailable, use:

"Item number not specified in the available maintenance documents."


REQUIRED PARTS

A part may only be placed under "required_parts" if the retrieved
documents explicitly establish that the part is required for the
specific maintenance task.

Do not assume that associated components are required.

Inventory presence alone does not mean that an item is required.

When no required part is explicitly established:

"required_parts": []


CONDITIONAL PARTS

If a part may be required depending on inspection, condition, or
findings, place it under "recommended_actions" instead.

Do not place conditional parts under "required_parts".

Do not include conditional parts in the cost.


CONSUMABLES

Only include a consumable when the retrieved documents explicitly
state that it is required for the exact maintenance task.

If no consumable is explicitly confirmed:

"consumables": []


COST

Only calculate estimated material cost from confirmed required
parts and consumables with documented costs.

Do not invent costs.

If no confirmed required items have documented costs:

"estimated_material_cost": null


SAFETY

Only include safety requirements supported by the documents or
clearly required by the stated maintenance procedure.

Safety equipment and procedures belong under "safety", not
"required_parts".


WORK ORDERS

When creating a maintenance work order, use only information
supported by the user's request and retrieved documents.

Return:

{
  "type": "maintenance_work_order",
  "equipment": {
    "name": "",
    "item_number": ""
  },
  "component": {
    "name": "",
    "item_number": ""
  },
  "priority": null,
  "task": "",
  "reason": "",
  "required_parts": [],
  "consumables": [],
  "estimated_material_cost": null,
  "recommended_actions": [],
  "safety": [],
  "sources": []
}


NORMAL MAINTENANCE QUESTIONS

For normal questions return:

{
  "type": "simple_answer",
  "answer": "",
  "sources": []
}


RESPONSE FORMAT

Return ONLY valid JSON.

Do not return Markdown.

Do not return code fences.

Do not add explanations outside the JSON.

Keep answers concise and practical.
"""


GENERAL_ENGINEERING_SYSTEM_PROMPT = """
You are Maintain AI, a practical general engineering knowledge
assistant.

Answer general engineering questions clearly, accurately, and
practically.

Topics may include:

- Mechanical engineering
- Electrical engineering
- Maintenance engineering
- Bearings
- Motors
- Gearboxes
- Materials
- Manufacturing
- Engineering principles
- Engineering terminology
- Equipment operation
- Engineering calculations
- Maintenance concepts


This is a GENERAL ENGINEERING question.

Do not use organization-specific maintenance documents.

Do not pretend that an answer came from organization-specific
documents.

Do not unnecessarily relate the answer to BC-01.

If the question is simple, give a simple answer.

Use practical examples when they improve understanding.

Return ONLY valid JSON:

{
  "type": "general_engineering",
  "answer": "",
  "sources": []
}

For general engineering questions, sources must always be an empty
array.

Return JSON only.
"""


# ============================================================
# LLM CALL
# ============================================================

def run_chat_completion(
    system_prompt: str,
    user_prompt: str,
    history: list[dict[str, Any]],
) -> str:
    """
    Execute a single remote DeepSeek request.

    DeepSeek remains hosted remotely through Hugging Face.
    Render never loads the DeepSeek model locally.
    """

    require_huggingface_token()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Previous conversation:\n\n"
                    f"{json.dumps(history, ensure_ascii=False)}"
                    "\n\n"
                    "Current request:\n\n"
                    f"{user_prompt}"
                ),
            },
        ],
        max_tokens=500,
        temperature=0.1,
    )

    return (
        response.choices[0]
        .message
        .content
        or ""
    )


# ============================================================
# MAIN MAINTAIN AI PIPELINE
# ============================================================

def ask_maintain_ai(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Run the complete Maintain AI pipeline.
    """

    if history is None:
        history = []

    request_start = time.time()

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    classification_start = time.time()

    question_type = classify_question(
        question
    )

    classification_time = (
        time.time()
        - classification_start
    )

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    context = ""
    sources: list[str] = []
    retrieval_time = 0.0

    if (
        question_type
        == "organization_maintenance"
    ):
        retrieval_start = time.time()

        retrieval_index = (
            get_retrieval_index()
        )

        context, sources = (
            search_documents(
                question,
                retrieval_index,
                top_k=3,
            )
        )

        retrieval_time = (
            time.time()
            - retrieval_start
        )

    # --------------------------------------------------------
    # Prompt construction
    # --------------------------------------------------------

    if (
        question_type
        == "organization_maintenance"
    ):
        user_prompt = f"""
MAINTENANCE KNOWLEDGE

{context if context else "No relevant maintenance document content was found."}


USER QUESTION

{question}


Use the retrieved maintenance knowledge as the primary source of
truth.

If the required organization-specific information is not present,
state:

"Not specified in the available maintenance documents."

Do not invent information.

Return ONLY valid JSON.
"""

        system_prompt = (
            MAINTENANCE_SYSTEM_PROMPT
        )

    else:
        user_prompt = question

        system_prompt = (
            GENERAL_ENGINEERING_SYSTEM_PROMPT
        )

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    llm_start = time.time()

    raw_response = run_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        history=history,
    )

    llm_time = (
        time.time()
        - llm_start
    )

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    try:
        result = parse_json_response(
            raw_response
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        # Preserve the model's answer rather than crashing the
        # entire API when the model returns non-JSON content.
        result = {
            "type": (
                "general_engineering"
                if question_type
                == "general_engineering"
                else "simple_answer"
            ),
            "answer": raw_response,
            "sources": [],
        }

    # --------------------------------------------------------
    # Source enforcement
    # --------------------------------------------------------

    if (
        question_type
        == "organization_maintenance"
    ):
        result["sources"] = sources

    else:
        result["sources"] = []

    # --------------------------------------------------------
    # Type enforcement
    # --------------------------------------------------------

    if not result.get("type"):
        result["type"] = (
            "general_engineering"
            if question_type
            == "general_engineering"
            else "simple_answer"
        )

    # --------------------------------------------------------
    # Performance metadata
    # --------------------------------------------------------

    request_time = (
        time.time()
        - request_start
    )

    result["_performance"] = {
        "question_type": question_type,
        "classification_time": round(
            classification_time,
            3,
        ),
        "retrieval_time": round(
            retrieval_time,
            3,
        ),
        "llm_time": round(
            llm_time,
            3,
        ),
        "request_time": round(
            request_time,
            3,
        ),
    }

    return result


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    print(
        "Maintain AI CLI"
    )

    print(
        "Type 'exit' to quit."
    )

    while True:

        question = input(
            "\nAsk Maintain AI: "
        ).strip()

        if not question:
            continue

        if question.lower() in {
            "exit",
            "quit",
            "bye",
        }:
            print(
                "\nMaintain AI session ended."
            )
            break

        try:
            result = ask_maintain_ai(
                question
            )

            print("\nMaintain AI:")

            print(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                )
            )

        except Exception as error:
            print(
                f"\nError: {error}"
            )