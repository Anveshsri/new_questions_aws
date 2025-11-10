from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import hashlib, secrets
import os
import shutil
import backend.pdf_parser as pdf_parser
import backend.mcq_generator as mcq_generator
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Login Server")

# --- Password hashing functions ---
def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

# Simple in-memory storage
users_db = {
    "anveshsri2025@gmail.com": {
        "id": 1,
        "name": "Anvesh",
        "email": "anveshsri2025@gmail.com",
        "hashed_password": "simple123456789012345678901234567890:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        "set_label": "A",
        "is_verified": "Y"
    }
}

# Sample questions database
questions_db = [
    {
        "id": 1,
        "question_text": "What is the capital of France?",
        "option_a": "London",
        "option_b": "Paris",
        "option_c": "Berlin",
        "option_d": "Madrid",
        "correct_answer": "B",
        "set_label": "A"
    },
    {
        "id": 2,
        "question_text": "Which planet is known as the Red Planet?",
        "option_a": "Venus",
        "option_b": "Mars",
        "option_c": "Jupiter",
        "option_d": "Saturn",
        "correct_answer": "B",
        "set_label": "A"
    },
    {
        "id": 3,
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
        "set_label": "A"
    },
    {
        "id": 4,
        "question_text": "Who wrote 'Romeo and Juliet'?",
        "option_a": "Charles Dickens",
        "option_b": "William Shakespeare",
        "option_c": "Mark Twain",
        "option_d": "Jane Austen",
        "correct_answer": "B",
        "set_label": "A"
    },
    {
        "id": 5,
        "question_text": "What is the largest ocean on Earth?",
        "option_a": "Atlantic",
        "option_b": "Indian",
        "option_c": "Pacific",
        "option_d": "Arctic",
        "correct_answer": "C",
        "set_label": "A"
    },
    {
        "id": 6,
        "question_text": "Which programming language is known for web development?",
        "option_a": "Python",
        "option_b": "JavaScript",
        "option_c": "C++",
        "option_d": "Java",
        "correct_answer": "B",
        "set_label": "B"
    },
    {
        "id": 7,
        "question_text": "What is the chemical symbol for gold?",
        "option_a": "Go",
        "option_b": "Gd",
        "option_c": "Au",
        "option_d": "Ag",
        "correct_answer": "C",
        "set_label": "B"
    },
    {
        "id": 8,
        "question_text": "Which country has the most population?",
        "option_a": "India",
        "option_b": "China",
        "option_c": "United States",
        "option_d": "Brazil",
        "correct_answer": "B",
        "set_label": "B"
    },
    {
        "id": 9,
        "question_text": "What is the speed of light?",
        "option_a": "300,000 km/s",
        "option_b": "150,000 km/s",
        "option_c": "450,000 km/s",
        "option_d": "600,000 km/s",
        "correct_answer": "A",
        "set_label": "C"
    },
    {
        "id": 10,
        "question_text": "Which is the smallest country in the world?",
        "option_a": "Monaco",
        "option_b": "Vatican City",
        "option_c": "Liechtenstein",
        "option_d": "San Marino",
        "correct_answer": "B",
        "set_label": "C"
    }
]

