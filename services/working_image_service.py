# services/working_image_service.py
"""
Working Image Generation Service - Sử dụng các dịch vụ thực sự hoạt động
"""

import os
import requests
import json
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from PIL import Image
import io

class WorkingImageService:
    """Service tạo hình ảnh sử dụng các dịch vụ thực sự hoạt động"""
    
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.stability_key = os.getenv("STABILITY_API_KEY")
    
    def is_available(self) -> bool:
        """Kiểm tra xem có dịch vụ nào khả dụng không"""
        return bool(self.pexels_key or self.unsplash_key or self.openai_key or self.stability_key)
    
    def generate_image(self, prompt: str, style: str = "realistic", 
                      size: str = "1024x1024", quality: str = "high") -> Optional[Dict[str, Any]]:
        """
        Tạo hình ảnh từ prompt sử dụng các dịch vụ hoạt động
        """
        if not self.is_available():
            print("No working image services available")
            return None
        
        # Thử các dịch vụ theo thứ tự ưu tiên
        services = [
            ("Stability AI", self._try_stability_ai),
            ("OpenAI DALL-E", self._try_openai),
            ("Pexels", self._try_pexels),
            ("Unsplash", self._try_unsplash)
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
    
    def _try_stability_ai(self, prompt: str, style: str, size: str, quality: str) -> Optional[Dict[str, Any]]:
        """Thử tạo hình ảnh với Stability AI"""
        if not self.stability_key:
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.stability_key}",
                "Content-Type": "application/json"
            }
            
            # Cải thiện prompt cho Stability AI
            enhanced_prompt = self._enhance_prompt_for_stability(prompt, style)
            
            data = {
                "text_prompts": [{"text": enhanced_prompt}],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30
            }
            
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if "artifacts" in result and len(result["artifacts"]) > 0:
                    artifact = result["artifacts"][0]
                    
                    # Decode base64 image
                    import base64
                    image_data = base64.b64decode(artifact["base64"])
                    
                    # Save to temp file
                    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_file.write(image_data)
                    temp_file.close()
                    
                    return {
                        "success": True,
                        "file_path": temp_file.name,
                        "prompt": enhanced_prompt,
                        "style": style,
                        "service": "Stability AI",
                        "source": "generation"
                    }
            
            return None
            
        except Exception as e:
            print(f"Stability AI error: {e}")
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
    
    def _try_pexels(self, prompt: str, style: str, size: str, quality: str) -> Optional[Dict[str, Any]]:
        """Thử tìm hình ảnh với Pexels"""
        if not self.pexels_key:
            return None
        
        try:
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
        """Thử tìm hình ảnh với Unsplash"""
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
    
    def _enhance_prompt_for_stability(self, prompt: str, style: str) -> str:
        """Cải thiện prompt cho Stability AI"""
        style_keywords = {
            "realistic": "photorealistic, high quality, detailed, professional photography",
            "educational": "educational illustration, clear, informative, professional",
            "technical": "technical diagram, professional, clear, detailed",
            "business": "business professional, corporate, clean, modern"
        }
        
        style_desc = style_keywords.get(style, style_keywords["realistic"])
        enhanced = f"{prompt}, {style_desc}, 8k resolution, sharp focus, well-lit"
        
        return enhanced
    
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
    
    def _improve_prompt_for_search(self, prompt: str) -> str:
        """Cải thiện prompt cho tìm kiếm hình ảnh"""
        # Mapping từ khóa chuyên môn sang từ khóa có hình ảnh
        keyword_mapping = {
            # Công nghệ thông tin
            "machine learning": "machine learning technology",
            "deep learning": "neural network technology", 
            "artificial intelligence": "AI technology",
            "data science": "data analysis charts",
            "programming": "coding computer screen",
            "algorithm": "computer algorithm visualization",
            "database": "database management system",
            "network": "computer network diagram",
            "security": "cybersecurity protection",
            "software": "software development",
            "web development": "web development coding",
            
            # Kinh doanh
            "marketing": "digital marketing strategy",
            "finance": "financial analysis charts",
            "management": "business management team",
            "strategy": "business strategy planning",
            "leadership": "business leadership",
            "entrepreneurship": "startup business",
            "sales": "sales presentation",
            
            # Giáo dục
            "education": "online learning platform",
            "teaching": "teacher classroom",
            "learning": "student studying",
            "research": "scientific research lab",
            "university": "university campus",
            "student": "student studying",
            
            # Khoa học
            "science": "scientific laboratory",
            "chemistry": "chemistry lab equipment",
            "physics": "physics experiment",
            "biology": "biology laboratory",
            "mathematics": "mathematical equations",
            "engineering": "engineering design",
            
            # Y tế
            "medicine": "medical healthcare",
            "health": "healthcare professionals",
            "treatment": "medical treatment",
            "diagnosis": "medical diagnosis",
            "hospital": "modern hospital",
            
            # Nghệ thuật
            "art": "artistic creativity",
            "design": "graphic design work",
            "music": "musical instruments",
            "literature": "books reading",
            "photography": "professional photography",
        }
        
        # Loại bỏ các từ không cần thiết
        words_to_remove = ["create", "generate", "make", "design", "illustration", "image", "picture"]
        
        improved = prompt.lower()
        for word in words_to_remove:
            improved = improved.replace(word, "")
        
        # Kiểm tra mapping trực tiếp
        for key, value in keyword_mapping.items():
            if key in improved:
                return value
        
        # Thêm context nếu cần
        if len(improved.split()) == 1:
            # Từ đơn - thêm context
            if improved in ["data", "analysis", "study", "research"]:
                return f"{improved} professional work"
            elif improved in ["system", "process", "method"]:
                return f"{improved} workflow diagram"
            elif improved in ["theory", "concept", "principle"]:
                return f"{improved} explanation illustration"
            elif improved in ["technology", "tech"]:
                return "modern technology"
            elif improved in ["business"]:
                return "business professional"
            elif improved in ["education"]:
                return "education learning"
        
        return improved.strip()
    
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
            Analyze the following content and create 3-5 prompts for finding/creating relevant illustration images:
            
            CONTENT:
            {content.strip()}
            
            IMPORTANT REQUIREMENTS:
            - Create SPECIFIC and ACCURATE prompts to find images that match the content
            - Prioritize REALISTIC images, CHARTS, CASE STUDIES, SPECIFIC EXAMPLES
            - Avoid ABSTRACT or IRRELEVANT images
            - Each prompt must CLEARLY DESCRIBE the image to find/create
            - Use ENGLISH for prompts
            - Focus on MAIN CONCEPTS and REAL-WORLD APPLICATIONS
            
            GOOD PROMPT EXAMPLES:
            - "machine learning algorithm visualization"
            - "data analysis charts and graphs"
            - "business strategy meeting room"
            - "scientific research laboratory"
            - "educational technology classroom"
            
            Return a list of prompts, one prompt per line:
            """
            
            model = genai.GenerativeModel("gemini-2.5-flash")
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
working_image_service = WorkingImageService()

def is_working_image_available() -> bool:
    """Kiểm tra xem có dịch vụ tạo hình ảnh nào khả dụng không"""
    return working_image_service.is_available()

def generate_working_image(prompt: str, style: str = "realistic") -> Optional[Dict[str, Any]]:
    """Function tiện ích để tạo hình ảnh"""
    return working_image_service.generate_image(prompt, style)

def analyze_content_for_working_images(content: str) -> List[str]:
    """Function tiện ích để phân tích nội dung cho hình ảnh"""
    return working_image_service.analyze_content_for_images(content)
