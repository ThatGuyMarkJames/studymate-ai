from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime



class UserCreate(BaseModel):
    username:  str       = Field(..., min_length=3, max_length=50)
    email:     EmailStr
    full_name: Optional[str] = None
    password:  str       = Field(..., min_length=6)

class UserLogin(BaseModel):
    email:    str
    password: str

class UserOut(BaseModel):
    id:         int
    username:   str
    email:      str
    full_name:  Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut



class SubjectCreate(BaseModel):
    name:        str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color:       Optional[str] = "#6366f1"

class SubjectOut(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    color:       str
    created_at:  datetime
    doc_count:   Optional[int] = 0
    class Config:
        from_attributes = True



class DocumentOut(BaseModel):
    id:            int
    original_name: str
    file_type:     Optional[str]
    file_size:     Optional[int]
    chunk_count:   int
    created_at:    datetime
    class Config:
        from_attributes = True



class ChatRequest(BaseModel):
    subject_id: int
    message:    str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    answer:    str
    sources:   Optional[List[str]] = []
    tips:      Optional[str] = None

class ChatMessageOut(BaseModel):
    id:         int
    role:       str
    content:    str
    sources:    Optional[Any]
    created_at: datetime
    class Config:
        from_attributes = True



class QuizGenerateRequest(BaseModel):
    subject_id:     int
    num_questions:  int  = Field(5,  ge=1, le=20)
    difficulty:     str  = Field("medium", pattern="^(easy|medium|hard)$")
    question_types: List[str] = ["mcq"]
    time_limit:     int  = 0

class QuizQuestionOut(BaseModel):
    id:            int
    question_text: str
    question_type: str
    options:       Optional[Any]
    difficulty:    str
    topic_tag:     Optional[str]
    class Config:
        from_attributes = True

class QuizOut(BaseModel):
    id:        int
    title:     Optional[str]
    difficulty: str
    time_limit: int
    questions: List[QuizQuestionOut]
    class Config:
        from_attributes = True

class QuizSubmitRequest(BaseModel):
    quiz_id:       int
    answers:       dict          # {question_id: answer_text}
    time_taken_sec: int = 0

class QuizResultOut(BaseModel):
    score:           float
    total_questions: int
    correct_count:   int
    percentage:      float
    weak_areas:      List[str]
    feedback:        str
    detailed:        List[dict]



class DSAChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

class DSAProgressOut(BaseModel):
    xp_points:       int
    level:           int
    streak_days:     int
    problems_solved: int
    challenges_done: int
    next_level_xp:   int
    class Config:
        from_attributes = True