# Password verification
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
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCQ System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }
            h3 {
                color: #555;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 5px;
                margin-top: 30px;
            }
            form {
                margin-bottom: 20px;
            }
            p {
                margin: 15px 0;
            }
            label {
                display: inline-block;
                width: 120px;
                font-weight: bold;
                color: #333;
            }
            input {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                width: 250px;
                font-size: 14px;
            }
            input:focus {
                border-color: #4CAF50;
                outline: none;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 10px;
            }
            button:hover {
                background-color: #45a049;
            }
            .password-container {
                position: relative;
                display: inline-block;
            }
            .toggle-password {
                position: absolute;
                right: 5px;
                top: 50%;
                transform: translateY(-50%);
                background: none;
                border: none;
                cursor: pointer;
                font-size: 12px;
                color: #666;
                padding: 2px 5px;
            }
            .toggle-password:hover {
                color: #333;
            }
            .links {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }
            .links a {
                color: #4CAF50;
                text-decoration: none;
            }
            .links a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>MCQ System</h2>
            
            <h3>Login</h3>
            <form method="post" action="/login" onsubmit="handleLogin(event)">
                <p>
                    <label>Email:</label>
                    <input name="email" type="email" required />
                </p>
                <p>
                    <label>Password:</label>
                    <div class="password-container">
                        <input name="password" type="text" required />
                        <button type="button" class="toggle-password" onclick="togglePassword(this)">Hide</button>
                    </div>
                </p>
                <p><button type="submit">Login</button></p>
            </form>
            
            <h3>Create Account</h3>
            <form method="post" action="/register">
                <p>
                    <label>Name:</label>
                    <input name="name" type="text" required />
                </p>
                <p>
                    <label>Email:</label>
                    <input name="email" type="email" required />
                </p>
                <p>
                    <label>Password:</label>
                    <div class="password-container">
                        <input name="password" type="text" required />
                        <button type="button" class="toggle-password" onclick="togglePassword(this)">Hide</button>
                    </div>
                </p>
                <p>
                    <label>Confirm Password:</label>
                    <div class="password-container">
                        <input name="confirm_password" type="text" required />
                        <button type="button" class="toggle-password" onclick="togglePassword(this)">Hide</button>
                    </div>
                </p>
                <p><button type="submit">Create Account</button></p>
            </form>
            
            <div class="links">
                <a href="/reset-password-page">Forgot Password?</a><br>
                <a href="/docs">API Documentation</a>
            </div>
        </div>
        
        <script>
            function togglePassword(button) {
                const input = button.previousElementSibling;
                if (input.type === 'text') {
                    input.type = 'password';
                    button.textContent = 'Show';
                } else {
                    input.type = 'text';
                    button.textContent = 'Hide';
                }
            }
            
            function handleLogin(e) {
                e.preventDefault();
                const form = e.target;
                const formData = new FormData(form);
                const data = Object.fromEntries(formData);
                
                fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.user) {
                        // Redirect to questions page with user ID
                        window.location.href = `/questions/${data.user.id}`;
                    } else {
                        alert('Login failed: ' + (data.detail || 'Unknown error'));
                    }
                })
                .catch(error => {
                    alert('Error: ' + error.message);
                });
            }
        </script>
    </body>
    </html>
    """)

# --- Questions Page ---
@app.get("/questions/{user_id}", response_class=HTMLResponse)
async def questions_page(user_id: int):
    # Find user by ID
    user = None
    for u in users_db.values():
        if u["id"] == user_id:
            user = u
            break
    
    if not user:
        return HTMLResponse("""
        <html>
        <head><title>User Not Found</title></head>
        <body>
            <h2>User Not Found</h2>
            <p><a href="/login">Back to Login</a></p>
        </body>
        </html>
        """)
    
    # Get questions for user's set_label
    user_set = user["set_label"]
    user_questions = [q for q in questions_db if q["set_label"] == user_set]
    
    # Generate HTML for questions
    questions_html = ""
    for i, q in enumerate(user_questions, 1):
        questions_html += f"""
        <div class="question-card">
            <h3>Question {i}</h3>
            <p class="question-text">{q['question_text']}</p>
            <div class="options">
                <div class="option">A) {q['option_a']}</div>
                <div class="option">B) {q['option_b']}</div>
                <div class="option">C) {q['option_c']}</div>
                <div class="option">D) {q['option_d']}</div>
            </div>
            <div class="correct-answer">Correct Answer: {q['correct_answer']}</div>
        </div>
        """
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCQ Questions - {user['name']}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 20px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
                text-align: center;
            }}
            .header h1 {{
                color: #333;
                margin: 0;
            }}
            .user-info {{
                color: #666;
                margin-top: 10px;
            }}
            .question-card {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .question-card h3 {{
                color: #4CAF50;
                margin-top: 0;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 5px;
            }}
            .question-text {{
                font-size: 16px;
                font-weight: bold;
                margin: 15px 0;
                color: #333;
            }}
            .options {{
                margin: 15px 0;
            }}
            .option {{
                padding: 8px;
                margin: 5px 0;
                background-color: #f9f9f9;
                border-left: 4px solid #ddd;
                border-radius: 4px;
            }}
            .correct-answer {{
                background-color: #d4edda;
                color: #155724;
                padding: 10px;
                border-radius: 4px;
                margin-top: 15px;
                font-weight: bold;
                border: 1px solid #c3e6cb;
            }}
            .actions {{
                text-align: center;
                margin-top: 30px;
            }}
            .btn {{
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin: 0 10px;
                text-decoration: none;
                display: inline-block;
            }}
            .btn:hover {{
                background-color: #45a049;
            }}
            .btn-secondary {{
                background-color: #6c757d;
            }}
            .btn-secondary:hover {{
                background-color: #5a6268;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📚 MCQ Questions</h1>
            <div class="user-info">
                Welcome, <strong>{user['name']}</strong>!<br>
                Email: {user['email']} | Set: {user['set_label']}
            </div>
        </div>
        
        {questions_html if questions_html else '<div class="question-card"><h3>No Questions Available</h3><p>No questions found for your set.</p></div>'}
        
        <div class="actions">
            <a href="/login" class="btn btn-secondary">Back to Login</a>
            <a href="/docs" class="btn">API Documentation</a>
        </div>
    </body>
    </html>
    """)

