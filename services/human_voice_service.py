# services/human_voice_service.py
"""
Human Voice Service - Tích hợp giọng nói người thật
"""

import os
import tempfile
import requests
import json
from typing import Optional, Dict, Any
import uuid

class HumanVoiceService:
    """Service để tích hợp giọng nói người thật"""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def is_available(self) -> bool:
        """Kiểm tra xem service có khả dụng không"""
        return self.api_key is not None and len(self.api_key) > 0
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Lấy danh sách giọng nói có sẵn"""
        if not self.is_available():
            return {"error": "API key not configured"}
        
        try:
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            response = requests.get(f"{self.base_url}/voices", headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def synthesize_speech(self, text: str, voice_id: Optional[str] = None, 
                         output_path: str = None) -> Dict[str, Any]:
        """
        Tạo giọng nói người thật từ text
        
        Args:
            text: Nội dung cần đọc
            voice_id: ID giọng nói (mặc định sử dụng voice_id của class)
            output_path: Đường dẫn file output (mặc định tạo file tạm)
        
        Returns:
            Dict với thông tin về file audio đã tạo
        """
        if not self.is_available():
            return {"error": "ElevenLabs API key not configured"}
        
        if voice_id is None:
            voice_id = self.voice_id
        
        if output_path is None:
            # Tạo file tạm
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"human_voice_{uuid.uuid4().hex[:8]}.mp3")
        
        try:
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",  # Model mới nhất cho giọng tự nhiên hơn
                "voice_settings": {
                    "stability": 0.7,  # Giảm để tự nhiên hơn, tránh máy
                    "similarity_boost": 0.9,  # Tăng để giống người thật hơn
                    "style": 0.7,  # Tăng biểu cảm tự nhiên, giống người nói thật
                    "use_speaker_boost": True  # Tăng chất lượng giọng người thật
                }
            }
            
            # Add timeout để tránh treo
            response = requests.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                json=data,
                headers=headers,
                timeout=60  # 60 giây timeout cho mỗi API call
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                return {
                    "success": True,
                    "file_path": output_path,
                    "duration": self._estimate_duration(text),
                    "voice_id": voice_id
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _estimate_duration(self, text: str) -> float:
        """Ước tính thời lượng audio dựa trên số từ"""
        words = len(text.split())
        # Giả sử tốc độ đọc 150 từ/phút
        return (words / 150.0) * 60.0
    
    def get_voice_info(self, voice_id: str = None) -> Dict[str, Any]:
        """Lấy thông tin về giọng nói"""
        if voice_id is None:
            voice_id = self.voice_id
        
        if not self.is_available():
            return {"error": "API key not configured"}
        
        try:
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            response = requests.get(f"{self.base_url}/voices/{voice_id}", headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# Global instance
human_voice_service = HumanVoiceService()

def get_human_voice_service() -> HumanVoiceService:
    """Lấy instance của HumanVoiceService"""
    return human_voice_service

def synthesize_human_voice(text: str, voice_id: str = None, output_path: str = None) -> Dict[str, Any]:
    """
    Function tiện ích để tạo giọng nói người thật
    
    Args:
        text: Nội dung cần đọc
        voice_id: ID giọng nói
        output_path: Đường dẫn file output
    
    Returns:
        Dict với thông tin về file audio
    """
    service = get_human_voice_service()
    return service.synthesize_speech(text, voice_id, output_path)

def is_human_voice_available() -> bool:
    """Kiểm tra xem giọng nói người thật có khả dụng không"""
    service = get_human_voice_service()
    return service.is_available()
