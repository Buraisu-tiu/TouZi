import requests
import time

def test_finnhub_key(api_key):
    """Test a Finnhub API key by requesting a simple stock quote."""
    base_url = "https://finnhub.io/api/v1"
    headers = {"X-Finnhub-Token": api_key}
    
    # Test endpoints
    test_cases = [
        ("/quote?symbol=AAPL", "Apple stock quote"),
        ("/stock/symbol?exchange=US", "US stock symbols"),
    ]
    
    print(f"\nTesting API key: {api_key[:4]}...{api_key[-4:]}")
    print("-" * 50)
    
    for endpoint, description in test_cases:
        try:
            url = f"{base_url}{endpoint}"
            print(f"Testing {description}...")
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Success! Status code: {response.status_code}")
                print(f"Response data: {response.json()}\n")
            elif response.status_code == 401:
                print(f"❌ Error: Invalid API key (Status code: 401)\n")
                return False
            elif response.status_code == 429:
                print(f"⚠️ Rate limit exceeded (Status code: 429)")
                print("Waiting 30 seconds before next test...")
                time.sleep(30)
            else:
                print(f"❌ Error: Status code {response.status_code}")
                print(f"Response: {response.text}\n")
                return False
                
        except Exception as e:
            print(f"❌ Error testing endpoint: {str(e)}\n")
            return False
            
        time.sleep(1)  # Brief pause between tests
    
    return True

def main():
    api_keys = [
        "d0lbmthr01qhb027hm90d0lbmthr01qhb027hm9g",
        "d0lbn4hr01qhb027hnn0d0lbn4hr01qhb027hnng"
    ]
    
    print("Finnhub API Key Tester")
    print("=" * 50)
    
    working_keys = []
    
    for i, key in enumerate(api_keys, 1):
        print(f"\nTesting Key #{i}")
        if test_finnhub_key(key):
            working_keys.append(key)
    
    print("\nTest Results:")
    print("=" * 50)
    print(f"Total keys tested: {len(api_keys)}")
    print(f"Working keys: {len(working_keys)}")
    
    if working_keys:
        print("\nWorking API keys:")
        for i, key in enumerate(working_keys, 1):
            print(f"{i}. {key[:4]}...{key[-4:]}")
    else:
        print("\n❌ No working API keys found!")

if __name__ == "__main__":
    main()
