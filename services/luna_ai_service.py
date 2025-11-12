# services/luna_ai_service.py
"""
LunaAI Service - Tích hợp LunaAI để tạo hình ảnh chân thật
"""

import os
import requests
import json
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from PIL import Image
import io

class LunaAIService:
    """Service để tích hợp LunaAI tạo hình ảnh"""
    
    def __init__(self):
        self.api_key = os.getenv("LUNA_API_KEY")
        self.base_url = "https://api.luna.ai/v1"  # Cập nhật URL thực tế của LunaAI
        self.model = "luna-vision"  # Model tạo hình ảnh của LunaAI
    
    def is_available(self) -> bool:
        """Kiểm tra xem LunaAI có khả dụng không"""
        return bool(self.api_key and len(self.api_key.strip()) > 0)
    
    def generate_image(self, prompt: str, style: str = "realistic", 
                      size: str = "1024x1024", quality: str = "high") -> Optional[Dict[str, Any]]:
        """
        Tạo hình ảnh từ prompt sử dụng LunaAI
        
        Args:
            prompt: Mô tả hình ảnh cần tạo
            style: Phong cách (realistic, artistic, professional, etc.)
            size: Kích thước hình ảnh
            quality: Chất lượng (high, medium, low)
        
        Returns:
            Dict chứa thông tin hình ảnh hoặc None nếu thất bại
        """
        if not self.is_available():
            print("LunaAI API key not configured")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Cải thiện prompt để có hình ảnh chân thật hơn
            enhanced_prompt = self._enhance_prompt_for_realistic_image(prompt, style)
            
            data = {
                "prompt": enhanced_prompt,
                "model": self.model,
                "size": size,
                "quality": quality,
                "style": style,
                "num_images": 1,
                "response_format": "url"  # Trả về URL hình ảnh
            }
            
            print(f"LunaAI generating image: {enhanced_prompt[:100]}...")
            
            response = requests.post(
                f"{self.base_url}/images/generations",
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
                            "size": size,
                            "quality": quality
                        }
                    else:
                        print("Could not download image to local")
                        return None
                else:
                    print("LunaAI did not return image")
                    return None
            else:
                print(f"LunaAI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"LunaAI generation error: {e}")
            return None
    
    def _enhance_prompt_for_realistic_image(self, prompt: str, style: str) -> str:
        """Cải thiện prompt để tạo hình ảnh chân thật hơn"""
        
        # Các từ khóa để tạo hình ảnh chân thật
        realistic_keywords = {
            "realistic": "photorealistic, high quality, detailed, professional photography",
            "educational": "educational illustration, clear, informative, professional",
            "technical": "technical diagram, professional, clear, detailed",
            "business": "business professional, corporate, clean, modern",
            "scientific": "scientific illustration, accurate, detailed, professional"
        }
        
        # Thêm từ khóa theo style
        style_keywords = realistic_keywords.get(style, realistic_keywords["realistic"])
        
        # Cải thiện prompt
        enhanced_prompt = f"{prompt}, {style_keywords}, 8k resolution, sharp focus, well-lit"
        
        # Loại bỏ các từ có thể gây ra hình ảnh không phù hợp
        enhanced_prompt = enhanced_prompt.replace("abstract", "concrete")
        enhanced_prompt = enhanced_prompt.replace("artistic", "realistic")
        
        return enhanced_prompt
    
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
                    
                print(f"✅ Downloaded and optimized image: {temp_file.name}")
                return temp_file.name
                
            except Exception as e:
                print(f"❌ Error processing image: {e}")
                return temp_file.name
                
        except Exception as e:
            print(f"❌ Error downloading image: {e}")
            return None
    
    def generate_multiple_images(self, prompts: List[str], style: str = "realistic") -> List[Dict[str, Any]]:
        """Tạo nhiều hình ảnh từ danh sách prompts"""
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"🎨 Generating image {i+1}/{len(prompts)}...")
            result = self.generate_image(prompt, style)
            
            if result:
                results.append(result)
            else:
                print(f"❌ Failed to generate image for: {prompt}")
        
        return results
    
    def analyze_content_for_images(self, content: str) -> List[str]:
        """Phân tích nội dung để tạo prompts hình ảnh phù hợp"""
        try:
            # Sử dụng AI để phân tích nội dung và tạo prompts
            from ai_gemini import _ensure
            
            if not _ensure():
                return self._fallback_image_prompts(content)
            
            import google.generativeai as genai
            
            prompt = f"""
            Phân tích nội dung dưới đây và tạo 3-5 prompts để tạo hình ảnh minh họa chân thật:
            
            NỘI DUNG:
            {content.strip()}
            
            YÊU CẦU:
            - Tạo prompts cụ thể để tạo hình ảnh chân thật, phù hợp với nội dung
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
            print(f"❌ Error analyzing content: {e}")
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
            prompts.append(f"Professional illustration of {word.lower()}, realistic, detailed")
        
        # Thêm prompts chung
        prompts.extend([
            "Educational content illustration, professional, clear",
            "Technical diagram, modern, detailed",
            "Professional presentation slide, clean design"
        ])
        
        return prompts[:5]

# Service instance
luna_ai_service = LunaAIService()

def is_luna_ai_available() -> bool:
    """Kiểm tra xem LunaAI có khả dụng không"""
    return luna_ai_service.is_available()

def generate_luna_image(prompt: str, style: str = "realistic") -> Optional[Dict[str, Any]]:
    """Function tiện ích để tạo hình ảnh LunaAI"""
    return luna_ai_service.generate_image(prompt, style)

def analyze_content_for_luna_images(content: str) -> List[str]:
    """Function tiện ích để phân tích nội dung cho LunaAI"""
    return luna_ai_service.analyze_content_for_images(content)
