from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os

from backend.models.database  import get_db, User, Subject, Document, ChatHistory
from backend.models.schemas   import SubjectCreate, SubjectOut, DocumentOut, ChatRequest, ChatMessageOut
from backend.utils.auth       import get_current_user
from backend.services         import rag_service, llm_service

router = APIRouter(prefix="/study", tags=["Study"])

MAX_FILE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 10))



@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    subj = Subject(
        user_id     = user.id,
        name        = payload.name,
        description = payload.description,
        color       = payload.color or "#6366f1",
    )
    db.add(subj)
    db.commit()
    db.refresh(subj)
    out      = SubjectOut.model_validate(subj)
    out.doc_count = 0
    return out


@router.get("/subjects", response_model=List[SubjectOut])
def list_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subjects = db.query(Subject).filter(Subject.user_id == user.id).order_by(Subject.created_at.desc()).all()
    result   = []
    for s in subjects:
        out = SubjectOut.model_validate(s)
        out.doc_count = len(s.documents)
        result.append(out)
    return result


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(
    subject_id: int,
    db: Session  = Depends(get_db),
    user: User   = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")
    # Clean up vector indexes
    for doc in subj.documents:
        if doc.vector_index_id:
            rag_service.delete_index(doc.vector_index_id)
    db.delete(subj)
    db.commit()



@router.post("/subjects/{subject_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    subject_id: int,
    file: UploadFile = File(...),
    db: Session   = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "txt"):
        raise HTTPException(400, "Only PDF and TXT files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {MAX_FILE_MB}MB limit")

    # Save & process
    filename, file_type = rag_service.save_upload(content, file.filename, user.id)
    chunks, index_id    = rag_service.process_document(filename, file_type)

    doc = Document(
        user_id         = user.id,
        subject_id      = subject_id,
        filename        = filename,
        original_name   = file.filename,
        file_type       = file_type,
        file_size       = len(content),
        chunk_count     = len(chunks),
        vector_index_id = index_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/subjects/{subject_id}/documents", response_model=List[DocumentOut])
def list_documents(
    subject_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")
    return subj.documents


@router.delete("/subjects/{subject_id}/documents/{doc_id}", status_code=204)
def delete_document(
    subject_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.subject_id == subject_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.vector_index_id:
        rag_service.delete_index(doc.vector_index_id)
    db.delete(doc)
    db.commit()



@router.post("/chat")
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    subj = db.query(Subject).filter(Subject.id == payload.subject_id, Subject.user_id == user.id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    # Get vector index IDs for all documents in subject
    index_ids = [d.vector_index_id for d in subj.documents if d.vector_index_id]

    # Retrieve relevant chunks
    context = rag_service.retrieve_context(payload.message, index_ids)

    # Get recent chat history
    history_rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user.id, ChatHistory.subject_id == payload.subject_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(10)
        .all()
    )
    history = [{"role": r.role, "content": r.content} for r in reversed(history_rows)]

    # Call LLM
    result  = llm_service.study_chat(payload.message, context, history)
    sources = [c[:120] + "…" for c in context] if context else []

    # Persist messages
    db.add(ChatHistory(user_id=user.id, subject_id=payload.subject_id, role="user",      content=payload.message))
    db.add(ChatHistory(user_id=user.id, subject_id=payload.subject_id, role="assistant", content=result["answer"], sources=sources))
    db.commit()

    return {"answer": result["answer"], "sources": sources}


@router.get("/chat/{subject_id}/history", response_model=List[ChatMessageOut])
def get_chat_history(
    subject_id: int,
    limit: int  = 50,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user.id, ChatHistory.subject_id == subject_id)
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )


@router.delete("/chat/{subject_id}/history", status_code=204)
def clear_chat_history(
    subject_id: int,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user),
):
    db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.subject_id == subject_id,
    ).delete()
    db.commit()
