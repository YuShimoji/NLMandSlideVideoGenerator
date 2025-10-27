import urllib.request

try:
    response = urllib.request.urlopen('http://localhost:8502')
    print("Success: Streamlit is accessible")
    print(f"Status: {response.status}")
except Exception as e:
    print(f"Error: {e}")
