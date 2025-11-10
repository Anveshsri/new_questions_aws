"""
Helper script to test if a password matches the stored hash.
This can help you find your password if you remember what it might be.
"""
import hashlib

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

# The stored hash for anveshsri2025@gmail.com
stored_hash = "simple123456789012345678901234567890:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"

print("=" * 60)
print("Password Testing Tool")
print("=" * 60)
print("\nTesting password against stored hash...")
print(f"Stored hash: {stored_hash}\n")

# Common passwords to test
common_passwords = [
    "simple",
    "password",
    "password123",
    "123456",
    "12345678",
    "admin",
    "test",
    "anvesh",
    "anvesh123",
    "Simple",
    "SIMPLE",
]

# Test common passwords
print("Testing common passwords:")
print("-" * 60)
for pwd in common_passwords:
    if verify_password(pwd, stored_hash):
        print(f"[MATCH FOUND] Password is: '{pwd}'")
        break
    else:
        print(f"[NO MATCH] '{pwd}'")
else:
    print("\nNo match found with common passwords.")
    print("\nYou can test your own password by modifying this script.")
    print("Or use the password reset feature in the API.")

print("\n" + "=" * 60)
print("To test a specific password, modify the script and add it to the list above.")
print("=" * 60)

