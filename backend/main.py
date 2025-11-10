from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import sqlalchemy
from typing import List
import os, shutil, random, smtplib, hashlib, secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import backend.database as database
import backend.models as models
import backend.schemas as schemas
import backend.crud as crud
import backend.pdf_parser as pdf_parser
import backend.mcq_generator as mcq_generator
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="PDF to MCQ API")

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://frontend-questions.s3-website.ap-south-1.amazonaws.com"], # Change this to your frontend S3 URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Password hashing helpers ---
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

# --- Database setup ---
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schema ensure ---
@app.on_event("startup")
def ensure_schema():
    try:
        with database.engine.begin() as conn:
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(150)"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp VARCHAR(10)"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified VARCHAR(1) DEFAULT 'N'"))
            conn.execute(sqlalchemy.text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS set_label VARCHAR(1)"))
        print("[startup] Schema ensure completed successfully ✅")
    except Exception as e:
        print(f"[startup] Skipping schema ensure due to DB error: {e}")

    # Auto-seed if no questions exist
    try:
        db = database.SessionLocal()
        if not db.query(models.Question).first():
            print("[startup] No questions found. Seeding sample questions...")
            samples = []
            base_questions = [
                ("What is the capital of France?", ("London", "Paris", "Berlin", "Madrid"), "B"),
                ("Which planet is known as the Red Planet?", ("Venus", "Mars", "Jupiter", "Saturn"), "B"),
                ("What is 2 + 2?", ("3", "4", "5", "6"), "B"),
                ("Who wrote 'Romeo and Juliet'?", ("Charles Dickens", "William Shakespeare", "Mark Twain", "Jane Austen"), "B"),
                ("Largest ocean on Earth?", ("Atlantic", "Indian", "Pacific", "Arctic"), "C"),
            ]
            for set_label in ["A", "B", "C", "D"]:
                for i in range(10):
                    q_text, opts, ans = base_questions[i % len(base_questions)]
                    samples.append(models.Question(
                        question_text=q_text,
                        option_a=opts[0], option_b=opts[1],
                        option_c=opts[2], option_d=opts[3],
                        correct_answer=ans, set_label=set_label
                    ))
            db.add_all(samples)
            db.commit()
            print(f"[startup] Seeded {len(samples)} sample questions.")
    except Exception as e:
        print("[startup] Failed to seed questions:", e)
    finally:
        db.close()

# --- Serve login route (simplified for S3 deployment) ---
@app.get("/login")
async def login_page():
    return JSONResponse({
        "message": "✅ Backend is running successfully. Use your S3 frontend to log in."
    })

# --- Redirect root to login ---
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login")

# --- Upload and parse PDF ---
@app.post("/upload-pdf/", response_model=List[schemas.QuestionOut])
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    os.makedirs("temp", exist_ok=True)
    file_path = os.path.join("temp", file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    text = pdf_parser.extract_text_from_pdf(file_path)
    questions = mcq_generator.generate_mcqs_from_text(text)

    sets = {"A": [], "B": [], "C": [], "D": []}
    for q in questions:
        lbl = (q.set_label or "A").upper()
        if lbl in sets and len(sets[lbl]) < 10:
            sets[lbl].append(q)
        if all(len(v) >= 10 for v in sets.values()):
            break

    limited = [q for label in ["A", "B", "C", "D"] for q in sets[label]]
    crud.delete_all_questions(db)
    return crud.bulk_create_questions(db, limited)

# --- Email OTP setup ---
SENDER_EMAIL = "anveshsri2025@gmail.com"
SENDER_PASSWORD = "xizrbgmyrdtsmfwv"

def send_email_otp(receiver: str, otp: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your OTP Code"
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver
    html = f"<p>Your OTP is <b>{otp}</b></p>"
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP send failed: {e}")

# --- OTP endpoints ---
@app.post("/request-otp")
def request_otp(email: str = Form(...), db: Session = Depends(get_db)):
    otp = str(random.randint(100000, 999999))
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        set_label = crud.choose_set_label(db)
        user = models.User(email=email, otp=otp, set_label=set_label)
        db.add(user)
    else:
        user.otp = otp
    db.commit()
    db.refresh(user)
    try:
        send_email_otp(email, otp)
        return {"message": f"OTP sent to {email}", "user_id": user.id, "otp": otp}
    except HTTPException as hx:
        return {"message": "Email send failed; fallback OTP", "user_id": user.id, "otp": otp, "error": hx.detail}

@app.post("/login-otp", response_model=schemas.UserOut)
def login_otp(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or user.otp != otp:
        raise HTTPException(status_code=401, detail="Invalid email or OTP")
    return user

# --- Registration and Login ---
@app.post("/register", response_model=schemas.UserOut)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp = str(random.randint(100000, 999999))
    set_label = crud.choose_set_label(db)
    hashed_password = hash_password(user_data.password)
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        otp=otp,
        set_label=set_label,
        is_verified='N'
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    try:
        send_email_otp(user_data.email, otp)
    except Exception:
        pass

    return new_user

@app.post("/verify-email", response_model=schemas.UserOut)
def verify_email(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or user.otp != otp:
        raise HTTPException(status_code=401, detail="Invalid email or OTP")

    user.is_verified = 'Y'
    user.otp = None
    db.commit()
    db.refresh(user)
    return user

@app.post("/login", response_model=schemas.UserOut)
def login_user(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.is_verified != 'Y':
        raise HTTPException(status_code=401, detail="Email not verified")
    return user

# --- Utilities ---
@app.post("/set-password")
def set_password(email: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"message": "Password updated", "user_id": user.id}

@app.get("/my-questions/{user_id}", response_model=List[schemas.QuestionOut])
def my_questions(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user_questions(db, user_id, limit=10)

@app.get("/questions/", response_model=List[schemas.QuestionOut])
def read_questions(skip: int = 0, limit: int = 10, set_label: str = None, db: Session = Depends(get_db)):
    return crud.get_questions(db, skip=skip, limit=limit, set_label=set_label)

@app.delete("/questions/clear")
def clear_questions(db: Session = Depends(get_db)):
    crud.delete_all_questions(db)
    return {"status": "ok", "message": "All questions deleted"}

@app.get("/user-by-email")
def user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "set_label": user.set_label,
        "is_verified": user.is_verified,
        "otp": user.otp,
        "has_password": bool(user.hashed_password),
    }
# --- Server-rendered Questions Page ---
# --- Server-rendered Questions Page ---
@app.get("/questions/{user_id}", response_class=HTMLResponse)
def questions_page(user_id: int, db: Session = Depends(get_db)):
    import json

    # --- Fetch questions for this user ---
    questions = crud.get_user_questions(db, user_id, limit=50)
    q_payload = [
        {
            "id": q.id,
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_answer": q.correct_answer,
        }
        for q in questions
    ]

    q_json = json.dumps(q_payload)
    safe_json = q_json.replace("</", "<\\/")

    html_content = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>MCQ Exam</title>
        <style>
          body {{
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            margin: 0;
            padding: 20px;
          }}
          .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #2d6a4f;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
          }}
          .container {{
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            gap: 20px;
          }}
          .question-box {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 20px;
            flex: 2;
          }}
          .palette {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 20px;
            flex: 1;
            text-align: center;
          }}
          .btn {{
            background-color: #2d6a4f;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
          }}
          .btn:disabled {{
            background-color: #999;
            cursor: not-allowed;
          }}
          .option {{
            display: block;
            margin: 8px 0;
          }}
          .question-number {{
            display: inline-block;
            width: 32px;
            height: 32px;
            line-height: 32px;
            border-radius: 50%;
            margin: 4px;
            background: #eee;
            color: #000;
            cursor: pointer;
          }}
          .question-number.active {{
            background: #2d6a4f;
            color: #fff;
          }}
          .timer {{
            background: #fff;
            color: #2d6a4f;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: bold;
          }}
        </style>
      </head>
      <body>
        <div class="header">
          <h2>MCQ Exam</h2>
          <div class="timer" id="timer">10:00</div>
        </div>

        <div class="container">
          <div class="question-box">
            <h3 id="question-text">Loading...</h3>
            <div id="options"></div>
            <div style="margin-top: 20px;">
              <button class="btn" id="prev-btn" onclick="prevQuestion()">Previous</button>
              <button class="btn" id="next-btn" onclick="nextQuestion()">Next</button>
            </div>
          </div>

          <div class="palette">
            <h3>Question Palette</h3>
            <div id="palette-buttons"></div>
            <button class="btn" style="margin-top: 15px;" onclick="submitTest()">Submit Test</button>
          </div>
        </div>

        <script id="qdata" type="application/json">{safe_json}</script>
        <script>
          const questions = JSON.parse(document.getElementById("qdata").textContent || "[]");
          let currentIndex = 0;
          const answers = {{}};

          function loadQuestion(index) {{
            if (questions.length === 0) {{
              document.getElementById("question-text").textContent = "No questions found.";
              return;
            }}

            const q = questions[index];
            document.getElementById("question-text").innerHTML = `<b>Q${{index + 1}}.</b> ${{q.question_text}}`;

            const opts = ["A", "B", "C", "D"];
            const optionsDiv = document.getElementById("options");
            optionsDiv.innerHTML = "";

            opts.forEach(opt => {{
              const optVal = q["option_" + opt.toLowerCase()];
              if (optVal) {{
                const checked = answers[q.id] === opt ? "checked" : "";
                optionsDiv.innerHTML += `
                  <label class='option'>
                    <input type='radio' name='option' value='${{opt}}' ${{checked}} 
                      onchange='answers[${{q.id}}] = this.value'> 
                    (${{opt}}) ${{optVal}}
                  </label>
                `;
              }}
            }});

            document.getElementById("prev-btn").disabled = index === 0;
            document.getElementById("next-btn").disabled = index === questions.length - 1;

            updatePalette();
          }}

          function nextQuestion() {{
            if (currentIndex < questions.length - 1) {{
              currentIndex++;
              loadQuestion(currentIndex);
            }}
          }}

          function prevQuestion() {{
            if (currentIndex > 0) {{
              currentIndex--;
              loadQuestion(currentIndex);
            }}
          }}

          function goToQuestion(i) {{
            currentIndex = i;
            loadQuestion(currentIndex);
          }}

          function updatePalette() {{
            const palette = document.getElementById("palette-buttons");
            palette.innerHTML = "";
            questions.forEach((q, i) => {{
              const active = i === currentIndex ? "active" : "";
              const btn = document.createElement("div");
              btn.className = "question-number " + active;
              btn.textContent = i + 1;
              btn.onclick = () => goToQuestion(i);
              palette.appendChild(btn);
            }});
          }}

          function startTimer(duration) {{
            let timer = duration, minutes, seconds;
            const display = document.getElementById("timer");
            const countdown = setInterval(() => {{
              minutes = parseInt(timer / 60, 10);
              seconds = parseInt(timer % 60, 10);

              minutes = minutes < 10 ? "0" + minutes : minutes;
              seconds = seconds < 10 ? "0" + seconds : seconds;

              display.textContent = minutes + ":" + seconds;

              if (--timer < 0) {{
                clearInterval(countdown);
                submitTest();
              }}
            }}, 1000);
          }}

          function submitTest() {{
            let answered = Object.keys(answers).length;
            alert(`You have answered ${{answered}} out of ${{questions.length}} questions.`);
          }}

          loadQuestion(0);
          startTimer(600); // 10 minutes
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html_content)


# --- Run app ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
