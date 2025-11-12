#!/usr/bin/env python3
"""
Test AI Quiz với Gemini
"""

import requests
import json
import time

def test_ai_quiz_api():
    """Test API AI Quiz"""
    print("Testing AI Quiz API...")
    
    # Test data
    test_subtitle = """
    It's like the loudspeaker of JavaScript. It outputs directly into the HTML document. 
    This is a fundamental concept in web development. JavaScript can manipulate the DOM 
    and create interactive web pages. The document object represents the entire HTML page.
    """
    
    payload = {
        "subtitle_text": test_subtitle,
        "time_range": "0-50 seconds",
        "language": "vi"
    }
    
    try:
        # Test API endpoint
        response = requests.post(
            "http://localhost:5000/api/ai-quiz/generate-from-subtitles",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("API Response:")
            try:
                print(f"   Question: {data.get('question', 'N/A')}")
                print(f"   Options: {data.get('options', [])}")
                print(f"   Correct Index: {data.get('correct_index', 'N/A')}")
                print(f"   Explanation: {data.get('explanation', 'N/A')}")
            except UnicodeEncodeError:
                print("   Response contains non-ASCII characters")
                print("   API is working but cannot display content")
            return True
        else:
            print(f"API Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Khong the ket noi den server. Hay chay Flask app truoc.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_flask_app():
    """Kiểm tra Flask app có chạy không"""
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Hàm chính"""
    print("TEST AI QUIZ VOI GEMINI")
    print("="*50)
    
    if not test_flask_app():
        print("Flask app chua chay!")
        print("Hay chay: python app.py")
        return
    
    print("Flask app dang chay")
    
    # Test AI Quiz API
    if test_ai_quiz_api():
        print("\nTest thanh cong!")
        print("AI Quiz da hoat dong voi Gemini")
    else:
        print("\nTest that bai!")
        print("Kiem tra:")
        print("   - GEMINI_API_KEY co duoc set khong")
        print("   - Internet connection")
        print("   - Flask app logs")

if __name__ == "__main__":
    main()
