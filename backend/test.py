import smtplib

EMAIL = "anveshsri2025@gmail.com"              
APP_PASSWORD = "xizrbgmyrdtsmfwv"  
try:
    # Connect to Gmail SMTP server
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()  # Use TLS
    server.login(EMAIL, APP_PASSWORD)
    print("Login successful! 🎉")
except Exception as e:
    print("Login failed:", e)
finally:
    server.quit()
