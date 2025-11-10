from pydantic import BaseModel, constr, field_validator, EmailStr
from typing import List, Optional

class QuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: constr(min_length=1, max_length=1)
    set_label: Optional[constr(min_length=1, max_length=1)] = None

    @field_validator("correct_answer", mode="before")
    def normalize_correct_answer(cls, v: str) -> str:
        if v is None:
            return v
        val = str(v).strip().upper()
        if val not in {"A", "B", "C", "D"}:
            raise ValueError("correct_answer must be one of A, B, C, or D")
        return val

    @field_validator("set_label", mode="before")
    def normalize_set_label(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        val = str(v).strip().upper()
        if val not in {"A", "B", "C", "D"}:
            raise ValueError("set_label must be one of A, B, C, or D")
        return val


class QuestionOut(QuestionCreate):
    id: int

    class Config:
        orm_mode = True


class BulkQuestionCreate(BaseModel):
    questions: List[QuestionCreate]


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str
    set_label: Optional[constr(min_length=1, max_length=1)] = None

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    username: Optional[str] = None
    email: EmailStr
    set_label: Optional[str]
    is_verified: str

    class Config:
        orm_mode = True

class EmailSchema(BaseModel):
    email: EmailStr


class VerifyEmailOtp(BaseModel):
    email: EmailStr
    otp: str
