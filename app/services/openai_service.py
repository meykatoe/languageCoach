import json
import os

from openai import OpenAI

from app.database import SessionLocal
from app.models import AppSetting

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "alloy"

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


def resolve_config() -> tuple[str | None, str]:
    """Resolve the OpenAI API key and model to use, preferring the value
    saved via the frontend Settings page (stored in AppSetting) and falling
    back to the .env-provided environment variables.
    """
    db = SessionLocal()
    try:
        setting = db.query(AppSetting).first()
    finally:
        db.close()

    api_key = (setting.openai_api_key if setting else None) or os.environ.get("OPENAI_API_KEY")
    model = (
        (setting.openai_model if setting else None)
        or os.environ.get("OPENAI_MODEL")
        or DEFAULT_MODEL
    )
    return api_key, model


def _get_client() -> tuple[OpenAI, str]:
    api_key, model = resolve_config()
    if not api_key:
        raise RuntimeError(
            "OpenAI API Key 尚未設定。請點右上角的 ⚙️ 設定，或編輯後端 .env 檔案。"
        )
    return OpenAI(api_key=api_key), model


def test_connection(api_key: str | None = None) -> str:
    """Verify an API key works with a minimal, cheap call. If `api_key` is
    omitted, tests whichever key `resolve_config()` currently resolves to
    (saved settings, falling back to .env). Returns the model id used for
    the check on success; raises RuntimeError/openai.APIError on failure.
    """
    if api_key is None:
        api_key, _ = resolve_config()
    if not api_key:
        raise RuntimeError("尚未提供任何 API Key 可供測試。")

    client = OpenAI(api_key=api_key)
    models = client.models.list()
    first = next(iter(models), None)
    return first.id if first else "(no models returned, but the key is valid)"


def grade_response(exam: str, task_prompt: str, user_response: str, skill: str) -> dict:
    """Grade a writing or speaking response using the OpenAI API.

    `skill` is "writing" or "speaking", used only for the user-facing prompt.
    """
    rubric = RUBRICS.get(exam.upper(), RUBRICS["TOEFL"])
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(rubric=rubric)

    client, model = _get_client()
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


def synthesize_speech(text: str, voice: str = DEFAULT_TTS_VOICE) -> bytes:
    """Generate spoken audio (MP3 bytes) for a listening transcript via the
    OpenAI TTS API, for the "播放語音" button (replacing the browser's
    built-in speechSynthesis with a real, natural-sounding voice).
    """
    client, _ = _get_client()
    response = client.audio.speech.create(
        model=DEFAULT_TTS_MODEL, voice=voice, input=text, response_format="mp3"
    )
    return response.content


TRANSLATION_SYSTEM_PROMPT = (
    "You are a professional translator. Translate the given exam question "
    "text into natural, easy-to-understand Traditional Chinese (繁體中文). "
    "Preserve the original line breaks and any option labels (A./B./C./D.) "
    "line by line. Output only the translation, with no extra commentary, "
    "preamble, or markdown formatting."
)


def translate_text(text: str) -> str:
    """Translate a block of English exam-question text into Traditional
    Chinese, for the per-question "translate" button on the frontend.
    """
    client, model = _get_client()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return completion.choices[0].message.content.strip()


REVIEW_PROGRESS_SYSTEM_PROMPT = (
    "You are a friendly, encouraging {exam} tutor helping a student review a "
    "question in their error notebook that they previously got wrong. Here "
    "is your earlier note about their mistake:\n\"{previous_note}\"\n\n"
    "The student has just attempted this same question again. In "
    "Traditional Chinese (繁體中文), write a brief (2-4 short sentences) "
    "updated comment: if they answered correctly this time, congratulate "
    "them and briefly confirm they've corrected the earlier "
    "misunderstanding; if they are still wrong, note whether it looks like "
    "the same mistake as before or a new one, and give refined guidance. "
    "Respond with plain text only, no JSON, no markdown."
)


