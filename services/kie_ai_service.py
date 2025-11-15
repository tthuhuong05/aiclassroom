# services/kie_ai_service.py
"""
KIE AI Service - Tích hợp KIE AI để tạo hình ảnh
"""

import os
import requests
import json
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from PIL import Image
import io

class KIEAIService:
    """Service để tích hợp KIE AI tạo hình ảnh"""
    
    def __init__(self):
        self.api_key = os.getenv("KIE_AI_KEY")
        self.base_url = "https://api.kie.ai/v1"  # Cập nhật URL thực tế của KIE AI
        self.model = "kie-image-generation"  # Model tạo hình ảnh của KIE AI
    
    def is_available(self) -> bool:
        """Kiểm tra xem KIE AI có khả dụng không"""
        return self.api_key is not None and self.api_key != ""
    
    def generate_image(self, prompt: str, style: str = "realistic", 
                      size: str = "1024x1024", quality: str = "high") -> Optional[Dict[str, Any]]:
        """
        Tạo hình ảnh sử dụng KIE AI
        Args:
            prompt: Text prompt để tạo hình ảnh
            style: Style của hình ảnh (realistic, cartoon, educational)
            size: Kích thước hình ảnh
            quality: Chất lượng hình ảnh
        Returns:
            Dict chứa success status và file_path nếu thành công
        """
        if not self.is_available():
            return {"success": False, "error": "KIE AI API key chưa được cấu hình"}
        
        # Thử các endpoint có thể có
        endpoints = [
            f"{self.base_url}/images/generations",
            f"{self.base_url}/generate",
            f"{self.base_url}/text-to-image",
            f"{self.base_url}/image-generation"
        ]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Cải thiện prompt
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        data = {
            "prompt": enhanced_prompt,
            "model": self.model,
            "size": size,
            "quality": quality,
            "num_images": 1
        }
        
        for endpoint in endpoints:
            try:
                print(f"Trying KIE AI endpoint: {endpoint}")
                response = requests.post(endpoint, json=data, headers=headers, timeout=30)
                
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Xử lý response tùy theo format của KIE AI
                    image_url = self._extract_image_url(result)
                    
                    if image_url:
                        # Tải hình ảnh về local
                        image_path = self._download_image(image_url)
                        
                        if image_path:
                            return {
                                "success": True,
                                "file_path": image_path,
                                "url": image_url,
                                "prompt": enhanced_prompt,
                                "style": style,
                                "service": "KIE AI",
                                "source": "generation"
                            }
                
                elif response.status_code == 401:
                    print("ERROR: Unauthorized - API key có thể không hợp lệ")
                elif response.status_code == 404:
                    print("ERROR: Not found - Endpoint không tồn tại")
                elif response.status_code == 400:
                    print("ERROR: Bad request - Dữ liệu không đúng format")
                    print(f"Response: {response.text[:200]}...")
                else:
                    print(f"ERROR: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print("ERROR: Request timeout")
            except requests.exceptions.ConnectionError:
                print("ERROR: Connection error")
            except Exception as e:
                print(f"ERROR: {e}")
        
        return {"success": False, "error": "Tất cả endpoint KIE AI đều không hoạt động"}
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """Cải thiện prompt cho KIE AI"""
        style_keywords = {
            "realistic": "photorealistic, high quality, detailed, professional",
            "educational": "educational illustration, clear, informative, professional",
            "technical": "technical diagram, professional, clear, detailed",
            "business": "business professional, corporate, clean, modern"
        }
        
        style_desc = style_keywords.get(style, style_keywords["realistic"])
        enhanced = f"{prompt}, {style_desc}, 8k resolution, sharp focus"
        
        return enhanced
    
    def _extract_image_url(self, response_data: Dict) -> Optional[str]:
        """Trích xuất URL hình ảnh từ response của KIE AI"""
        try:
            # Thử các format response có thể có
            if "data" in response_data:
                if isinstance(response_data["data"], list) and len(response_data["data"]) > 0:
                    return response_data["data"][0].get("url")
                elif isinstance(response_data["data"], dict):
                    return response_data["data"].get("url")
            
            if "images" in response_data:
                if isinstance(response_data["images"], list) and len(response_data["images"]) > 0:
                    return response_data["images"][0].get("url")
            
            if "url" in response_data:
                return response_data["url"]
            
            if "image_url" in response_data:
                return response_data["image_url"]
            
            if "result" in response_data:
                return response_data["result"].get("url")
            
            return None
            
        except Exception as e:
            print(f"Error extracting image URL: {e}")
            return None
    
    def _download_image(self, image_url: str) -> Optional[str]:
        """Tải hình ảnh từ URL về local"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Tạo file tạm
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            temp_file.write(response.content)
            temp_file.close()
            
            # Kiểm tra và cải thiện hình ảnh
            try:
                with Image.open(temp_file.name) as img:
                    # Convert sang RGB nếu cần
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize nếu cần (tối ưu cho video)
                    if img.size[0] > 1920 or img.size[1] > 1080:
                        img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    
                    # Lưu lại
                    img.save(temp_file.name, 'JPEG', quality=95)
                    
                print(f"Downloaded and optimized KIE AI image: {temp_file.name}")
                return temp_file.name
                
            except Exception as e:
                print(f"Error processing KIE AI image: {e}")
                return temp_file.name
                
        except Exception as e:
            print(f"Error downloading KIE AI image: {e}")
            return None
    
    def analyze_content_for_images(self, content: str) -> List[str]:
        """Phân tích nội dung để tạo prompts hình ảnh phù hợp"""
        try:
            # Sử dụng AI để phân tích nội dung và tạo prompts
            from ai_gemini import _ensure
            
            if not _ensure():
                return self._fallback_image_prompts(content)
            
            import google.generativeai as genai
            
            prompt = f"""
            Phân tích nội dung dưới đây và tạo 3-5 prompts để tạo hình ảnh minh họa phù hợp với KIE AI:
            
            NỘI DUNG:
            {content.strip()}
            
            YÊU CẦU:
            - Tạo prompts cụ thể để tạo hình ảnh phù hợp với nội dung
            - Ưu tiên hình ảnh thực tế, biểu đồ, case study, ví dụ cụ thể
            - Tránh hình ảnh trừu tượng hoặc không liên quan
            - Mỗi prompt phải mô tả rõ ràng hình ảnh cần tạo
            - Sử dụng tiếng Anh cho prompts
            
            Trả về danh sách prompts, mỗi prompt trên một dòng:
            """
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            if response.text:
                prompts = [line.strip() for line in response.text.split('\n') if line.strip()]
                return prompts[:5]  # Giới hạn 5 prompts
            else:
                return self._fallback_image_prompts(content)
                
        except Exception as e:
            print(f"Error analyzing content for KIE AI: {e}")
            return self._fallback_image_prompts(content)
    
    def _fallback_image_prompts(self, content: str) -> List[str]:
        """Fallback tạo prompts khi AI không khả dụng"""
        import re
        
        # Trích xuất từ khóa quan trọng
        words = re.findall(r'\b[A-Za-zÀ-ỹ0-9\-]+\b', content)
        important_words = [w for w in words if len(w) >= 4][:10]
        
        # Tạo prompts đơn giản
        prompts = []
        for word in important_words[:3]:
            prompts.append(f"{word.lower()} professional")
        
        # Thêm prompts chung
        prompts.extend([
            "educational content",
            "professional presentation",
            "business meeting",
            "technology innovation"
        ])
        
        return prompts[:5]

# Service instance
kie_ai_service = KIEAIService()

def is_kie_ai_available() -> bool:
    """Kiểm tra xem KIE AI có khả dụng không"""
    return kie_ai_service.is_available()

def generate_kie_ai_image(prompt: str, style: str = "realistic") -> Optional[Dict[str, Any]]:
    """Function tiện ích để tạo hình ảnh với KIE AI"""
    return kie_ai_service.generate_image(prompt, style)

def analyze_content_for_kie_images(content: str) -> List[str]:
    """Function tiện ích để phân tích nội dung cho hình ảnh KIE AI"""
    return kie_ai_service.analyze_content_for_images(content)