# --- Root redirects to /login ---
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login", status_code=302)

# --- Login with Email and Password ---
@app.post("/login")
async def login_user(request: Request):
    try:
        # Try to get JSON data first
        try:
            data = await request.json()
            email = data.get("email")
            password = data.get("password")
        except:
            # Fallback to form data
            form_data = await request.form()
            email = form_data.get("email")
            password = form_data.get("password")
        
        print(f"Login attempt: {email}")
        
        user = users_db.get(email)
        if not user:
            print(f"User not found: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password against stored hashed_password
        stored_hash = user.get("hashed_password")
        if not stored_hash:
            print(f"No stored hash for user: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not verify_password(password, stored_hash):
            print(f"Password verification failed for: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if user.get("is_verified") != "Y":
            print(f"User not verified: {email}")
            raise HTTPException(status_code=401, detail="Email not verified. Please verify your email first.")
        
        print(f"Login successful: {email}")
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
    except HTTPException:
        raise
    except Exception as e:
        print("Unexpected login error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Clear All Users ---
@app.delete("/users/clear")
def clear_all_users():
    """Clear all existing users from the database"""
    users_db.clear()
    return {"message": "All users cleared successfully", "count": 0}

# --- List All Users ---
@app.get("/users")
def list_users():
    """List all existing users"""
    return {
        "users": list(users_db.values()),
        "count": len(users_db)
    }

# --- Test endpoint ---
@app.get("/test")
def test_endpoint():
    return {"message": "Server is working!", "status": "ok"}

# --- Get Questions for User ---
@app.get("/my-questions/{user_id}")
def my_questions(user_id: int, limit: int = 10):
    # Find user by ID
    user = None
    for u in users_db.values():
        if u["id"] == user_id:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get questions for user's set_label
    user_set = user["set_label"]
    user_questions = [q for q in questions_db if q["set_label"] == user_set]
    
    # Limit the number of questions
    limited_questions = user_questions[:limit]
    
    return {
        "user_id": user_id,
        "user_set": user_set,
        "questions": limited_questions,
        "total_questions": len(limited_questions)
    }

# --- Get All Questions ---
@app.get("/questions/")
def read_questions(skip: int = 0, limit: int = 10, set_label: str = None):
    filtered_questions = questions_db
    
    if set_label:
        filtered_questions = [q for q in questions_db if q["set_label"] == set_label.upper()]
    
    # Apply pagination
    paginated_questions = filtered_questions[skip:skip + limit]
    
    return {
        "questions": paginated_questions,
        "total": len(filtered_questions),
        "skip": skip,
        "limit": limit
    }

# --- Clear Questions ---
@app.delete("/questions/clear")
def clear_questions():
    questions_db.clear()
    return {"status": "ok", "message": "All questions deleted"}

# --- Add Question ---
@app.post("/questions/")
def add_question(question_data: dict):
    new_id = max([q["id"] for q in questions_db], default=0) + 1
    question = {
        "id": new_id,
        "question_text": question_data.get("question_text", ""),
        "option_a": question_data.get("option_a", ""),
        "option_b": question_data.get("option_b", ""),
        "option_c": question_data.get("option_c", ""),
        "option_d": question_data.get("option_d", ""),
        "correct_answer": question_data.get("correct_answer", ""),
        "set_label": question_data.get("set_label", "A")
    }
    questions_db.append(question)
    return {"message": "Question added successfully", "question": question}

# --- Upload and Parse PDF ---
@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        file_path = os.path.join("temp", file.filename)

        # Save uploaded file
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Extract text from PDF
        text = pdf_parser.extract_text_from_pdf(file_path)
        
        # Generate MCQs from text
        questions = mcq_generator.generate_mcqs_from_text(text)

        # Organize questions by set labels
        sets = {"A": [], "B": [], "C": [], "D": []}
        for q in questions:
            lbl = (q.set_label or "A").upper()
            if lbl in sets and len(sets[lbl]) < 10:
                sets[lbl].append(q)
            if all(len(v) >= 10 for v in sets.values()):
                break

        # Flatten questions and add to database
        limited = [q for label in ["A", "B", "C", "D"] for q in sets[label]]
        
        # Clear existing questions
        questions_db.clear()
        
        # Add new questions to in-memory database
        for i, q in enumerate(limited):
            question = {
                "id": i + 1,
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_answer": q.correct_answer,
                "set_label": q.set_label or "A"
            }
            questions_db.append(question)

        # Clean up temp file
        os.remove(file_path)

        return {
            "message": f"PDF processed successfully! Generated {len(limited)} questions.",
            "questions": limited[:10],  # Return first 10 questions as preview
            "total_questions": len(limited)
        }
        
    except Exception as e:
        return {"error": f"Failed to process PDF: {str(e)}"}

# --- Email OTP functionality ---
def send_email_otp(email: str, otp: str):
    """Send OTP via email"""
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "your-email@gmail.com"  # Replace with your email
        sender_password = "your-app-password"   # Replace with your app password
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = "Your OTP Code"
        
        body = f"Your OTP code is: {otp}\n\nThis code will expire in 10 minutes."
        msg.attach(MIMEText(body, "plain"))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        
    except Exception as e:
        # For development, just print the OTP instead of sending email
        print(f"Email send failed: {e}")
        print(f"OTP for {email}: {otp}")

# --- Request OTP ---
@app.post("/request-otp")
def request_otp(email: str = Form(...)):
    otp = str(random.randint(100000, 999999))
    
    # Check if user exists
    if email in users_db:
        users_db[email]["otp"] = otp
    else:
        # Create new user with OTP
        new_id = max([u["id"] for u in users_db.values()], default=0) + 1
        set_labels = ["A", "B", "C", "D"]
        set_label = set_labels[new_id % 4]  # Distribute users across sets
        
        users_db[email] = {
            "id": new_id,
            "name": email.split("@")[0],  # Use email prefix as name
            "email": email,
            "otp": otp,
            "set_label": set_label,
            "is_verified": "N"
        }
    
    try:
        send_email_otp(email, otp)
        # For development/testing, always return the OTP
        return {
            "message": f"OTP sent to {email}", 
            "user_id": users_db[email]["id"],
            "otp": otp  # Include OTP for testing
        }
    except Exception as e:
        # Return fallback with OTP for development/testing
        return {
            "message": "Email send failed; using fallback OTP", 
            "user_id": users_db[email]["id"], 
            "otp": otp, 
            "error": str(e)
        }

# --- Login via OTP ---
@app.post("/login-otp")
def login_otp(email: str = Form(...), otp: str = Form(...)):
    if email not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[email]
    if user["otp"] != otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    
    # Mark user as verified
    user["is_verified"] = "Y"
    
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

# --- User Registration (supports both JSON and form data) ---
@app.post("/register")
async def register_user(request: Request):
    try:
        # Try to get JSON data first
        try:
            data = await request.json()
            name = data.get("name")
            email = data.get("email")
            password = data.get("password")
            confirm_password = data.get("confirm_password")
        except:
            # Fallback to form data
            form_data = await request.form()
            name = form_data.get("name")
            email = form_data.get("email")
            password = form_data.get("password")
            confirm_password = form_data.get("confirm_password")
        
        # Validate all required fields
        if not all([name, email, password, confirm_password]):
            return JSONResponse(
                status_code=400, 
                content={"error": "Missing required fields: name, email, password, confirm_password"}
            )
        
        # Check if passwords match
        if password != confirm_password:
            return JSONResponse(
                status_code=400, 
                content={"error": "Passwords do not match"}
            )
        
        # Check if user already exists
        if email in users_db:
            return JSONResponse(
                status_code=400, 
                content={"error": "Email already registered"}
            )
        
        # Generate OTP for email verification
        otp = str(random.randint(100000, 999999))
        
        # Create new user
        new_id = max([u["id"] for u in users_db.values()], default=0) + 1
        set_labels = ["A", "B", "C", "D"]
        set_label = set_labels[new_id % 4]  # Distribute users across sets
        
        hashed_password = hash_password(password)
        
        users_db[email] = {
            "id": new_id,
            "name": name,
            "email": email,
            "hashed_password": hashed_password,
            "otp": otp,
            "set_label": set_label,
            "is_verified": "N"
        }
        
        # Return success response with proper user structure
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Registration successful! OTP: {otp}",
                "user": {
                    "id": new_id,
                    "name": name,
                    "email": email,
                    "set_label": set_label,
                    "is_verified": "N"
                },
                "otp": otp
            }
        )
        
    except Exception as e:
        # Catch any unexpected errors and return JSON
        return JSONResponse(
            status_code=500, 
            content={"error": f"Registration failed: {str(e)}"}
        )

# --- Verify Email with OTP ---
@app.post("/verify-email")
def verify_email(email: str = Form(...), otp: str = Form(...)):
    if email not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[email]
    
    # Check if OTP exists for the user
    stored_otp = user.get("otp")
    if not stored_otp or stored_otp != otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    
    # Mark user as verified
    user["is_verified"] = "Y"
    
    return {
        "message": "Email verified successfully!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "set_label": user["set_label"],
            "is_verified": user["is_verified"]
        }
    }

# --- Password Reset Request ---
@app.post("/reset-password-request")
def reset_password_request(email: str = Form(...)):
    """Request password reset - sends OTP to email"""
    if email not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[email]
    
    # Generate new OTP for password reset
    otp = str(random.randint(100000, 999999))
    user["reset_otp"] = otp
    user["reset_otp_expiry"] = "10min"  # In production, use actual timestamp
    
    try:
        send_email_otp(email, otp)
        # For development/testing, always return the OTP
        return {
            "message": f"Password reset OTP sent to {email}",
            "otp": otp  # Include OTP for testing/development
        }
    except Exception as e:
        # Return fallback with OTP for development/testing
        return {
            "message": "Email send failed; using fallback OTP",
            "otp": otp,
            "error": str(e)
        }

# --- Password Reset with OTP ---
@app.post("/reset-password")
def reset_password(email: str = Form(...), otp: str = Form(...), new_password: str = Form(...)):
    """Reset password using OTP"""
    if email not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[email]
    
    # Check if OTP exists and matches
    stored_otp = user.get("reset_otp")
    if not stored_otp or stored_otp != otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    
    # Update password
    user["hashed_password"] = hash_password(new_password)
    
    # Clear reset OTP
    user.pop("reset_otp", None)
    user.pop("reset_otp_expiry", None)
    
    return {
        "message": "Password reset successfully! You can now login with your new password.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }

# --- Password Reset Page ---
@app.get("/reset-password-page", response_class=HTMLResponse)
async def reset_password_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reset Password - MCQ System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }
            h3 {
                color: #555;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 5px;
                margin-top: 30px;
            }
            form {
                margin-bottom: 20px;
            }
            p {
                margin: 15px 0;
            }
            label {
                display: inline-block;
                width: 150px;
                font-weight: bold;
                color: #333;
            }
            input {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                width: 250px;
                font-size: 14px;
            }
            input:focus {
                border-color: #4CAF50;
                outline: none;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 10px;
            }
            button:hover {
                background-color: #45a049;
            }
            .message {
                padding: 10px;
                border-radius: 4px;
                margin: 15px 0;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .links {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }
            .links a {
                color: #4CAF50;
                text-decoration: none;
            }
            .links a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Reset Password</h2>
            
            <div id="step1">
                <h3>Step 1: Request OTP</h3>
                <form onsubmit="requestOTP(event)">
                    <p>
                        <label>Email:</label>
                        <input name="email" type="email" required />
                    </p>
                    <p><button type="submit">Send OTP</button></p>
                </form>
            </div>
            
            <div id="step2" style="display: none;">
                <h3>Step 2: Reset Password</h3>
                <form onsubmit="resetPassword(event)">
                    <p>
                        <label>Email:</label>
                        <input name="email" type="email" id="resetEmail" required />
                    </p>
                    <p>
                        <label>OTP:</label>
                        <input name="otp" type="text" required />
                    </p>
                    <p>
                        <label>New Password:</label>
                        <input name="new_password" type="password" required />
                    </p>
                    <p>
                        <label>Confirm Password:</label>
                        <input name="confirm_password" type="password" required />
                    </p>
                    <p><button type="submit">Reset Password</button></p>
                </form>
            </div>
            
            <div id="message"></div>
            
            <div class="links">
                <a href="/login">Back to Login</a>
            </div>
        </div>
        
        <script>
            let currentEmail = '';
            
            function showMessage(text, isError = false) {
                const msgDiv = document.getElementById('message');
                msgDiv.className = 'message ' + (isError ? 'error' : 'success');
                msgDiv.textContent = text;
                msgDiv.style.display = 'block';
            }
            
            function requestOTP(e) {
                e.preventDefault();
                const form = e.target;
                const formData = new FormData(form);
                const email = formData.get('email');
                currentEmail = email;
                
                fetch('/reset-password-request', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.otp) {
                        showMessage('OTP sent! Check your email. OTP: ' + data.otp + ' (for testing)', false);
                        document.getElementById('step1').style.display = 'none';
                        document.getElementById('step2').style.display = 'block';
                        document.getElementById('resetEmail').value = email;
                    } else {
                        showMessage('Error: ' + (data.detail || 'Unknown error'), true);
                    }
                })
                .catch(error => {
                    showMessage('Error: ' + error.message, true);
                });
            }
            
            function resetPassword(e) {
                e.preventDefault();
                const form = e.target;
                const formData = new FormData(form);
                const newPassword = formData.get('new_password');
                const confirmPassword = formData.get('confirm_password');
                
                if (newPassword !== confirmPassword) {
                    showMessage('Passwords do not match!', true);
                    return;
                }
                
                fetch('/reset-password', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message) {
                        showMessage(data.message + ' Redirecting to login...', false);
                        setTimeout(() => {
                            window.location.href = '/login';
                        }, 2000);
                    } else {
                        showMessage('Error: ' + (data.detail || 'Unknown error'), true);
                    }
                })
                .catch(error => {
                    showMessage('Error: ' + error.message, true);
                });
            }
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("login_server:app", host="127.0.0.1", port=8000, reload=False)
