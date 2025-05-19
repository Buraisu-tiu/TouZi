import requests

def test_buy_route():
    """Test the buy route with a simple POST request"""
    url = "http://localhost:5000/buy"
    session = requests.Session()
    
    # First get login page to get CSRF token if needed
    login_resp = session.get("http://localhost:5000/login")
    
    # Login
    login_data = {
        "username": "testuser",  # Replace with a valid username
        "password": "testpass"   # Replace with a valid password
    }
    login = session.post("http://localhost:5000/login", data=login_data)
    
    # Now test the buy route
    data = {
        "symbol": "AAPL",
        "shares": "1"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    response = session.post(url, data=data, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}...")  # Print the first 200 chars of the response
    
    # Check if redirected
    print(f"Final URL: {response.url}")

if __name__ == "__main__":
    test_buy_route()
