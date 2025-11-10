// ========== CONFIG ==========
// Directly set your EC2 backend URL here
const API_BASE = "http://65.2.150.98:8000"; 

// ========== PAGE NAVIGATION ==========
function showLoginForm() {
  document.getElementById('page-welcome').classList.add('hidden');
  document.getElementById('page-login').classList.remove('hidden');
}

function showRegisterForm() {
  document.getElementById('page-welcome').classList.add('hidden');
  document.getElementById('page-register').classList.remove('hidden');
}

function backToWelcome() {
  document.getElementById('page-login').classList.add('hidden');
  document.getElementById('page-register').classList.add('hidden');
  document.getElementById('page-verify').classList.add('hidden');
  document.getElementById('page-welcome').classList.remove('hidden');
}

function backToRegister() {
  document.getElementById('page-verify').classList.add('hidden');
  document.getElementById('page-register').classList.remove('hidden');
}

// ========== USER REGISTRATION ==========
async function registerUser() {
  const name = document.getElementById('regName').value;
  const email = document.getElementById('regEmail').value;
  const password = document.getElementById('regPassword').value;
  const confirmPassword = document.getElementById('regConfirmPassword').value;

  if (!name || !email || !password || !confirmPassword) {
    alert('Please fill in all fields');
    return;
  }

  if (password !== confirmPassword) {
    alert('Passwords do not match');
    return;
  }

  if (password.length < 6) {
    alert('Password must be at least 6 characters long');
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: name,
        email: email,
        password: password,
        confirm_password: confirmPassword
      })
    });

    const data = await response.json();
    
    if (response.ok) {
      alert(data.message);
      document.getElementById('verifyEmail').textContent = email;
      document.getElementById('page-register').classList.add('hidden');
      document.getElementById('page-verify').classList.remove('hidden');
    } else {
      alert(data.detail || 'Registration failed');
    }
  } catch (error) {
    alert('Registration failed: ' + error.message);
  }
}

// ========== EMAIL VERIFICATION ==========
async function verifyEmail() {
  const email = document.getElementById('verifyEmail').textContent;
  const otp = document.getElementById('verifyOtp').value;

  if (!otp) {
    alert('Please enter the verification code');
    return;
  }

  try {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('otp', otp);

    const response = await fetch(`${API_BASE}/verify-email`, {
      method: 'POST',
      body: formData
    });

    const user = await response.json();
    
    if (response.ok) {
      alert('Email verified successfully! You can now sign in.');
      backToWelcome();
    } else {
      alert(user.detail || 'Verification failed');
    }
  } catch (error) {
    alert('Verification failed: ' + error.message);
  }
}

// ========== USER LOGIN ==========
async function loginUser() {
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;

  if (!email || !password) {
    alert('Please fill in all fields');
    return;
  }

  try {
    const btns = Array.from(document.querySelectorAll('#page-login button'));
    const signInBtn = btns.find(b => b.textContent.trim().toLowerCase().includes('sign in'));
    const prevText = signInBtn ? signInBtn.textContent : '';
    if (signInBtn) { signInBtn.disabled = true; signInBtn.textContent = 'Signing in...'; }

    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      body: formData
    });

    let data;
    const raw = await response.text();
    try { data = raw ? JSON.parse(raw) : {}; } catch (e) { data = { error: 'Invalid JSON', raw }; }

    const userObj = (data && data.user) ? data.user : data;
  
    if (response.ok && userObj && (userObj.id || userObj.email)) {
      const uid = userObj.id || '';
      const target = `${API_BASE}/questions/${uid}`;
      console.log('Login successful, redirecting to:', target);
      window.location.replace(target);
      return;
    } else {
      alert(`Login failed (${response.status}).\n` + (data.detail || data.error || data.raw || ''));
    }
  } catch (error) {
    console.error('Login error', error);
    alert('Login failed: ' + error.message);
  } finally {
    const btns = Array.from(document.querySelectorAll('#page-login button'));
    const signInBtn = btns.find(b => b.textContent.includes('Signing in...') || b.textContent.includes('Sign In'));
    if (signInBtn) { signInBtn.disabled = false; signInBtn.textContent = 'Sign In'; }
  }
}


// ========== GLOBAL EXAM STATE ==========
let examState = { user: null, questions: [], index: 0, answers: {}, viewed: {} };
let examTimerInterval = null; // store interval ID
let totalTime = 10 * 60; // 10 minutes (you can adjust here)

