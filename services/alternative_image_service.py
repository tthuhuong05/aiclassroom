# services/alternative_image_service.py
"""
Alternative Image Generation Service - Sử dụng các dịch vụ khác khi LunaAI không khả dụng
"""

import os
import requests
import json
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from PIL import Image
import io

class AlternativeImageService:
    """Service tạo hình ảnh thay thế khi LunaAI không khả dụng"""
    
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
    
    def is_available(self) -> bool:
        """Kiểm tra xem có dịch vụ nào khả dụng không"""
        return bool(self.pexels_key or self.unsplash_key or self.openai_key)
    
    def generate_image(self, prompt: str, style: str = "realistic", 
                      size: str = "1024x1024", quality: str = "high") -> Optional[Dict[str, Any]]:
        """
        Tạo hình ảnh từ prompt sử dụng các dịch vụ thay thế
        """
        if not self.is_available():
            print("No image generation services available")
            return None
        
        # Thử các dịch vụ theo thứ tự ưu tiên
        services = [
            ("Pexels", self._try_pexels),
            ("Unsplash", self._try_unsplash),
            ("OpenAI DALL-E", self._try_openai)
        ]
        
        for service_name, service_func in services:
            try:
                print(f"Trying {service_name} for: {prompt[:50]}...")
                result = service_func(prompt, style, size, quality)
                
                if result and result.get("success"):
                    print(f"SUCCESS: {service_name} generated image")
                    return result
                else:
                    print(f"FAILED: {service_name} could not generate image")
                    
            except Exception as e:
                print(f"ERROR: {service_name} failed: {e}")
        
        print("All image generation services failed")
        return None
    
    def _try_pexels(self, prompt: str, style: str, size: str, quality: str) -> Optional[Dict[str, Any]]:
        """Thử tạo hình ảnh với Pexels"""
        if not self.pexels_key:
            return None
        
        try:
            # Pexels không tạo hình ảnh mà chỉ tìm kiếm
            # Nhưng chúng ta có thể tìm hình ảnh phù hợp
            headers = {"Authorization": self.pexels_key}
            
            # Cải thiện prompt cho tìm kiếm
            search_query = self._improve_prompt_for_search(prompt)
            
            response = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": search_query, "per_page": 1, "orientation": "landscape"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    photo = data["photos"][0]
                    image_url = photo["src"]["large"]
                    
                    # Tải hình ảnh về local
                    image_path = self._download_image(image_url)
                    
                    if image_path:
                        return {
                            "success": True,
                            "file_path": image_path,
                            "url": image_url,
                            "prompt": prompt,
                            "style": style,
                            "service": "Pexels",
                            "source": "search"
                        }
            
            return None
            
        except Exception as e:
            print(f"Pexels error: {e}")
            return None
    
    def _try_unsplash(self, prompt: str, style: str, size: str, quality: str) -> Optional[Dict[str, Any]]:
        """Thử tạo hình ảnh với Unsplash"""
        if not self.unsplash_key:
            return None
        
        try:
            headers = {"Authorization": f"Client-ID {self.unsplash_key}"}
            
            # Cải thiện prompt cho tìm kiếm
            search_query = self._improve_prompt_for_search(prompt)
            
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": search_query, "per_page": 1, "orientation": "landscape"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    photo = data["results"][0]
                    image_url = photo["urls"]["regular"]
                    
                    # Tải hình ảnh về local
                    image_path = self._download_image(image_url)
                    
                    if image_path:
                        return {
                            "success": True,
                            "file_path": image_path,
                            "url": image_url,
                            "prompt": prompt,
                            "style": style,
                            "service": "Unsplash",
                            "source": "search"
                        }
            
            return None
            
        except Exception as e:
            print(f"Unsplash error: {e}")
            return None
    
    def _try_openai(self, prompt: str, style: str, size: str, quality: str) -> Optional[Dict[str, Any]]:
        """Thử tạo hình ảnh với OpenAI DALL-E"""
        if not self.openai_key:
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            
            # Cải thiện prompt cho DALL-E
            enhanced_prompt = self._enhance_prompt_for_dalle(prompt, style)
            
            data = {
                "prompt": enhanced_prompt,
                "n": 1,
                "size": size,
                "quality": quality,
                "response_format": "url"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if "data" in result and len(result["data"]) > 0:
                    image_data = result["data"][0]
                    
                    # Tải hình ảnh về local
                    image_path = self._download_image(image_data.get("url"))
                    
                    if image_path:
                        return {
                            "success": True,
                            "file_path": image_path,
                            "url": image_data.get("url"),
                            "prompt": enhanced_prompt,
                            "style": style,
                            "service": "OpenAI DALL-E",
                            "source": "generation"
                        }
            
            return None
            
        except Exception as e:
            print(f"OpenAI DALL-E error: {e}")
            return None
    
    def _improve_prompt_for_search(self, prompt: str) -> str:
        """Cải thiện prompt cho tìm kiếm hình ảnh"""
        # Loại bỏ các từ không cần thiết
        words_to_remove = ["create", "generate", "make", "design", "illustration", "image"]
        
        improved = prompt.lower()
        for word in words_to_remove:
            improved = improved.replace(word, "")
        
        # Thêm từ khóa tìm kiếm tốt
        if "machine learning" in improved:
            improved = "machine learning technology"
        elif "business" in improved:
            improved = "business professional"
        elif "education" in improved:
            improved = "education learning"
        
        return improved.strip()
    
    def _enhance_prompt_for_dalle(self, prompt: str, style: str) -> str:
        """Cải thiện prompt cho DALL-E"""
        style_keywords = {
            "realistic": "photorealistic, high quality, detailed",
            "educational": "educational illustration, clear, informative",
            "technical": "technical diagram, professional, clear",
            "business": "business professional, corporate, clean"
        }
        
        style_desc = style_keywords.get(style, style_keywords["realistic"])
        enhanced = f"{prompt}, {style_desc}, 8k resolution, sharp focus"
        
        return enhanced
    
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
                    
                print(f"Downloaded and optimized image: {temp_file.name}")
                return temp_file.name
                
            except Exception as e:
                print(f"Error processing image: {e}")
                return temp_file.name
                
        except Exception as e:
            print(f"Error downloading image: {e}")
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
            Phân tích nội dung dưới đây và tạo 3-5 prompts để tìm kiếm hình ảnh minh họa phù hợp:
            
            NỘI DUNG:
            {content.strip()}
            
            YÊU CẦU:
            - Tạo prompts cụ thể để tìm kiếm hình ảnh phù hợp với nội dung
            - Ưu tiên hình ảnh thực tế, biểu đồ, case study, ví dụ cụ thể
            - Tránh hình ảnh trừu tượng hoặc không liên quan
            - Mỗi prompt phải mô tả rõ ràng hình ảnh cần tìm
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
            print(f"Error analyzing content: {e}")
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
alternative_image_service = AlternativeImageService()

def is_alternative_image_available() -> bool:
    """Kiểm tra xem có dịch vụ tạo hình ảnh thay thế nào khả dụng không"""
    return alternative_image_service.is_available()

def generate_alternative_image(prompt: str, style: str = "realistic") -> Optional[Dict[str, Any]]:
    """Function tiện ích để tạo hình ảnh thay thế"""
    return alternative_image_service.generate_image(prompt, style)

def analyze_content_for_alternative_images(content: str) -> List[str]:
    """Function tiện ích để phân tích nội dung cho hình ảnh thay thế"""
    return alternative_image_service.analyze_content_for_images(content)
