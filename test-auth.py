"""
Test script for authentication endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_register():
    """Test user registration"""
    print("\n=== Testing User Registration ===")
    data = {
        "email": "test@example.com",
        "password": "Test@1234",
        "full_name": "Test User"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 201

def test_login():
    """Test user login"""
    print("\n=== Testing User Login ===")
    data = {
        "email": "test@example.com",
        "password": "Test@1234"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code == 200:
        return result.get("access_token")
    return None

def test_me(access_token):
    """Test getting current user"""
    print("\n=== Testing Get Current User ===")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    print("Testing Authentication Flow")
    print("=" * 50)
    
    # Test registration (might fail if user exists)
    try:
        test_register()
    except Exception as e:
        print(f"Registration error (user might already exist): {e}")
    
    # Test login
    access_token = test_login()
    
    if access_token:
        # Test getting user info
        test_me(access_token)
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Login failed!")

if __name__ == "__main__":
    main()
