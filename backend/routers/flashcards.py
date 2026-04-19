from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from backend.models.database import get_db, User, Subject, FlashcardDeck, Flashcard
from backend.utils.auth      import get_current_user
from backend.services        import rag_service, llm_service

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


class DeckGenerateRequest(BaseModel):
    subject_id: int
    num_cards:  int = Field(10, ge=3, le=30)


class FlashcardUpdate(BaseModel):
    mastered: bool


@router.post("/generate", status_code=201)
def generate_deck(
    payload: DeckGenerateRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == payload.subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    index_ids = [d.vector_index_id for d in subj.documents if d.vector_index_id]
    if not index_ids:
        raise HTTPException(400, "Upload at least one document for this subject first")

    context   = rag_service.retrieve_context(f"key concepts definitions terms {subj.name}", index_ids, top_k=12)
    raw_cards = llm_service.generate_flashcards(context, payload.num_cards, subj.name)
    if not raw_cards:
        raise HTTPException(500, "Failed to generate flashcards — try again")

    deck = FlashcardDeck(
        user_id    = user.id,
        subject_id = payload.subject_id,
        title      = f"{subj.name} — Flashcards",
        card_count = len(raw_cards),
    )
    db.add(deck)
    db.flush()

    for c in raw_cards:
        db.add(Flashcard(
            deck_id   = deck.id,
            user_id   = user.id,
            front     = c.get("front", ""),
            back      = c.get("back", ""),
            topic_tag = c.get("topic_tag", ""),
        ))

    db.commit()
    db.refresh(deck)

    return {
        "id":         deck.id,
        "title":      deck.title,
        "card_count": deck.card_count,
        "cards":      [_card_out(c) for c in deck.cards],
    }


@router.get("/subject/{subject_id}")
def list_decks(
    subject_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    decks = (
        db.query(FlashcardDeck)
        .filter(FlashcardDeck.subject_id == subject_id, FlashcardDeck.user_id == user.id)
        .order_by(FlashcardDeck.created_at.desc())
        .all()
    )
    return [{"id": d.id, "title": d.title, "card_count": d.card_count, "created_at": d.created_at.isoformat()} for d in decks]


@router.get("/deck/{deck_id}")
def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user.id).first()
    if not deck:
        raise HTTPException(404, "Deck not found")
    return {
        "id":         deck.id,
        "title":      deck.title,
        "card_count": deck.card_count,
        "cards":      [_card_out(c) for c in deck.cards],
    }


@router.patch("/card/{card_id}")
def update_card(
    card_id: int,
    payload: FlashcardUpdate,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    card = db.query(Flashcard).filter(Flashcard.id == card_id, Flashcard.user_id == user.id).first()
    if not card:
        raise HTTPException(404, "Card not found")
    card.mastered = payload.mastered
    db.commit()
    return {"id": card.id, "mastered": card.mastered}


@router.delete("/deck/{deck_id}", status_code=204)
def delete_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user.id).first()
    if not deck:
        raise HTTPException(404, "Deck not found")
    db.delete(deck)
    db.commit()


def _card_out(c: Flashcard) -> dict:
    return {
        "id":        c.id,
        "front":     c.front,
        "back":      c.back,
        "topic_tag": c.topic_tag,
        "mastered":  c.mastered,
    }
