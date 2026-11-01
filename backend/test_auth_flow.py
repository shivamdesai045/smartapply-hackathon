import requests

session = requests.Session()
BASE_URL = "http://localhost:5000/api/auth"

def test_auth():
    print("Testing Registration...")
    reg_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "mobile_number": "9999999999",
        "password": "password123",
        "preferred_language": "en"
    }
    r = session.post(f"{BASE_URL}/register", json=reg_data)
    print("Register Response:", r.status_code, r.json())
    
    print("Testing Duplicate Registration...")
    r = session.post(f"{BASE_URL}/register", json=reg_data)
    print("Duplicate Register Response:", r.status_code, r.json())
    
    print("Testing Login with wrong password...")
    r = session.post(f"{BASE_URL}/login", json={"email": "test@example.com", "password": "wrongpassword"})
    print("Bad Login Response:", r.status_code, r.json())
    
    print("Testing Login with correct password...")
    r = session.post(f"{BASE_URL}/login", json={"email": "test@example.com", "password": "password123"})
    print("Login Response:", r.status_code, r.json())
    
    print("Testing /me to verify session cookie...")
    r = session.get(f"{BASE_URL}/me")
    print("Me Response:", r.status_code, r.json())
    
    print("Testing Logout...")
    r = session.post(f"{BASE_URL}/logout")
    print("Logout Response:", r.status_code, r.json())
    
    print("Testing /me after logout...")
    r = session.get(f"{BASE_URL}/me")
    print("Me After Logout Response:", r.status_code, r.json())

if __name__ == "__main__":
    test_auth()
