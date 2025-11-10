# app/crud.py
from sqlalchemy.orm import Session
import backend.models as models
import backend.schemas as schemas
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

def create_question(db: Session, question: schemas.QuestionCreate):
    db_question = models.Question(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def get_questions(db: Session, skip=0, limit=10, set_label: str | None = None, newest_first: bool = True):
    q = db.query(models.Question)
    if set_label:
        q = q.filter(models.Question.set_label == set_label.upper())
    if newest_first:
        q = q.order_by(models.Question.id.desc())
    return q.offset(skip).limit(limit).all()

def delete_all_questions(db: Session):
    db.query(models.Question).delete()
    db.commit()
from sqlalchemy.orm import Session
import backend.models as models

def get_user_questions(db: Session, user_id: int, limit: int = 10):
    """Fetch questions based on the user's assigned set_label."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return []  # user not found

    if not user.set_label:
        return []  # user has no assigned set (edge case)

    # Fetch questions belonging to that user's set
    questions = (
        db.query(models.Question)
        .filter(models.Question.set_label == user.set_label)
        .limit(limit)
        .all()
    )
    return questions

def bulk_create_questions(db: Session, questions: list[schemas.QuestionCreate]):
    db_questions = [models.Question(**q.model_dump()) for q in questions]
    db.add_all(db_questions)
    db.commit()
    for q in db_questions:
        db.refresh(q)
    return db_questions

def choose_set_label(db: Session) -> str:
    """Choose a set label A-D balancing users and ensuring questions exist.
    Prefers sets that have questions and currently fewer users.
    """
    # How many questions exist per set
    q_counts = dict(
        db.query(models.Question.set_label, func.count())
        .group_by(models.Question.set_label)
        .all()
    )
    # How many users are assigned per set
    u_counts = dict(
        db.query(models.User.set_label, func.count())
        .group_by(models.User.set_label)
        .all()
    )

    candidates = []
    for s in ["A", "B", "C", "D"]:
        candidates.append((s, q_counts.get(s, 0), u_counts.get(s, 0)))

    # Filter to sets that have at least 1 question
    with_questions = [c for c in candidates if c[1] > 0]
    pool = with_questions if with_questions else candidates

    # Choose the set with the smallest user count; on ties, pick the one with more questions
    pool.sort(key=lambda t: (t[2], -t[1]))
    return pool[0][0]

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    # choose set automatically if not provided: round-robin by counts
    set_label = user.set_label
    if not set_label:
        set_label = choose_set_label(db)

    hashed = generate_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed, set_label=set_label)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.username == username).first()
    if user and check_password_hash(user.hashed_password, password):
        # normalize any legacy/invalid set labels to uppercase A-D
        if not user.set_label:
            user.set_label = "A"
            db.commit()
            db.refresh(user)
        else:
            upper = user.set_label.upper()
            if upper not in {"A","B","C","D"}:
                upper = "A"
            if upper != user.set_label:
                user.set_label = upper
                db.commit()
                db.refresh(user)
        return user
    return None

def get_user_questions(db: Session, user_id: int, limit: int = 10):
    user = db.get(models.User, user_id)
    if not user:
        return []
    set_label = (user.set_label or "A").upper()
    return (
        db.query(models.Question)
        .filter(models.Question.set_label == set_label)
        .order_by(models.Question.id.desc())
        .limit(limit)
        .all()
    )
