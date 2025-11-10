from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import hashlib, secrets

app = FastAPI(title="PDF to MCQ API - Working Version")

# Simple in-memory storage for testing
users_db = {
    "anveshsri2025@gmail.com": {
        "id": 1,
        "name": "Anvesh",
        "email": "anveshsri2025@gmail.com",
        "hashed_password": "e071aed4041c788d5143be874b58f6fd:546be70248e9903c03bd753c823dd931ef8c9db3f5b6d3d192fd9bc59352ea65",
        "set_label": "A",
        "is_verified": "Y"
    }
}
questions_db = []

# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str
    set_label: Optional[str] = None

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    set_label: Optional[str]
    is_verified: str

class QuestionOut(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    set_label: Optional[str]

# Password hashing
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

# --- Serve login page ---
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse("""
    <html><body>
      <h3>Login</h3>
      <form method="post" action="/login">
        <label>Email</label><br>
        <input name="email" type="email" required />
        <br><br>
        <label>Password</label><br>
        <input name="password" type="password" required />
        <br><br>
        <button type="submit">Login</button>
      </form>
      <br>
      <a href="/docs">API Documentation</a>
    </body></html>
    """)

# --- Root redirects to /login ---
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login", status_code=302)

# --- User Registration ---
@app.post("/register", response_model=dict)
def register_user(user_data: UserCreate):
    # Check if user already exists
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate passwords match
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Create new user
    user_id = len(users_db) + 1
    hashed_password = hash_password(user_data.password)
    
    users_db[user_data.email] = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "set_label": user_data.set_label or "A",
        "is_verified": "Y"  # Auto-verify for testing
    }
    
    return {
        "message": f"Registration successful! User created for {user_data.email}",
        "user_id": user_id
    }

# --- Login with Email and Password ---
@app.post("/login", response_model=dict)
def login_user(email: str = Form(...), password: str = Form(...)):
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user["is_verified"] != "Y":
        raise HTTPException(status_code=401, detail="Email not verified. Please verify your email first.")
    
    return {
        "message": "Login successful!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "set_label": user["set_label"],
            "is_verified": user["is_verified"]
        }
    }

# --- Get all users (for testing) ---
@app.get("/users")
def get_users():
    return {"users": list(users_db.values())}

# --- Test endpoint ---
@app.get("/test")
def test_endpoint():
    return {"message": "Server is working!", "status": "ok"}

# --- Run App ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_working:app", host="127.0.0.1", port=8000, reload=True)
