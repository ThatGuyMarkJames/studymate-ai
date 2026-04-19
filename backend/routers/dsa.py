from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta

from backend.models.database import get_db, User, DSAProgress, DSAChatHistory, DSAChallenge
from backend.models.schemas  import DSAChatRequest, DSAProgressOut
from backend.utils.auth      import get_current_user
from backend.services        import llm_service

router = APIRouter(prefix="/dsa", tags=["DSA Practice"])

XP_PER_LEVEL = 200  # XP needed per level


def _get_or_create_progress(user_id: int, db: Session) -> DSAProgress:
    prog = db.query(DSAProgress).filter(DSAProgress.user_id == user_id).first()
    if not prog:
        prog = DSAProgress(user_id=user_id)
        db.add(prog)
        db.commit()
        db.refresh(prog)
    return prog


def _update_streak(prog: DSAProgress, db: Session):
    today = date.today()
    if prog.last_activity == today:
        return
    if prog.last_activity == today - timedelta(days=1):
        prog.streak_days += 1
    else:
        prog.streak_days = 1
    prog.last_activity = today
    db.commit()


def _award_xp(prog: DSAProgress, xp: int, db: Session):
    prog.xp_points += xp
    prog.level      = 1 + prog.xp_points // XP_PER_LEVEL
    db.commit()



@router.post("/chat")
def dsa_chat(
    payload: DSAChatRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    prog = _get_or_create_progress(user.id, db)

    # Get recent history
    history_rows = (
        db.query(DSAChatHistory)
        .filter(DSAChatHistory.user_id == user.id)
        .order_by(DSAChatHistory.created_at.desc())
        .limit(12)
        .all()
    )
    history = [{"role": r.role, "content": r.content} for r in reversed(history_rows)]

    result  = llm_service.dsa_chat(payload.message, history)

    # Persist messages
    db.add(DSAChatHistory(user_id=user.id, role="user",      content=payload.message, topic_tag=result["topic"]))
    db.add(DSAChatHistory(user_id=user.id, role="assistant", content=result["answer"], topic_tag=result["topic"]))

    # Award XP + update streak
    _update_streak(prog, db)
    _award_xp(prog, result.get("xp_gain", 5), db)

    # Increment problems_solved when a coding solution is involved
    if "solution" in result["answer"].lower() or "solve" in payload.message.lower():
        prog.problems_solved += 1
        db.commit()

    # Check active challenges
    challenge_done = _check_challenges(user.id, result["topic"], prog, db)

    return {
        "answer":          result["answer"],
        "topic":           result["topic"],
        "xp_gained":       result.get("xp_gain", 5),
        "total_xp":        prog.xp_points,
        "level":           prog.level,
        "challenge_done":  challenge_done,
    }


def _check_challenges(user_id: int, topic: str, prog: DSAProgress, db: Session) -> bool:
    """Increment challenge progress if topic matches. Returns True if challenge completed."""
    challenge = (
        db.query(DSAChallenge)
        .filter(
            DSAChallenge.user_id   == user_id,
            DSAChallenge.completed == False,
            DSAChallenge.expires_at >= date.today(),
        )
        .first()
    )
    if not challenge:
        return False

    if topic.lower() in (challenge.topic or "").lower() or challenge.topic == "General DSA":
        challenge.current_count += 1
        if challenge.current_count >= challenge.target_count:
            challenge.completed   = True
            prog.challenges_done += 1
            _award_xp(prog, challenge.xp_reward, db)
            db.commit()
            return True
        db.commit()
    return False



@router.get("/progress", response_model=DSAProgressOut)
def get_progress(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prog = _get_or_create_progress(user.id, db)
    return DSAProgressOut(
        xp_points       = prog.xp_points,
        level           = prog.level,
        streak_days     = prog.streak_days,
        problems_solved = prog.problems_solved,
        challenges_done = prog.challenges_done,
        next_level_xp   = (prog.level * XP_PER_LEVEL) - prog.xp_points,
    )


@router.get("/chat/history")
def get_dsa_history(
    limit: int  = 50,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    rows = (
        db.query(DSAChatHistory)
        .filter(DSAChatHistory.user_id == user.id)
        .order_by(DSAChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": r.role, "content": r.content, "topic": r.topic_tag, "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/challenge/new")
def new_challenge(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prog = _get_or_create_progress(user.id, db)

    # Expire old challenges
    db.query(DSAChallenge).filter(
        DSAChallenge.user_id == user.id,
        DSAChallenge.completed == False,
    ).delete()

    # Generate new one
    data = llm_service.generate_dsa_challenge(prog.level)
    ch   = DSAChallenge(
        user_id        = user.id,
        challenge_text = data.get("description", "Solve 3 DSA problems"),
        target_count   = data.get("target_count", 3),
        topic          = data.get("topic", "General DSA"),
        xp_reward      = data.get("xp_reward", 50),
        expires_at     = date.today() + timedelta(days=1),
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    return {
        "id":             ch.id,
        "title":          data.get("title", "Daily Challenge"),
        "description":    ch.challenge_text,
        "topic":          ch.topic,
        "target_count":   ch.target_count,
        "current_count":  ch.current_count,
        "xp_reward":      ch.xp_reward,
        "expires_at":     str(ch.expires_at),
    }


@router.get("/challenge/active")
def get_active_challenge(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ch = (
        db.query(DSAChallenge)
        .filter(
            DSAChallenge.user_id   == user.id,
            DSAChallenge.completed == False,
            DSAChallenge.expires_at >= date.today(),
        )
        .first()
    )
    if not ch:
        return None
    return {
        "id":            ch.id,
        "description":   ch.challenge_text,
        "topic":         ch.topic,
        "target_count":  ch.target_count,
        "current_count": ch.current_count,
        "xp_reward":     ch.xp_reward,
        "expires_at":    str(ch.expires_at),
    }


@router.delete("/chat/history", status_code=204)
def clear_dsa_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(DSAChatHistory).filter(DSAChatHistory.user_id == user.id).delete()
    db.commit()
