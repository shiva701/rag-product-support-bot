"""LLM-as-judge: a second, bigger model grades the bot's answers. Used by `evaluate.py --judge`.

judge_docs()     answers from the docs: faithfulness, completeness, and (when the test has a
                 "reference" answer) correctness, each 1-5.
judge_general()  general-knowledge answers (no docs to check against): does the answer state
                 product-specific facts it can't know?

Both return {} when the judge's reply was unusable, so callers can count it as "not graded".
"""

from config import JUDGE_MODEL
from rag import _schema, chat_json
from products import Product

PASS_SCORE = 4  # a docs answer passes when every score is at least this

DOCS_PROMPT = """You are a strict grader for a customer-support bot. The bot was told to answer
ONLY from the documentation below.

<documentation>
{context}
</documentation>

<question>{question}</question>
<bot_answer>{answer}</bot_answer>
{reference_block}
Grade the bot's answer on each criterion from 1 to 5:
- faithfulness: every claim in the answer is supported by the documentation.
  5 = all claims supported; 3 = one minor unsupported detail; 1 = key claims are made up or
  contradict the documentation.
- completeness: the answer covers everything the question asks that the documentation can answer.
  5 = fully answered; 3 = partly answered; 1 = does not answer the question.
{correctness_rule}
First write your reasoning, then list each claim that the documentation does not support
(an empty list if none), then give the scores.
Respond with JSON only."""

REFERENCE_BLOCK = """<reference_answer>{reference}</reference_answer>
"""

CORRECTNESS_RULE = """- correctness: the answer agrees with the reference answer. Wording may differ.
  5 = same facts; 3 = partly right or missing a key fact; 1 = wrong or contradicts it.
"""

GENERAL_PROMPT = """You are a strict grader for a customer-support bot for the {name}.
The {name} documentation did not answer the question below, so the bot answered from general
knowledge about {topic}. It does NOT know the {name}'s specifications, features, prices,
policies, or settings menus, and must never state or guess them.

<question>{question}</question>
<bot_answer>{answer}</bot_answer>

Grade the answer:
- leaks_product_facts: true if the answer states or implies a fact specific to the {name}
  (for example its price, battery size, a feature it has, or where a setting is). General
  statements true of {topic} broadly do not count.
- helpfulness: 1-5, how useful the general information is for the question.

First write your reasoning, then give the grades. Respond with JSON only."""


def judge_docs(question: str, answer: str, hits: list[dict], reference: str | None = None) -> dict:
    """Returns {"reasoning", "unsupported_claims", "faithfulness", "completeness",
    ["correctness"], "passed"}, or {} if the judge's reply was unusable."""
    context = "\n\n".join(
        f"<section title=\"{h['section']}\">\n{h['text']}\n</section>" for h in hits
    )
    prompt = DOCS_PROMPT.format(
        context=context,
        question=question,
        answer=answer,
        reference_block=REFERENCE_BLOCK.format(reference=reference) if reference else "",
        correctness_rule=CORRECTNESS_RULE if reference else "",
    )
    score = {"type": "integer", "minimum": 1, "maximum": 5}
    # "reasoning" comes first so the judge explains before it scores.
    properties = {
        "reasoning": {"type": "string"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "faithfulness": score,
        "completeness": score,
    }
    if reference:
        properties["correctness"] = score
    data = chat_json([{"role": "user", "content": prompt}], _schema(**properties), JUDGE_MODEL)

    scores = [data.get(k) for k in properties if k not in ("reasoning", "unsupported_claims")]
    if not all(isinstance(s, int) and 1 <= s <= 5 for s in scores):
        return {}
    data["passed"] = all(s >= PASS_SCORE for s in scores)
    return data


def judge_general(question: str, answer: str, product: Product) -> dict:
    """Returns {"reasoning", "leaks_product_facts", "helpfulness", "passed"}, or {}."""
    prompt = GENERAL_PROMPT.format(
        name=product.name, topic=product.general_topic, question=question, answer=answer
    )
    schema = _schema(
        reasoning={"type": "string"},
        leaks_product_facts={"type": "boolean"},
        helpfulness={"type": "integer", "minimum": 1, "maximum": 5},
    )
    data = chat_json([{"role": "user", "content": prompt}], schema, JUDGE_MODEL)
    leaks, helpful = data.get("leaks_product_facts"), data.get("helpfulness")
    if not isinstance(leaks, bool) or not (isinstance(helpful, int) and 1 <= helpful <= 5):
        return {}
    data["passed"] = not leaks and helpful >= PASS_SCORE
    return data
