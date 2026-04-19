import os
import json
import re
from typing import List
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL   = "llama3-70b-8192"


def _chat(messages: list, temperature: float = 0.4, max_tokens: int = 1500) -> str:
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


STUDY_SYSTEM = """You are StudyMate AI, an expert academic tutor helping college students.
Your responses must:
1. Directly answer the question using the provided context
2. Explain concepts clearly with examples
3. Highlight KEY POINTS using **bold**
4. End with a 💡 EXAM TIP or EXTRA INSIGHT section

If the context doesn't fully cover the question, say so honestly and provide what you know.
Be encouraging and student-friendly."""

def study_chat(query: str, context_chunks: List[str], chat_history: List[dict] = None) -> dict:
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No document context available."
    messages = [{"role": "system", "content": STUDY_SYSTEM}]
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    user_prompt = f"""DOCUMENT CONTEXT:\n{context}\n\nSTUDENT QUESTION: {query}\n\nProvide a comprehensive answer with key points highlighted and an exam tip."""
    messages.append({"role": "user", "content": user_prompt})
    answer = _chat(messages, temperature=0.35, max_tokens=1200)
    return {"answer": answer}


def generate_quiz(context_chunks, num_questions, difficulty, question_types, subject_name="the subject"):
    context   = "\n\n".join(context_chunks[:8])
    types_str = " and ".join(question_types)
    system = f"""You are an expert exam setter. Generate exactly {num_questions} {difficulty}-level
{types_str} questions based on the provided text.

Return ONLY valid JSON array. Each object:
{{
  "question_text": "...",
  "question_type": "mcq" or "short",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."] (only for mcq, else null),
  "correct_answer": "full correct answer or option letter like A",
  "explanation": "why this is correct",
  "difficulty": "{difficulty}",
  "topic_tag": "brief topic label"
}}

No extra text, no markdown, just the JSON array."""
    prompt = f"TEXT:\n{context}\n\nGenerate {num_questions} questions about {subject_name}."
    raw = _chat([
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt}
    ], temperature=0.5, max_tokens=2000)
    try:
        clean     = re.sub(r"```json|```", "", raw).strip()
        questions = json.loads(clean)
        if isinstance(questions, list):
            return questions[:num_questions]
    except Exception:
        pass
    return []


def evaluate_answers(questions: List[dict], user_answers: dict) -> dict:
    results = []
    correct = 0
    topics  = {}

    for q in questions:
        qid      = str(q["id"])
        user_ans = user_answers.get(qid, "").strip().lower()
        correct_ans = q["correct_answer"].strip().lower()

        is_correct = False
        if q["question_type"] == "mcq":
            if user_ans and (user_ans[0] == correct_ans[0] or user_ans == correct_ans):
                is_correct = True
        else:
            key_terms   = [w for w in correct_ans.split() if len(w) > 4]
            match_count = sum(1 for t in key_terms if t in user_ans)
            is_correct  = match_count >= max(1, len(key_terms) // 2)

        if is_correct:
            correct += 1

        tag = q.get("topic_tag", "General")
        topics.setdefault(tag, {"correct": 0, "total": 0})
        topics[tag]["total"] += 1
        if is_correct:
            topics[tag]["correct"] += 1

        results.append({
            "question_id":    q["id"],
            "question":       q["question_text"],
            "user_answer":    user_answers.get(qid, "Not answered"),
            "correct_answer": q["correct_answer"],
            "is_correct":     is_correct,
            "explanation":    q.get("explanation", ""),
        })

    total    = len(questions)
    pct      = round((correct / total) * 100, 1) if total else 0
    weak     = [tag for tag, v in topics.items() if v["correct"] / v["total"] < 0.5]
    feedback = (
        "🎉 Excellent work! Keep it up!"     if pct >= 80 else
        "👍 Good effort! Review weak areas." if pct >= 60 else
        "📚 Keep studying — you'll get there!"
    )

    return {
        "score":           pct,
        "total_questions": total,
        "correct_count":   correct,
        "percentage":      pct,
        "weak_areas":      weak,
        "feedback":        feedback,
        "detailed":        results,
    }


DSA_SYSTEM = """You are DSA Mentor — an expert Data Structures & Algorithms tutor for college students.

For concept questions: explain clearly with real-world analogy + complexity.
For coding problems: give problem statement, hint first, then full solution with comments.
For debugging: analyze the code and explain the fix.

Always:
- Show time/space complexity with Big-O
- Use Python/Java code examples
- Be encouraging — mistakes are learning!
- Tag the topic (e.g., #Arrays #DynamicProgramming #Graphs)
- If user solves a problem, celebrate and award virtual XP!"""


def dsa_chat(message: str, history: List[dict] = None) -> dict:
    messages = [{"role": "system", "content": DSA_SYSTEM}]
    if history:
        for msg in history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})
    answer  = _chat(messages, temperature=0.4, max_tokens=1500)
    topic   = _detect_dsa_topic(message + " " + answer)
    xp_gain = 10 if "solve" in message.lower() or "solution" in answer.lower() else 5
    return {"answer": answer, "topic": topic, "xp_gain": xp_gain}


DSA_TOPICS = {
    "array": "Arrays", "string": "Strings", "linked": "Linked List",
    "tree": "Trees", "graph": "Graphs", "dp": "Dynamic Programming",
    "dynamic": "Dynamic Programming", "sort": "Sorting", "search": "Searching",
    "stack": "Stack", "queue": "Queue", "heap": "Heap", "hash": "Hashing",
    "recursion": "Recursion", "greedy": "Greedy", "backtrack": "Backtracking",
    "binary": "Binary Search", "pointer": "Two Pointers",
}

def _detect_dsa_topic(text: str) -> str:
    lower = text.lower()
    for kw, topic in DSA_TOPICS.items():
        if kw in lower:
            return topic
    return "General DSA"


def generate_dsa_challenge(level: int) -> dict:
    tier   = "beginner" if level <= 3 else "intermediate" if level <= 7 else "advanced"
    prompt = f"""Generate a {tier} DSA daily challenge for a level-{level} student.
Return JSON only:
{{
  "title": "Challenge title",
  "description": "What to accomplish today",
  "topic": "topic name",
  "target_count": 3,
  "xp_reward": 50
}}"""
    raw = _chat([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=300)
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception:
        return {
            "title": "Array Challenge",
            "description": "Solve 3 array problems today",
            "topic": "Arrays",
            "target_count": 3,
            "xp_reward": 50,
        }


def generate_flashcards(context_chunks: List[str], num_cards: int, subject_name: str = "the subject") -> List[dict]:
    context = "\n\n".join(context_chunks[:10])
    system  = f"""You are an expert flashcard creator. Generate exactly {num_cards} high-quality flashcards from the provided text.

Return ONLY valid JSON array. Each object:
{{
  "front": "A clear question, term, or concept prompt",
  "back": "Concise but complete answer or explanation (2-4 sentences max)",
  "topic_tag": "brief topic label"
}}

Focus on key definitions, formulas, important relationships, and testable facts.
No extra text, no markdown, just the JSON array."""
    prompt = f"TEXT:\n{context}\n\nGenerate {num_cards} flashcards about {subject_name}."
    raw = _chat([
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt}
    ], temperature=0.4, max_tokens=2500)
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        cards = json.loads(clean)
        if isinstance(cards, list):
            return cards[:num_cards]
    except Exception:
        pass
    return []
