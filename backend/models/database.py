from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Boolean, Float, JSON, Enum, Date, ForeignKey, func
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

import urllib.parse

load_dotenv()

# Database Connection Strings
MYSQL_URL = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")

if MYSQL_URL:
    # Use direct URL if provided by cloud platform (Railway/Render)
    if MYSQL_URL.startswith("mysql://"):
        DATABASE_URL = MYSQL_URL.replace("mysql://", "mysql+pymysql://", 1)
    else:
        DATABASE_URL = MYSQL_URL
else:
    # Build from components (Local development)
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = os.getenv("DB_PORT", "3306")
    DB_USER     = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME     = os.getenv("DB_NAME", "studymate_db")

    safe_password = urllib.parse.quote_plus(DB_PASSWORD)
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50),  unique=True, nullable=False)
    email      = Column(String(120), unique=True, nullable=False)
    full_name  = Column(String(100))
    password   = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active  = Column(Boolean, default=True)

    subjects        = relationship("Subject",       back_populates="user", cascade="all, delete")
    chat_history    = relationship("ChatHistory",   back_populates="user", cascade="all, delete")
    quiz_attempts   = relationship("QuizAttempt",   back_populates="user", cascade="all, delete")
    dsa_progress    = relationship("DSAProgress",   back_populates="user", uselist=False, cascade="all, delete")
    notes           = relationship("Note",          back_populates="user", cascade="all, delete")
    flashcard_decks = relationship("FlashcardDeck", back_populates="user", cascade="all, delete")


class Subject(Base):
    __tablename__ = "subjects"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name        = Column(String(100), nullable=False)
    description = Column(Text)
    color       = Column(String(7), default="#6366f1")
    created_at  = Column(DateTime(timezone=True), default=func.now())

    user            = relationship("User",     back_populates="subjects")
    documents       = relationship("Document", back_populates="subject", cascade="all, delete")
    chats           = relationship("ChatHistory", back_populates="subject")
    notes           = relationship("Note",     back_populates="subject", cascade="all, delete")
    flashcard_decks = relationship("FlashcardDeck", back_populates="subject", cascade="all, delete")


class Document(Base):
    __tablename__ = "documents"
    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    subject_id      = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    filename        = Column(String(255), nullable=False)
    original_name   = Column(String(255), nullable=False)
    file_type       = Column(String(10))
    file_size       = Column(Integer)
    chunk_count     = Column(Integer, default=0)
    vector_index_id = Column(String(100))
    created_at      = Column(DateTime(timezone=True), default=func.now())

    subject = relationship("Subject", back_populates="documents")


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    role       = Column(Enum("user", "assistant"), nullable=False)
    content    = Column(Text, nullable=False)
    sources    = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user    = relationship("User",    back_populates="chat_history")
    subject = relationship("Subject", back_populates="chats")


class Quiz(Base):
    __tablename__ = "quizzes"
    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    subject_id     = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    title          = Column(String(200))
    difficulty     = Column(Enum("easy", "medium", "hard"), default="medium")
    question_count = Column(Integer, default=5)
    time_limit     = Column(Integer, default=0)
    created_at     = Column(DateTime(timezone=True), default=func.now())

    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete")
    attempts  = relationship("QuizAttempt",  back_populates="quiz", cascade="all, delete")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id             = Column(Integer, primary_key=True)
    quiz_id        = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text  = Column(Text, nullable=False)
    question_type  = Column(Enum("mcq", "short"), default="mcq")
    options        = Column(JSON)
    correct_answer = Column(Text, nullable=False)
    explanation    = Column(Text)
    difficulty     = Column(Enum("easy", "medium", "hard"), default="medium")
    topic_tag      = Column(String(100))

    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id              = Column(Integer, primary_key=True)
    quiz_id         = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
    score           = Column(Float, default=0)
    total_questions = Column(Integer, default=0)
    time_taken_sec  = Column(Integer, default=0)
    answers         = Column(JSON)
    weak_areas      = Column(JSON)
    completed_at    = Column(DateTime(timezone=True), default=func.now())

    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", back_populates="quiz_attempts")


class DSAProgress(Base):
    __tablename__ = "dsa_progress"
    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    xp_points       = Column(Integer, default=0)
    level           = Column(Integer, default=1)
    streak_days     = Column(Integer, default=0)
    last_activity   = Column(Date, nullable=True)
    problems_solved = Column(Integer, default=0)
    challenges_done = Column(Integer, default=0)

    user = relationship("User", back_populates="dsa_progress")


class DSAChatHistory(Base):
    __tablename__ = "dsa_chat_history"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role       = Column(Enum("user", "assistant"), nullable=False)
    content    = Column(Text, nullable=False)
    topic_tag  = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=func.now())


class DSAChallenge(Base):
    __tablename__ = "dsa_challenges"
    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_text = Column(Text)
    target_count   = Column(Integer, default=3)
    current_count  = Column(Integer, default=0)
    topic          = Column(String(50))
    xp_reward      = Column(Integer, default=50)
    completed      = Column(Boolean, default=False)
    expires_at     = Column(Date)
    created_at     = Column(DateTime(timezone=True), default=func.now())


class Note(Base):
    __tablename__ = "notes"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    title      = Column(String(200), nullable=False)
    content    = Column(Text)
    color      = Column(String(7), default="#fef3c7")
    updated_at = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())

    user    = relationship("User",    back_populates="notes")
    subject = relationship("Subject", back_populates="notes")


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    title      = Column(String(200), nullable=False)
    card_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user    = relationship("User",    back_populates="flashcard_decks")
    subject = relationship("Subject", back_populates="flashcard_decks")
    cards   = relationship("Flashcard", back_populates="deck", cascade="all, delete")


class Flashcard(Base):
    __tablename__ = "flashcards"
    id        = Column(Integer, primary_key=True)
    deck_id   = Column(Integer, ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False)
    user_id   = Column(Integer, ForeignKey("users.id",           ondelete="CASCADE"), nullable=False)
    front     = Column(Text, nullable=False)
    back      = Column(Text, nullable=False)
    topic_tag = Column(String(100))
    mastered  = Column(Boolean, default=False)

    deck = relationship("FlashcardDeck", back_populates="cards")
