from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.models.database import get_db, User, Subject, Document, Quiz, QuizQuestion, QuizAttempt
from backend.models.schemas  import QuizGenerateRequest, QuizOut, QuizQuestionOut, QuizSubmitRequest, QuizResultOut
from backend.utils.auth      import get_current_user
from backend.services        import rag_service, llm_service

router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.post("/generate", response_model=QuizOut, status_code=201)
def generate_quiz(
    payload: QuizGenerateRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == payload.subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    # Get context chunks for quiz generation
    index_ids = [d.vector_index_id for d in subj.documents if d.vector_index_id]
    if not index_ids:
        raise HTTPException(400, "No documents uploaded for this subject yet")

    # Sample diverse chunks
    context = rag_service.retrieve_context(
        f"important concepts topics summary {subj.name}",
        index_ids,
        top_k=8,
    )

    # Generate questions via LLM
    raw_questions = llm_service.generate_quiz(
        context,
        payload.num_questions,
        payload.difficulty,
        payload.question_types,
        subj.name,
    )

    if not raw_questions:
        raise HTTPException(500, "Failed to generate questions — try again")

    # Persist quiz
    quiz = Quiz(
        user_id        = user.id,
        subject_id     = payload.subject_id,
        title          = f"{subj.name} — {payload.difficulty.title()} Quiz",
        difficulty     = payload.difficulty,
        question_count = len(raw_questions),
        time_limit     = payload.time_limit,
    )
    db.add(quiz)
    db.flush()

    for q in raw_questions:
        db.add(QuizQuestion(
            quiz_id        = quiz.id,
            question_text  = q.get("question_text", ""),
            question_type  = q.get("question_type", "mcq"),
            options        = q.get("options"),
            correct_answer = q.get("correct_answer", ""),
            explanation    = q.get("explanation", ""),
            difficulty     = q.get("difficulty", payload.difficulty),
            topic_tag      = q.get("topic_tag", ""),
        ))

    db.commit()
    db.refresh(quiz)

    return QuizOut(
        id         = quiz.id,
        title      = quiz.title,
        difficulty = quiz.difficulty,
        time_limit = quiz.time_limit,
        questions  = [QuizQuestionOut.model_validate(q) for q in quiz.questions],
    )


@router.post("/submit", response_model=QuizResultOut)
def submit_quiz(
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    quiz = db.query(Quiz).filter(Quiz.id == payload.quiz_id, Quiz.user_id == user.id).first()
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    # Prepare question data for evaluation
    questions = [
        {
            "id":             q.id,
            "question_text":  q.question_text,
            "question_type":  q.question_type,
            "correct_answer": q.correct_answer,
            "explanation":    q.explanation,
            "topic_tag":      q.topic_tag,
        }
        for q in quiz.questions
    ]

    result = llm_service.evaluate_answers(questions, payload.answers)

    # Persist attempt
    attempt = QuizAttempt(
        quiz_id         = quiz.id,
        user_id         = user.id,
        score           = result["percentage"],
        total_questions = result["total_questions"],
        time_taken_sec  = payload.time_taken_sec,
        answers         = payload.answers,
        weak_areas      = result["weak_areas"],
    )
    db.add(attempt)
    db.commit()

    return result


@router.get("/history")
def quiz_history(
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for a in attempts:
        result.append({
            "id":               a.id,
            "quiz_title":       a.quiz.title if a.quiz else "Unknown",
            "score":            a.score,
            "total_questions":  a.total_questions,
            "time_taken_sec":   a.time_taken_sec,
            "completed_at":     a.completed_at.isoformat(),
            "weak_areas":       a.weak_areas or [],
        })
    return result


@router.get("/stats")
def quiz_stats(
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).all()
    if not attempts:
        return {"total_quizzes": 0, "avg_score": 0, "best_score": 0, "weak_areas": []}

    scores   = [a.score for a in attempts]
    all_weak = []
    for a in attempts:
        if a.weak_areas:
            all_weak.extend(a.weak_areas)

    # Count most frequent weak areas
    from collections import Counter
    weak_counts = Counter(all_weak).most_common(5)

    return {
        "total_quizzes": len(attempts),
        "avg_score":     round(sum(scores) / len(scores), 1),
        "best_score":    round(max(scores), 1),
        "weak_areas":    [w[0] for w in weak_counts],
    }
