#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Gemini Models
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def test_gemini_models():
    """Test available Gemini models"""
    print("Testing Gemini Models...")
    
    try:
        import google.generativeai as genai
        
        # Configure API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        
        # List available models
        print("Available models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"  - {model.name}")
        
        # Test different models
        models_to_test = [
            "gemini-1.5-flash",
            "gemini-1.5-pro", 
            "gemini-pro",
            "gemini-1.0-pro",
            "gemini-1.5-flash-8b"
        ]
        
        for model_name in models_to_test:
            try:
                print(f"\nTesting model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello, test message")
                print(f"SUCCESS: {model_name} works!")
                print(f"Response: {response.text[:100]}...")
                return model_name
            except Exception as e:
                print(f"FAILED: {model_name} - {e}")
        
        return None
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    """Main function"""
    print("Gemini Models Test")
    print("=" * 30)
    
    working_model = test_gemini_models()
    
    if working_model:
        print(f"\nSUCCESS: Found working model: {working_model}")
        print("Update your code to use this model")
    else:
        print("\nERROR: No working Gemini models found")
        print("Check your API key and try again")

if __name__ == "__main__":
    main()
