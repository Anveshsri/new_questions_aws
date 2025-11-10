from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List
import os

app = FastAPI(title="PDF to MCQ API - Simple Version")

# Simple in-memory user storage for testing
users_db = {
    "anveshsri2025@gmail.com": {
        "id": 1,
        "name": "Test User",
        "email": "anveshsri2025@gmail.com",
        "password": "xizrbgmyrdtsmfwv",
        "is_verified": "Y"
    }
}

# --- Serve login page ---
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse("""
    <html><body>
      <h3>Login</h3>
      <form method="post" action="/login">
        <label>Email</label><br>
        <input name="email" type="email" required value="anveshsri2025@gmail.com" />
        <br><br>
        <label>Password</label><br>
        <input name="password" type="password" required value="xizrbgmyrdtsmfwv" />
        <br><br>
        <button type="submit">Login</button>
      </form>
    </body></html>
    """)

# --- Root redirects to /login ---
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login", status_code=302)

# --- Login with Email and Password ---
@app.post("/login")
def login_user(email: str = Form(...), password: str = Form(...)):
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user["is_verified"] != "Y":
        raise HTTPException(status_code=401, detail="Email not verified. Please verify your email first.")
    
    return {"message": "Login successful!", "user": user}

# --- Test endpoint ---
@app.get("/test")
def test_endpoint():
    return {"message": "Server is working!", "status": "ok"}

# --- Run App ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="127.0.0.1", port=8000, reload=True)
