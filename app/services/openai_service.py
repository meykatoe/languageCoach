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
