from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from backend.database import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text)
    option_a = Column(String(255))
    option_b = Column(String(255))
    option_c = Column(String(255))
    option_d = Column(String(255))
    correct_answer = Column(String(10))
    set_label = Column(String(1), index=True, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    username = Column(String(150), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    otp = Column(String(10), nullable=True)
    set_label = Column(String(1), index=True, nullable=False)
    is_verified = Column(String(1), default='N', nullable=False)

    
 
