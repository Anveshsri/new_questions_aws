import hashlib

password = 'xizrbgmyrdtsmfwv'
salt = '12345678901234567890123456789012'  # Fixed salt
password_hash = hashlib.sha256((password + salt).encode()).hexdigest()

print(f"Password: {password}")
print(f"Salt: {salt}")
print(f"Hash: {password_hash}")
print(f"Full hash: {salt}:{password_hash}")

# Test verification
def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

test_hash = f"{salt}:{password_hash}"
print(f"Verification test: {verify_password(password, test_hash)}")
