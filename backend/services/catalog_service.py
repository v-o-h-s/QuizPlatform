import re

from fastapi import HTTPException, status
from postgrest import AsyncPostgrestClient

from ..schemas import (
    AdminQuizDetailOut,
    AdminQuestionIn,
    ModuleCreateIn,
    ModuleOut,
    ModuleUpdateIn,
    ModuleWithQuizzesOut,
    QuestionOut,
    QuizDetailOut,
    QuizSummaryOut,
    QuizUpsertIn,
)

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
CHOICE_KEYS = ["choice_a", "choice_b", "choice_c", "choice_d", "choice_e", "choice_f"]
IMAGE_KEYS = [
    "choice_a_image_url",
    "choice_b_image_url",
    "choice_c_image_url",
    "choice_d_image_url",
    "choice_e_image_url",
    "choice_f_image_url",
]


def _normalize_module_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _serialize_quiz_summary(
    quiz_id: str,
    display_name: str,
    question_count: int,
    module_id: str | None,
    module_display_name: str | None,
) -> QuizSummaryOut:
    return QuizSummaryOut(
        id=quiz_id,
        display_name=display_name,
        module_id=module_id,
        module_display_name=module_display_name,
        question_count=int(question_count),
    )


def _serialize_quiz_detail(quiz: dict, module: dict | None, questions: list[dict]) -> QuizDetailOut:
    return QuizDetailOut(
        id=quiz["id"],
        display_name=quiz["display_name"],
        module_id=module["id"] if module else None,
        module_display_name=module["display_name"] if module else None,
        questions=[QuestionOut.model_validate(question) for question in questions],
    )


def _serialize_admin_quiz_detail(quiz: dict, module: dict | None, questions: list[dict]) -> AdminQuizDetailOut:
    return AdminQuizDetailOut(
        id=quiz["id"],
        display_name=quiz["display_name"],
        module_id=module["id"] if module else None,
        module_display_name=module["display_name"] if module else None,
        questions=[
            AdminQuestionIn(
                question_number=question["question_number"],
                question_text=question["question_text"],
                question_image_url=question.get("question_image_url"),
                choice_a=question["choice_a"],
                choice_a_image_url=question.get("choice_a_image_url"),
                choice_b=question["choice_b"],
                choice_b_image_url=question.get("choice_b_image_url"),
                choice_c=question.get("choice_c"),
                choice_c_image_url=question.get("choice_c_image_url"),
                choice_d=question.get("choice_d"),
                choice_d_image_url=question.get("choice_d_image_url"),
                choice_e=question.get("choice_e"),
                choice_e_image_url=question.get("choice_e_image_url"),
                choice_f=question.get("choice_f"),
                choice_f_image_url=question.get("choice_f_image_url"),
                correct_answer=question["correct_answer"],
                difficulty=question.get("difficulty"),
            )
            for question in questions
        ],
    )


def _normalize_question_payload(question: AdminQuestionIn) -> dict[str, str | int | None]:
    normalized = question.model_dump()
    normalized["question_text"] = question.question_text.strip()
    normalized["question_image_url"] = _clean_optional(question.question_image_url)
    normalized["correct_answer"] = question.correct_answer.strip().lower()
    normalized["difficulty"] = _clean_optional(question.difficulty)

    for key in [*CHOICE_KEYS, *IMAGE_KEYS]:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = value.strip() or None

    if not normalized["question_text"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Every question must include question_text.",
        )

    if not normalized["choice_a"] or not normalized["choice_b"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each question must include choices a and b.",
        )

    if normalized["correct_answer"] not in VALID_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correct_answer must be one of a, b, c, d, e, or f.",
        )

    difficulty = normalized["difficulty"]
    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="difficulty must be easy, medium, hard, or null.",
        )

    required_choice_key = f"choice_{normalized['correct_answer']}"
    if not normalized.get(required_choice_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"correct_answer '{normalized['correct_answer']}' must point to a non-empty choice.",
        )

    return normalized


