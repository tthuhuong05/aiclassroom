#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script load biến môi trường từ file .env
"""

import os
from pathlib import Path

def load_env_file():
    """Load biến môi trường từ file .env"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("File .env khong ton tai!")
        print("Chay: python setup_api_keys.py de tao file .env")
        return False
    
    print(f"Loading {env_file}...")
    
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    loaded_count = 0
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value
            loaded_count += 1
    
    print(f"Da load {loaded_count} bien moi truong")
    
    # Hiển thị các biến quan trọng
    important_vars = ['ELEVENLABS_API_KEY', 'GEMINI_API_KEY', 'LUNA_API_KEY', 'REQUIRE_HUMAN_VOICE']
    
    print("\nCac bien quan trong:")
    for var in important_vars:
        value = os.environ.get(var)
        if value:
            if var in ['ELEVENLABS_API_KEY', 'GEMINI_API_KEY', 'LUNA_API_KEY']:
                print(f"   {var}: {value[:10]}...")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: Chua thiet lap")
    
    return True

if __name__ == "__main__":
    load_env_file()