// ========== START EXAM ==========
async function startExam(user) {
  examState.user = user;
  examState.index = 0;
  examState.answers = {};

  // Hide auth pages safely, show exam page
  const hideIds = ['page-login', 'page-register', 'page-verify', 'page-welcome'];
  hideIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
  const examPage = document.getElementById('page-exam');
  if (examPage) examPage.classList.remove('hidden');

  // Fetch user-specific questions
  let qData = [];
  try {
    const qRes = await fetch(`${API_BASE}/my-questions/${user.id}`);
    const qRaw = await qRes.text();
    try { qData = qRaw ? JSON.parse(qRaw) : []; } catch (e) { qData = { error: 'Invalid JSON', raw: qRaw }; }
    if (!qRes.ok) {
      throw new Error(`Questions request failed (${qRes.status}): ${qData.detail || qData.error || qData.raw || ''}`);
    }
  } catch (err) {
    console.error('Fetch questions error:', err);
    alert('Failed to load questions: ' + err.message);
  }
  // Support both shapes: array of questions OR { questions: [...] }
  examState.questions = Array.isArray(qData) ? qData : ((qData && qData.questions) ? qData.questions : []);

  // Guard: if no questions, stop and inform the user
  if (!examState.questions || examState.questions.length === 0) {
    alert('No questions found for your set. Please upload questions or seed sample ones in /docs.');
    // Return to welcome page
    const examPage2 = document.getElementById('page-exam');
    if (examPage2) examPage2.classList.add('hidden');
    const welcome = document.getElementById('page-welcome');
    if (welcome) welcome.classList.remove('hidden');
    return;
  }

  // Hide OTP page, show exam page
  document.getElementById('page-otp').classList.add('hidden');
  document.getElementById('page-exam').classList.remove('hidden');

  // Extract user details safely
  const name = user.name || user.username || user.email?.split('@')[0] || 'User';
  const id = user.id || 'N/A';
  const email = user.email || 'N/A';
  const set = user.set_label || 'A';

  // Update info inside the exam header
  document.getElementById('userInfo').innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px;">
      <h2 style="margin: 0;">MCQ Test</h2>
    </div>
  `;

  // Show user details box in the right side container
  const userDetailsBox = document.getElementById('userInfoFixed');
  userDetailsBox.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 2px; font-size: 12px;">
      <div><strong>👤 ${name}</strong></div>
      <div><strong>🆔 ID: ${id}</strong></div>
      <div><strong>📧 ${email}</strong></div>
      <div><strong>📝 Set: ${set}</strong></div>
    </div>
  `;
  userDetailsBox.classList.remove('hidden');

  renderPalette();
  renderQuestion();
  startTimer(); // ✅ start timer when exam starts
}

// ========== TIMER ==========
function startTimer() {
  const timerElement = document.getElementById("timer");
  totalTime = 1 * 60; // reset to 10 mins if needed

  // Clear old interval if any
  if (examTimerInterval) clearInterval(examTimerInterval);

  examTimerInterval = setInterval(() => {
    let minutes = Math.floor(totalTime / 60);
    let seconds = totalTime % 60;

    minutes = minutes < 10 ? '0' + minutes : minutes;
    seconds = seconds < 10 ? '0' + seconds : seconds;

    timerElement.textContent = `${minutes}:${seconds}`;

    if (totalTime <= 0) {
      clearInterval(examTimerInterval);
      alert("⏰ Time's up! Your exam will be submitted automatically.");
      finishExam(); // ✅ Auto-submit exam
    }

    totalTime--;
  }, 1000);
}

// ========== RENDER QUESTION ==========
function renderQuestion() {
  const i = examState.index;
  if (!examState.questions || examState.questions.length === 0) {
    const container = document.getElementById('questionContainer');
    if (container) {
      container.innerHTML = '<div class="q-card"><h3>No Questions Available</h3><p>Please upload or seed questions.</p></div>';
    }
    document.getElementById('progress').textContent = 'No questions';
    return;
  }
  const q = examState.questions[i];
  const container = document.getElementById('questionContainer');

  // Mark as viewed
  examState.viewed[i] = true;

  const opts = ['A', 'B', 'C', 'D'].map(opt => {
    const text = q['option_' + opt.toLowerCase()];
    const checked = examState.answers[i] === opt ? 'checked' : '';
    const id = `ans_${i}_${opt}`;
    return `
      <div class="option" onclick="selectOption('${opt}')">
        <input type="radio" id="${id}" name="ans" value="${opt}" ${checked}>
        <span class="custom-radio"></span>
        <label for="${id}">${text}</label>
      </div>`;
  }).join('');

  container.innerHTML = `
    <div class="q-card" data-correct="${q.correct_answer.toUpperCase()}">
      <h3>Q${i + 1}. ${q.question_text}</h3>
      <div class="opts">${opts}</div>
      <div id="qFeedback" class="feedback"></div>
    </div>`;

  document.getElementById('progress').textContent =
    `Question ${i + 1} of ${examState.questions.length}`;

  document.getElementById('prevBtn').disabled = i === 0;
  document.getElementById('submitBtn').textContent =
    (i === examState.questions.length - 1) ? 'Submit Test' : 'Submit & Next';

  if (examState.answers[i]) updatePaletteColor(i, 'green');
  else updatePaletteColor(i, 'red');
}