def _normalize_quiz_payload(payload: QuizUpsertIn) -> tuple[str, str, str | None, list[dict[str, str | int | None]]]:
    quiz_id = payload.id.strip()
    display_name = payload.display_name.strip()
    module_id = _clean_optional(payload.module_id)

    if not quiz_id or not display_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz id and display_name are required.",
        )

    seen_numbers: set[int] = set()
    questions: list[dict[str, str | int | None]] = []

    for question in payload.questions:
        if question.question_number in seen_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate question_number {question.question_number} in quiz payload.",
            )
        seen_numbers.add(question.question_number)
        questions.append(_normalize_question_payload(question))

    ordered_numbers = sorted(seen_numbers)
    expected = list(range(1, len(ordered_numbers) + 1))
    if ordered_numbers != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz questions must be numbered contiguously starting at 1.",
        )

    return quiz_id, display_name, module_id, questions


async def _require_module(db: AsyncPostgrestClient, module_id: str) -> dict:
    response = await db.table("modules").select("*").eq("id", module_id).maybe_single().execute()
    module = response.data
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    return module


async def list_modules(db: AsyncPostgrestClient) -> list[ModuleOut]:
    modules_resp = await db.table("modules").select("*").order("display_name").execute()
    modules = modules_resp.data

    quizzes_resp = await db.table("quizzes").select("id, module_id").execute()
    quizzes = quizzes_resp.data

    counts = {}
    for q in quizzes:
        m_id = q.get("module_id")
        if m_id:
            counts[m_id] = counts.get(m_id, 0) + 1

    return [
        ModuleOut(
            id=m["id"],
            display_name=m["display_name"],
            description=m.get("description"),
            quiz_count=counts.get(m["id"], 0),
        )
        for m in modules
    ]


async def create_module(db: AsyncPostgrestClient, payload: ModuleCreateIn) -> ModuleOut:
    module_id = _normalize_module_id(payload.id)
    if not module_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module id is invalid.")

    existing_resp = await db.table("modules").select("id").eq("id", module_id).maybe_single().execute()
    if existing_resp is not None and existing_resp.data is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module id already exists.")

    data = {
        "id": module_id,
        "display_name": payload.display_name.strip(),
        "description": _clean_optional(payload.description),
    }
    await db.table("modules").insert(data).execute()
    return ModuleOut(id=data["id"], display_name=data["display_name"], description=data["description"], quiz_count=0)


async def update_module(db: AsyncPostgrestClient, module_id: str, payload: ModuleUpdateIn) -> ModuleOut:
    module_resp = await db.table("modules").select("*").eq("id", module_id).maybe_single().execute()
    if module_resp.data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    data = {
        "display_name": payload.display_name.strip(),
        "description": _clean_optional(payload.description),
    }
    await db.table("modules").update(data).eq("id", module_id).execute()
    
    quizzes_resp = await db.table("quizzes").select("id", count="exact").eq("module_id", module_id).execute()
    quiz_count = quizzes_resp.count if quizzes_resp.count else 0
    
    return ModuleOut(
        id=module_id,
        display_name=data["display_name"],
        description=data["description"],
        quiz_count=quiz_count,
    )


async def list_quizzes(db: AsyncPostgrestClient) -> list[QuizSummaryOut]:
    quizzes_resp = await db.table("quizzes").select("*, modules(*)").execute()
    quizzes = quizzes_resp.data

    questions_resp = await db.table("questions").select("quiz_id", count="exact").execute()
    
    # We need a group by to get counts per quiz, but postgrest python doesn't support complex group by easily
    # So fetch all questions quiz_id and count
    all_questions_resp = await db.table("questions").select("quiz_id").execute()
    
    counts = {}
    for q in all_questions_resp.data:
        q_id = q["quiz_id"]
        counts[q_id] = counts.get(q_id, 0) + 1
        
    def _sort_key(quiz):
        module = quiz.get("modules")
        mod_name = module.get("display_name", "") if module else "zzz" # Nulls last
        return (mod_name, quiz["display_name"])

    quizzes.sort(key=_sort_key)

    return [
        _serialize_quiz_summary(
            quiz["id"],
            quiz["display_name"],
            counts.get(quiz["id"], 0),
            quiz.get("module_id"),
            quiz.get("modules", {}).get("display_name") if quiz.get("modules") else None,
        )
        for quiz in quizzes
        if counts.get(quiz["id"], 0) > 0
    ]


