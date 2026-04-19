from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

from backend.models.database import get_db, User, Subject, Note
from backend.utils.auth      import get_current_user

router = APIRouter(prefix="/notes", tags=["Notes"])


class NoteCreate(BaseModel):
    subject_id: int
    title:      str          = Field(..., min_length=1, max_length=200)
    content:    Optional[str] = ""
    color:      Optional[str] = "#fef3c7"


class NoteUpdate(BaseModel):
    title:   Optional[str] = None
    content: Optional[str] = None
    color:   Optional[str] = None


def _note_out(n: Note) -> dict:
    return {
        "id":         n.id,
        "subject_id": n.subject_id,
        "title":      n.title,
        "content":    n.content,
        "color":      n.color,
        "updated_at": n.updated_at.isoformat(),
    }


@router.post("/", status_code=201)
def create_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == payload.subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")
    note = Note(
        user_id    = user.id,
        subject_id = payload.subject_id,
        title      = payload.title,
        content    = payload.content,
        color      = payload.color,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_out(note)


@router.get("/subject/{subject_id}")
def list_notes(
    subject_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    notes = (
        db.query(Note)
        .filter(Note.subject_id == subject_id, Note.user_id == user.id)
        .order_by(Note.updated_at.desc())
        .all()
    )
    return [_note_out(n) for n in notes]


@router.put("/{note_id}")
def update_note(
    note_id: int,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    if payload.title   is not None: note.title   = payload.title
    if payload.content is not None: note.content = payload.content
    if payload.color   is not None: note.color   = payload.color
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return _note_out(note)


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()
