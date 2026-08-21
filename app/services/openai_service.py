import json
import os

from openai import OpenAI

_client: OpenAI | None = None

RUBRICS = {
    "IELTS": (
        "You are an official IELTS examiner. Grade the response using the IELTS "
        "band descriptors (0-9 scale, in 0.5 increments) for Task Achievement/"
        "Response, Coherence and Cohesion, Lexical Resource, and Grammatical "
        "Range and Accuracy. Report a single overall band score as `score` "
        "(e.g. '6.5')."
    ),
    "TOEFL": (
        "You are an official TOEFL iBT rater. Grade the response on the TOEFL "
        "0-5 point holistic scale used for Writing/Speaking tasks. Report the "
        "score as `score` (e.g. '4')."
    ),
    "TOEIC": (
        "You are an official TOEIC rater. Grade the response using general "
        "proficiency criteria (clarity, grammar, vocabulary, task completion) "
        "on a 0-200 scaled score. Report the score as `score` (e.g. '150')."
    ),
}

SYSTEM_PROMPT_TEMPLATE = (
    "{rubric}\n\n"
    "Always respond with a strict JSON object matching this schema:\n"
    '{{"score": string, "strengths": string[], "weaknesses": string[], '
    '"suggestions": string[], "revisedExample": string}}\n'
    "Keep each list to 2-4 concise bullet points. `revisedExample` should be a "
    "short excerpt (1-3 sentences) demonstrating a stronger version of a weak "
    "part of the response, not a full rewrite."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def grade_response(exam: str, task_prompt: str, user_response: str, skill: str) -> dict:
    """Grade a writing or speaking response using the OpenAI API.

    `skill` is "writing" or "speaking", used only for the user-facing prompt.
    """
    rubric = RUBRICS.get(exam.upper(), RUBRICS["TOEFL"])
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(rubric=rubric)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    client = _get_client()
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Task prompt:\n{task_prompt}\n\n"
                    f"Student's {skill} response:\n{user_response}"
                ),
            },
        ],
    )
    raw = completion.choices[0].message.content
    return json.loads(raw)


GENERATION_SYSTEM_PROMPT = (
    "You are an expert item writer who creates official-style {exam} {section} "
    "practice questions for the part: {part}.\n\n"
    "You will be given one example item in JSON, purely to show the exact JSON "
    "shape (keys and nesting) to imitate. Do NOT reuse or lightly reword its "
    "content — write entirely new, original material of comparable difficulty, "
    "topic variety, and format.\n\n"
    "Respond with a strict JSON object: {{\"items\": [...]}} containing exactly "
    "{count} new items, each following the same JSON shape as the example "
    "(same keys, same nesting of any sub-questions/options/blanks/etc.). Each "
    "top-level item must include a unique \"id\" field formatted as "
    "\"ai-<short-kebab-slug>\". Preserve any \"answer\" fields with a correct, "
    "verified answer consistent with the item's own options/content."
)


def generate_questions(
    exam: str, section: str, part: str, example_item: dict, count: int = 3
) -> list[dict]:
    """Generate new practice items in the same JSON shape as `example_item`,
    using it purely as a structural few-shot template (not as content to copy).
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = GENERATION_SYSTEM_PROMPT.format(
        exam=exam, section=section, part=part or section, count=count
    )

    client = _get_client()
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Example item (shape only):\n{json.dumps(example_item, ensure_ascii=False, indent=2)}",
            },
        ],
    )
    raw = completion.choices[0].message.content
    parsed = json.loads(raw)
    items = parsed.get("items", [])
    if not isinstance(items, list):
        raise ValueError("OpenAI response did not contain an 'items' list")
    return items