async def list_modules_with_quizzes(db: AsyncPostgrestClient) -> list[ModuleWithQuizzesOut]:
    modules = await list_modules(db)
    quizzes = await list_quizzes(db)

    grouped: dict[str, list[QuizSummaryOut]] = {module.id: [] for module in modules}
    ungrouped: list[QuizSummaryOut] = []

    for quiz in quizzes:
        if quiz.module_id and quiz.module_id in grouped:
            grouped[quiz.module_id].append(quiz)
        else:
            ungrouped.append(quiz)

    payload = [
        ModuleWithQuizzesOut(
            id=module.id,
            display_name=module.display_name,
            description=module.description,
            quizzes=grouped[module.id],
        )
        for module in modules
    ]

    if ungrouped:
        payload.append(
            ModuleWithQuizzesOut(
                id="ungrouped",
                display_name="Ungrouped",
                description="Quizzes not assigned to a module yet.",
                quizzes=ungrouped,
            )
        )

    return payload


async def get_quiz_detail(db: AsyncPostgrestClient, quiz_id: str) -> QuizDetailOut:
    quiz_resp = await db.table("quizzes").select("*, modules(*), questions(*)").eq("id", quiz_id).maybe_single().execute()
    quiz = quiz_resp.data
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    
    questions = sorted(quiz.get("questions", []), key=lambda q: q["question_number"])
    return _serialize_quiz_detail(quiz, quiz.get("modules"), questions)


async def get_admin_quiz_detail(db: AsyncPostgrestClient, quiz_id: str) -> AdminQuizDetailOut:
    quiz_resp = await db.table("quizzes").select("*, modules(*), questions(*)").eq("id", quiz_id).maybe_single().execute()
    quiz = quiz_resp.data
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    
    questions = sorted(quiz.get("questions", []), key=lambda q: q["question_number"])
    return _serialize_admin_quiz_detail(quiz, quiz.get("modules"), questions)


async def create_quiz(db: AsyncPostgrestClient, payload: QuizUpsertIn) -> AdminQuizDetailOut:
    quiz_id, display_name, module_id, questions = _normalize_quiz_payload(payload)

    existing_resp = await db.table("quizzes").select("id").eq("id", quiz_id).maybe_single().execute()
    if existing_resp is not None and existing_resp.data is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz id already exists.")

    if module_id:
        await _require_module(db, module_id)

    quiz_data = {"id": quiz_id, "display_name": display_name, "module_id": module_id}
    await db.table("quizzes").insert(quiz_data).execute()

    for q in questions:
        q["quiz_id"] = quiz_id
    
    if questions:
        await db.table("questions").insert(questions).execute()

    return await get_admin_quiz_detail(db, quiz_id)


async def update_quiz(db: AsyncPostgrestClient, quiz_id: str, payload: QuizUpsertIn) -> AdminQuizDetailOut:
    normalized_id, display_name, module_id, questions = _normalize_quiz_payload(payload)
    if normalized_id != quiz_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz id in the body must match the URL.",
        )

    quiz_resp = await db.table("quizzes").select("*, questions(*)").eq("id", quiz_id).maybe_single().execute()
    quiz = quiz_resp.data
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    if module_id:
        await _require_module(db, module_id)

    answers_resp = await db.table("answers").select("id", count="exact").eq("quiz_id", quiz_id).limit(1).execute()
    answers_count = answers_resp.count if answers_resp.count else 0
    
    existing_questions = quiz.get("questions", [])
    existing_by_number = {q["question_number"]: q for q in existing_questions}
    incoming_numbers = {int(q["question_number"]) for q in questions}
    existing_numbers = set(existing_by_number.keys())

    if answers_count and incoming_numbers != existing_numbers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This quiz already has answer history, so you can only edit existing question content, not add or remove question numbers.",
        )

    await db.table("quizzes").update({"display_name": display_name, "module_id": module_id}).eq("id", quiz_id).execute()

    # Update questions
    for q_payload in questions:
        q_num = int(q_payload["question_number"])
        q_payload["quiz_id"] = quiz_id
        if q_num not in existing_by_number:
            await db.table("questions").insert(q_payload).execute()
        else:
            await db.table("questions").update(q_payload).eq("quiz_id", quiz_id).eq("question_number", q_num).execute()

    if not answers_count:
        removable_numbers = existing_numbers - incoming_numbers
        if removable_numbers:
            await db.table("questions").delete().eq("quiz_id", quiz_id).in_("question_number", list(removable_numbers)).execute()

    return await get_admin_quiz_detail(db, quiz_id)