def review_progress_comment(
    exam: str,
    question_node: dict,
    correct_answer: object,
    submitted_answer: object,
    is_correct: bool,
    previous_note: str,
) -> str:
    """Generate an updated review-notebook comment for a repeat attempt,
    taking the previously recorded mistake note into account.
    """
    system_prompt = REVIEW_PROGRESS_SYSTEM_PROMPT.format(exam=exam, previous_note=previous_note)

    client, model = _get_client()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Question:\n{json.dumps(question_node, ensure_ascii=False)}\n\n"
                    f"Correct answer: {correct_answer}\n"
                    f"Student's answer this time: {submitted_answer}\n"
                    f"Correct this time: {is_correct}"
                ),
            },
        ],
    )
    return completion.choices[0].message.content.strip()


MISTAKE_EXPLANATION_SYSTEM_PROMPT = (
    "You are a friendly, encouraging {exam} tutor. A student answered a "
    "practice question incorrectly. In Traditional Chinese (繁體中文), write a "
    "brief, easy-to-understand explanation (2-4 short sentences) of why their "
    "answer is wrong and where their misunderstanding lies, based on the "
    "question, the correct answer, and what they submitted. Focus on the "
    "reasoning, not just restating the correct answer. Respond with plain "
    "text only, no JSON, no markdown."
)


def explain_mistake(
    exam: str, question_node: dict, correct_answer: object, submitted_answer: object
) -> str:
    """Generate a brief explanation of why a submitted answer was wrong, to
    be stored as a note in the user's error notebook (review page).
    """
    system_prompt = MISTAKE_EXPLANATION_SYSTEM_PROMPT.format(exam=exam)

    client, model = _get_client()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Question:\n{json.dumps(question_node, ensure_ascii=False)}\n\n"
                    f"Correct answer: {correct_answer}\n"
                    f"Student's answer: {submitted_answer}"
                ),
            },
        ],
    )
    return completion.choices[0].message.content.strip()


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
    system_prompt = GENERATION_SYSTEM_PROMPT.format(
        exam=exam, section=section, part=part or section, count=count
    )

    client, model = _get_client()
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


UPLOAD_GENERATION_SYSTEM_PROMPT = (
    "You are an expert item writer. A user has uploaded reference material "
    "(it could be a past exam, a textbook excerpt, an article, or any study "
    "material). Based on its topic, question type (if any), and difficulty, "
    "generate {count} new, original practice items of a similar style and "
    "difficulty. Do NOT copy sentences or questions from the reference "
    "material verbatim — write entirely new content only inspired by its "
    "topic, tone, and format.\n\n"
    "Choose exactly ONE of the following JSON shapes — whichever best fits "
    "what the reference material looks like — and produce all {count} items "
    "in that same shape:\n\n"
    "Shape A - single multiple-choice question:\n"
    '{{"id": "...", "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "B"}}\n\n'
    "Shape B - short passage with multiple-choice sub-questions:\n"
    '{{"id": "...", "title": "...", "passage": "...", "questions": '
    '[{{"id": "...", "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "..."}}]}}\n\n'
    "Shape C - fill-in-the-blank text completion (mark blanks in the text "
    'like ___(1)___, ___(2)___):\n'
    '{{"id": "...", "text": "... ___(1)___ ...", "blanks": '
    '[{{"id": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "..."}}]}}\n\n'
    "Shape D - open-ended writing or speaking prompt (use this if the "
    "material is an essay, article, or discussion topic rather than a "
    "quiz):\n"
    '{{"id": "...", "prompt": "..."}}\n\n'
    "Respond with a strict JSON object: {{\"items\": [...]}} containing "
    "exactly {count} items, each with a unique \"id\" formatted as "
    "\"upload-<short-kebab-slug>\". Preserve any \"answer\" fields with a "
    "correct, verified answer consistent with the item's own options."
)


def generate_from_reference(reference_text: str, count: int = 3) -> list[dict]:
    """Generate new practice items inspired by arbitrary uploaded reference
    text (not tied to any existing question bank shape).
    """
    system_prompt = UPLOAD_GENERATION_SYSTEM_PROMPT.format(count=count)

    client, model = _get_client()
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Reference material:\n{reference_text}"},
        ],
    )
    raw = completion.choices[0].message.content
    parsed = json.loads(raw)
    items = parsed.get("items", [])
    if not isinstance(items, list):
        raise ValueError("OpenAI response did not contain an 'items' list")
    return items
