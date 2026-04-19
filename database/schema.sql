-- StudyMate AI - MySQL Schema
-- Run this file to set up the complete database

CREATE DATABASE IF NOT EXISTS studymate_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE studymate_db;

-- ─────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    email       VARCHAR(120) NOT NULL UNIQUE,
    full_name   VARCHAR(100),
    password    VARCHAR(255) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login  DATETIME,
    is_active   BOOLEAN DEFAULT TRUE,
    INDEX idx_email (email),
    INDEX idx_username (username)
);

-- ─────────────────────────────────────────
-- SUBJECTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    color       VARCHAR(7) DEFAULT '#6366f1',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_subjects (user_id)
);

-- ─────────────────────────────────────────
-- DOCUMENTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    subject_id      INT NOT NULL,
    filename        VARCHAR(255) NOT NULL,
    original_name   VARCHAR(255) NOT NULL,
    file_type       VARCHAR(10),
    file_size       INT,
    chunk_count     INT DEFAULT 0,
    vector_index_id VARCHAR(100),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    INDEX idx_subject_docs (subject_id),
    INDEX idx_user_docs (user_id)
);

-- ─────────────────────────────────────────
-- CHAT HISTORY
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    subject_id  INT,
    role        ENUM('user','assistant') NOT NULL,
    content     TEXT NOT NULL,
    sources     JSON,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
    INDEX idx_chat_user    (user_id),
    INDEX idx_chat_subject (subject_id),
    INDEX idx_chat_created (created_at)
);

-- ─────────────────────────────────────────
-- QUIZZES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quizzes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    subject_id  INT,
    title       VARCHAR(200),
    difficulty  ENUM('easy','medium','hard') DEFAULT 'medium',
    question_count INT DEFAULT 5,
    time_limit  INT DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    quiz_id         INT NOT NULL,
    question_text   TEXT NOT NULL,
    question_type   ENUM('mcq','short') DEFAULT 'mcq',
    options         JSON,
    correct_answer  TEXT NOT NULL,
    explanation     TEXT,
    difficulty      ENUM('easy','medium','hard') DEFAULT 'medium',
    topic_tag       VARCHAR(100),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    quiz_id         INT NOT NULL,
    user_id         INT NOT NULL,
    score           FLOAT DEFAULT 0,
    total_questions INT DEFAULT 0,
    time_taken_sec  INT DEFAULT 0,
    answers         JSON,
    weak_areas      JSON,
    completed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)   ON DELETE CASCADE,
    INDEX idx_attempt_user (user_id)
);

-- ─────────────────────────────────────────
-- DSA PROGRESS & GAMIFICATION
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsa_progress (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL UNIQUE,
    xp_points       INT DEFAULT 0,
    level           INT DEFAULT 1,
    streak_days     INT DEFAULT 0,
    last_activity   DATE,
    problems_solved INT DEFAULT 0,
    challenges_done INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dsa_chat_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    role        ENUM('user','assistant') NOT NULL,
    content     TEXT NOT NULL,
    topic_tag   VARCHAR(100),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_dsa_user (user_id)
);

CREATE TABLE IF NOT EXISTS dsa_challenges (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    challenge_text  TEXT,
    target_count    INT DEFAULT 3,
    current_count   INT DEFAULT 0,
    topic           VARCHAR(50),
    xp_reward       INT DEFAULT 50,
    completed       BOOLEAN DEFAULT FALSE,
    expires_at      DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