// ========== SELECT OPTION ==========
function selectOption(optionValue) {
  document.querySelectorAll('input[name="ans"]').forEach(input => {
    input.checked = false;
  });
  const selectedInput = document.querySelector(`input[value="${optionValue}"]`);
  if (selectedInput) selectedInput.checked = true;

  examState.answers[examState.index] = optionValue;
  updatePaletteColor(examState.index, 'green');

  const fb = document.getElementById('qFeedback');
  fb.className = 'feedback';
  fb.textContent = '';
}

// ========== SUBMIT ANSWER ==========
function submitAnswer() {
  const selected = document.querySelector('input[name="ans"]:checked');
  const fb = document.getElementById('qFeedback');
  if (!selected) {
    fb.className = 'feedback bad';
    fb.textContent = 'Please choose an option.';
    return;
  }

  const choice = selected.value.toUpperCase();
  examState.answers[examState.index] = choice;
  const correct = document.querySelector('.q-card').dataset.correct;

  if (choice === correct) {
    fb.className = 'feedback ok';
    fb.textContent = 'Correct!';
  } else {
    fb.className = 'feedback bad';
    fb.textContent = `Incorrect. Correct answer is ${correct}.`;
  }

  updatePaletteColor(examState.index, 'green');

  if (examState.index < examState.questions.length - 1) {
    examState.index++;
    renderQuestion();
  } else {
    finishExam();
  }
}

// ========== PREVIOUS ==========
function prevQuestion() {
  if (examState.index === 0) return;
  examState.index--;
  renderQuestion();
}

// ========== FINISH EXAM ==========
function finishExam() {
  // Stop timer if running
  if (examTimerInterval) clearInterval(examTimerInterval);

  const total = examState.questions.length;
  let correct = 0;
  let attempted = 0;

  // Count correct & attempted
  examState.questions.forEach((q, i) => {
    const userAns = (examState.answers[i] || '').trim();
    if (userAns) attempted++; // count attempted if any answer chosen
    if (userAns.toUpperCase() === q.correct_answer.toUpperCase()) correct++;
  });

  const notAttempted = total - attempted;
  const percentage = Math.round((correct / total) * 100);

  // User details
  const user = examState.user;
  const name = user.name || user.username || user.email?.split('@')[0] || 'User';
  const id = user.id || 'N/A';
  const email = user.email || 'N/A';
  const set = user.set_label || 'A';

  // Switch to result page
  document.getElementById('page-exam').classList.add('hidden');
  document.getElementById('page-result').classList.remove('hidden');

  // Show result summary
  document.getElementById('resultText').innerHTML = `
    <div style="text-align: left; max-width: 500px; margin: 0 auto;">
      <h3 style="color: #007bff; margin-bottom: 20px;">📊 Test Results</h3>

      <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin: 0 0 10px 0; color: #333;">👤 User Details</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px;">
          <div><strong>Name:</strong> ${name}</div>
          <div><strong>User ID:</strong> ${id}</div>
          <div><strong>Email:</strong> ${email}</div>
          <div><strong>Set:</strong> ${set}</div>
        </div>
      </div>

      <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin: 0 0 10px 0; color: #2d5a2d;">🎯 Score Summary</h4>
        <div style="font-size: 16px; color: #2d5a2d;">
          <p><strong>Total Questions:</strong> ${total}</p>
          <p><strong>Attempted:</strong> ${attempted}</p>
          <p><strong>Not Attempted:</strong> ${notAttempted}</p>
          <p><strong>Marks Scored:</strong> ${correct}</p>
          <p><strong>Percentage:</strong> ${percentage}%</p>
        </div>
      </div>
    </div>
  `;
}

// ========== NAVIGATION ==========
function goHome() {
  if (examTimerInterval) clearInterval(examTimerInterval);
  document.getElementById('page-result').classList.add('hidden');
  document.getElementById('page-welcome').classList.remove('hidden');
  examState = { user: null, questions: [], index: 0, answers: {}, viewed: {} };
}

// ========== PALETTE ==========
function renderPalette() {
  const palette = document.getElementById('questionPalette');
  palette.innerHTML = '';
  for (let i = 0; i < examState.questions.length; i++) {
    const btn = document.createElement('button');
    btn.className = 'palette-btn grey';
    btn.textContent = i + 1;
    btn.onclick = () => {
      examState.index = i;
      renderQuestion();
    };
    palette.appendChild(btn);
  }
}

function updatePaletteColor(index, status) {
  const buttons = document.querySelectorAll('.palette-btn');
  if (!buttons[index]) return;
  buttons[index].className = `palette-btn ${status}`;
}
