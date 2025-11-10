import requests

# Step 1: Register a new user
print('=== STEP 1: REGISTRATION ===')
reg_response = requests.post('http://127.0.0.1:8000/register', json={
    'name': 'Flow Test User', 
    'email': 'flowtest@example.com', 
    'password': 'password123', 
    'confirm_password': 'password123'
})
print(f'Registration: {reg_response.status_code}')
reg_data = reg_response.json()
print(f'User ID: {reg_data["user_id"]}, OTP: {reg_data["otp"]}')

# Step 2: Verify email
print('\n=== STEP 2: EMAIL VERIFICATION ===')
verify_response = requests.post('http://127.0.0.1:8000/verify-email', data={
    'email': 'flowtest@example.com',
    'otp': reg_data['otp']
})
print(f'Verification: {verify_response.status_code}')
print(f'Response: {verify_response.json()}')

# Step 3: Login
print('\n=== STEP 3: LOGIN ===')
login_response = requests.post('http://127.0.0.1:8000/login', json={
    'email': 'flowtest@example.com',
    'password': 'password123'
})
print(f'Login: {login_response.status_code}')
login_data = login_response.json()
print(f'User: {login_data["user"]}')

# Step 4: Access questions page
print('\n=== STEP 4: QUESTIONS PAGE ===')
questions_response = requests.get(f'http://127.0.0.1:8000/questions/{login_data["user"]["id"]}')
print(f'Questions page: {questions_response.status_code}')
print('Questions page loaded successfully!' if questions_response.status_code == 200 else 'Error loading questions page')
