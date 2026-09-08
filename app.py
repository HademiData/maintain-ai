import os
import time
import json

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from rag import build_knowledge_base, search_documents


# -----------------------------
# Environment
# -----------------------------

load_dotenv()


# -----------------------------
# Hugging Face
# -----------------------------

client = InferenceClient(
    api_key=os.getenv("HF_TOKEN")
)

MODEL = "deepseek-ai/DeepSeek-V3-0324"


# -----------------------------
# Response parsing
# -----------------------------

def parse_json_response(response_text):
    """
    Parse JSON returned by DeepSeek.

    Handles:
    - Normal JSON
    - JSON wrapped in ```json ... ```
    - JSON wrapped in ``` ... ```
    """

    cleaned = response_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]

    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())


# -----------------------------
# Question classification
# -----------------------------

def classify_question(question, history=None):

    if history is None:
        history = []

    response = client.chat.completions.create(
        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": """
You are the question classifier for Maintain AI.

Classify the user's question into exactly ONE category:

ORGANIZATION_MAINTENANCE
GENERAL_ENGINEERING


ORGANIZATION_MAINTENANCE:

Use this category when the question requires
organization-specific maintenance information.

This includes:

- BC-01
- Equipment records
- Maintenance procedures
- Maintenance schedules
- Inspection procedures
- Troubleshooting based on organization documents
- Spare parts
- Item numbers
- Work orders
- Maintenance planning
- Organization-specific maintenance information


Examples:

What is the item number of the BC-01 gearbox?

What maintenance should be performed on BC-01?

What spare parts are available for BC-01?

Create a work order for the damaged conveyor idler.

What does the BC-01 maintenance manual say about
the gearbox?


GENERAL_ENGINEERING:

Use this category for general engineering knowledge
that does not require organization-specific documents.

Examples:

What do the numbers in a bearing designation mean?

What is the difference between AC and DC?

What is MTBF?

How does a gearbox transmit torque?

Why does a bearing overheat?

What is the difference between preventive and
predictive maintenance?

Explain preventive maintenance.


IMPORTANT:

If the question mentions BC-01 or asks for
organization-specific equipment information,
classify it as ORGANIZATION_MAINTENANCE.


Return ONLY one of:

ORGANIZATION_MAINTENANCE

GENERAL_ENGINEERING
"""
            },
            {
                "role": "user",
                "content": f"""
                Previous conversation:

                {json.dumps(history, ensure_ascii=False)}

                Current question:

                {question}
"""
            }
        ],

        max_tokens=10,
        temperature=0.0
    )

    classification = (
        response.choices[0]
        .message
        .content
        .strip()
    )

    if "ORGANIZATION_MAINTENANCE" in classification:
        return "organization_maintenance"

    return "general_engineering"


# -----------------------------
# Load knowledge base
# -----------------------------

print("Loading maintenance knowledge base...")

kb_start = time.time()

embedding_model, index, chunks = build_knowledge_base()

kb_time = time.time() - kb_start

print(
    f"Knowledge base ready: {len(chunks)} chunks "
    f"({kb_time:.2f}s)"
)


# =========================================================
# MAIN MAINTAIN AI FUNCTION
# =========================================================

def ask_maintain_ai(question, history=None):

    if history is None:
        history = []
    # -------------------------
    # Classification
    # -------------------------

    classification_start = time.time()

    question_type = classify_question(question, history)

    classification_time = (
        time.time() - classification_start
    )


    # -------------------------
    # RAG retrieval
    # -------------------------

    context = ""
    sources = []

    retrieval_time = 0.0


    if question_type == "organization_maintenance":

        retrieval_start = time.time()

        context, sources = search_documents(
            question,
            embedding_model,
            index,
            chunks,
            top_k=3
        )

        retrieval_time = (
            time.time() - retrieval_start
        )


    # -------------------------
    # Build DeepSeek prompt
    # -------------------------

    if question_type == "organization_maintenance":

        system_prompt = """
You are Maintain AI, an AI-powered engineering and
maintenance assistant for industrial organizations.

Your role is to help maintenance planners,
maintenance engineers, and operations teams with
maintenance planning, troubleshooting, equipment
information, and general engineering questions.

Respond naturally, professionally, and conversationally.

Classify the user's message internally, but NEVER reveal
the classification, routing process, RAG pipeline,
knowledge base, or internal system logic.

For casual conversation, greetings, acknowledgements,
and simple social messages, respond naturally and briefly.
Do not force an engineering-related response when the
user is simply having a conversation.

For genuine engineering questions, provide clear,
accurate, and practical engineering knowledge.

For organization-specific maintenance questions, use
the retrieved maintenance documents as the primary
source of truth and clearly distinguish documented
information from general engineering judgment.



For organization-specific maintenance questions, use the provided maintenance
documents as the primary source of truth and clearly distinguish documented
information from general engineering knowledge.

Your role is to help maintenance planners,
maintenance engineers, and operations teams make
practical, evidence-based maintenance decisions.

The primary demonstration asset is industrial belt
conveyor BC-01.

Relevant components include:

- Conveyor belt
- Pulleys
- Idlers
- Bearings
- Drive motor
- Gearbox
- Scrapers
- Take-up system
- Safety equipment


IMPORTANT:

The retrieved maintenance documents are the primary
source of truth.

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


If information is unavailable, state exactly:

"Not specified in the available maintenance documents."


DOCUMENTED INFORMATION VS ENGINEERING JUDGMENT:

Clearly distinguish information supported by the
maintenance documents from general engineering
judgment.

Never present general engineering knowledge as if it
came from the organization's maintenance documents.


PRIORITY RULES:

Never assume a maintenance priority.

Priority must be supported by documented:

- Severity
- Safety risk
- Operational impact

Do not infer:

- Production impact
- Failure severity
- Operational impact
- Extent of damage

unless explicitly provided by the user or supported
by the retrieved documents.


MINIMUM-ANSWER PRINCIPLE:

Return only the information required to answer the
user's question.

If the user asks for a single identifier, number,
value, or fact, return only that value in the
"answer" field.

Do not add unnecessary explanations.


WORK-ORDER RULES:

When creating a maintenance work order, generate a
structured work order using ONLY information supported
by the user's request and the retrieved maintenance
documents.

Include:

- Equipment
- Equipment Item Number
- Component
- Component Item Number
- Priority
- Task
- Reason
- Required Parts
- Consumables
- Estimated Material Cost
- Recommended Actions
- Safety
- Sources


EQUIPMENT AND COMPONENT:

Use the exact equipment and component information
supported by the retrieved documents.

Do not confuse an equipment name with its item number.

If BC-01 is the equipment identifier, use:

"name": "Belt Conveyor"
"item_number": "BC-01"

Do not replace the equipment name with the identifier.


REQUIRED PARTS:

A part may ONLY be placed under "required_parts" if
the retrieved documents explicitly establish that the
part is required for the specific maintenance task.

Do NOT assume that associated components are required.

For example, when replacing an idler, do NOT automatically
include:

- Bearings
- Bolts
- Fasteners
- Grease
- Brackets
- Washers

unless the documents explicitly state that they are
required for that specific task.

If no required part is explicitly established:

"required_parts": []


CONDITIONAL PARTS:

If a part may be required depending on inspection,
condition, or findings, place it under
"recommended_actions" instead.

Do NOT place conditional parts under "required_parts".

Do NOT include conditional parts in the cost.


CONSUMABLES:

This rule is STRICT.

Only include a consumable when the retrieved documents
explicitly state that it is required for the EXACT
maintenance task.

Do NOT include a consumable simply because:

- It exists in inventory
- It is normally used during maintenance
- It is associated with the component
- It appears in the maintenance manual
- It would be useful

For example, do not automatically include:

- Bearing grease
- Cleaning cloth
- Lubricant
- Cleaning materials

for an idler replacement.

If no consumable is explicitly confirmed as required:

"consumables": []


COST:

Only calculate "estimated_material_cost" from parts
and consumables that are explicitly confirmed as
required for the task.

Do not include conditional or optional items.

Do not invent costs.

If no confirmed required items have documented costs:

"estimated_material_cost": null


PRIORITY:

Never assign HIGH, MEDIUM, or LOW unless the user or
retrieved documents provide sufficient evidence.

If priority cannot be established:

"priority": null


REASON:

The reason must describe ONLY the condition stated by
the user or explicitly documented.

Do not invent:

- Production impact
- Downtime
- Failure consequences
- Severity
- Safety risk
- Belt damage
- Operational impact

For example, if the user says:

"Create a work order for a damaged idler."

The reason should be based only on:

"Damaged idler reported by the user."

Do not add predicted consequences.


SAFETY:

Only include safety requirements supported by the
retrieved documents or clearly required by the stated
maintenance procedure.

Do not treat safety equipment as a required spare part.

For example, a lockout/tagout requirement belongs
under "safety", not "required_parts".


ITEM NUMBERS:

Never invent item numbers.

Use an item number only when it appears in the
retrieved documents.

If an item number is unavailable, state exactly:

"Item number not specified in the available maintenance documents."


SOURCES:

Only use source filenames provided by the Python
application.

Do not invent source filenames.

Every equipment, component, spare part, or consumable
must have an item number when available.

Never invent an item number.

If unavailable, state exactly:

"Item number not specified in the available maintenance documents."



REQUIRED PARTS:

This rule is STRICT.

An item MUST NOT be placed under "required_parts"
merely because:

- It belongs to the same equipment
- It is associated with the component
- It appears in the inventory document
- It is commonly replaced together
- It is physically part of the component
- It could potentially be needed

A part can ONLY be included in "required_parts" when
the retrieved documents explicitly state that the part
is required for the EXACT maintenance task being created.

Inventory presence alone does NOT mean the item is
required.

For example:

If the task is:

"Replace damaged idler"

Do NOT automatically include:

- Carrying idler
- Idler bearing
- Structural bolts
- Grease
- Cleaning cloth

unless the retrieved documents explicitly say that
those specific items are required for an idler
replacement.

If the documents only provide item numbers or inventory
availability, that is NOT sufficient evidence that the
item is required.

When no part is explicitly confirmed as required:

"required_parts": []


IMPORTANT:

Do not use engineering assumptions to fill
"required_parts".

When uncertain, leave the array empty.



CONDITIONAL ITEMS:

If a part depends on inspection or another condition,
do not list it under required_parts.

Place it under recommended_actions as a conditional
recommendation.

Conditional items must NOT be included in the
estimated material cost.


COST:

Estimated material cost must include ONLY confirmed
required items.

Do not estimate costs for conditional items.

Do not invent costs.

Use documented costs only.


SOURCES:

The Python application will provide the retrieved
source filenames.

Do not invent source filenames.


RESPONSE FORMAT:

Return ONLY valid JSON.

Do not return markdown.

Do not return code fences.

Do not add explanations outside the JSON.


For a normal maintenance question, use:

{
  "type": "simple_answer",
  "answer": "string",
  "sources": []
}


Other valid types are:

equipment_information
maintenance_information
troubleshooting
parts_cost


For a maintenance work order, use:

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


Return JSON only.
Keep responses concise and practical.
"""


        user_prompt = f"""
MAINTENANCE KNOWLEDGE:

{context}


USER QUESTION:

{question}


Use the retrieved maintenance knowledge as the
primary source of truth.

If the required information is not present,
state:

"Not specified in the available maintenance documents."

Do not invent information.

Return ONLY valid JSON.
"""


    else:

        system_prompt = """

You are Maintain AI, a practical general engineering
knowledge assistant.

Answer general engineering questions clearly,
accurately, and practically.

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
- Engineering concepts
- Maintenance concepts


This is a GENERAL ENGINEERING question.

Do not use the organization's maintenance documents.

Do not pretend that the answer came from the
organization's maintenance documents.

Do not unnecessarily relate the answer to BC-01.

If the question is simple, give a simple answer.

Use practical examples when they improve understanding.

Keep responses concise and useful.


RESPONSE FORMAT:

Return ONLY valid JSON.

Do not return markdown.

Do not return code fences.

Do not add explanations outside the JSON.

Use exactly:

{
  "type": "general_engineering",
  "answer": "string",
  "sources": []
}


Because this is general engineering knowledge,
sources MUST always be an empty array.

Return JSON only.
"""


        user_prompt = question


    # -------------------------
    # DeepSeek
    # -------------------------

    llm_start = time.time()

    response = client.chat.completions.create(
        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
            "role": "user",
            "content": f"""
            Previous conversation:

            {json.dumps(history, ensure_ascii=False)}

            Current request:

            {user_prompt}
    """
        }
        ],

        max_tokens=500,
        temperature=0.1
    )

    llm_time = time.time() - llm_start


    # -------------------------
    # Parse JSON
    # -------------------------

    raw_response = (
        response.choices[0]
        .message
        .content
    )


    try:

        result = parse_json_response(
            raw_response
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        result = {
            "type": (
                "general_engineering"
                if question_type ==
                "general_engineering"
                else "simple_answer"
            ),
            "answer": raw_response,
            "sources": []
        }


    # -------------------------
    # Source handling
    # -------------------------

    if question_type == "organization_maintenance":

        result["sources"] = sources

    else:

        result["sources"] = []


    # -------------------------
    # Ensure type exists
    # -------------------------

    if "type" not in result:

        if question_type == "general_engineering":

            result["type"] = "general_engineering"

        else:

            result["type"] = "simple_answer"


    # -------------------------
    # Performance metadata
    # -------------------------

    result["_performance"] = {
        "classification_time": round(
            classification_time,
            3
        ),
        "retrieval_time": round(
            retrieval_time,
            3
        ),
        "llm_time": round(
            llm_time,
            3
        ),
        "request_time": round(
            classification_time
            + retrieval_time
            + llm_time,
            3
        )
    }


    return result


# =========================================================
# CLI MODE
# =========================================================

if __name__ == "__main__":

    while True:

        question = input(
            "\nAsk Maintain AI: "
        ).strip()


        if not question:
            continue


        if question.lower() in [
            "exit",
            "quit",
            "bye"
        ]:

            print(
                "\nMaintain AI session ended."
            )

            break


        result = ask_maintain_ai(
            question
        )


        print("\nMaintain AI:")

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )


        print("\nPerformance:")

        performance = result.get(
            "_performance",
            {}
        )

        print(
            f"- Question classification: "
            f"{performance.get('classification_time', 0):.3f}s"
        )

        print(
            f"- RAG retrieval: "
            f"{performance.get('retrieval_time', 0):.3f}s"
        )

        print(
            f"- LLM response: "
            f"{performance.get('llm_time', 0):.3f}s"
        )

        print(
            f"- Request time: "
            f"{performance.get('request_time', 0):.3f}s"
        )
