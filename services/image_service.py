# services/image_service.py
"""
Image Service - Tìm và thêm hình ảnh phù hợp vào video
"""

import os
import requests
import json
import tempfile
from typing import List, Dict, Any, Optional
import uuid
from PIL import Image, ImageDraw, ImageFont
import textwrap

class ImageService:
    """Service để tìm và tạo hình ảnh phù hợp"""
    
    def __init__(self):
        self.unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
    
    def is_available(self) -> bool:
        """Kiểm tra xem service có khả dụng không"""
        return (self.unsplash_access_key is not None and len(self.unsplash_access_key) > 0) or \
               (self.pexels_api_key is not None and len(self.pexels_api_key) > 0)
    
    def search_images(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm kiếm hình ảnh phù hợp với nội dung
        
        Args:
            query: Từ khóa tìm kiếm
            count: Số lượng hình ảnh cần lấy
        
        Returns:
            List các dict chứa thông tin hình ảnh
        """
        images = []
        
        # Thử Unsplash trước
        if self.unsplash_access_key:
            unsplash_images = self._search_unsplash(query, count)
            images.extend(unsplash_images)
        
        # Thử Pexels nếu cần thêm
        if len(images) < count and self.pexels_api_key:
            pexels_images = self._search_pexels(query, count - len(images))
            images.extend(pexels_images)
        
        return images[:count]
    
    def _search_unsplash(self, query: str, count: int) -> List[Dict[str, Any]]:
        """Tìm kiếm trên Unsplash"""
        try:
            headers = {
                "Authorization": f"Client-ID {self.unsplash_access_key}"
            }
            
            params = {
                "query": query,
                "per_page": count,
                "orientation": "landscape"
            }
            
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                images = []
                for photo in data.get("results", []):
                    images.append({
                        "url": photo["urls"]["regular"],
                        "download_url": photo["urls"]["full"],
                        "description": photo.get("description", ""),
                        "author": photo["user"]["name"],
                        "source": "unsplash"
                    })
                return images
        except Exception as e:
            print(f"Unsplash search failed: {e}")
        
        return []
    
    def _search_pexels(self, query: str, count: int) -> List[Dict[str, Any]]:
        """Tìm kiếm trên Pexels"""
        try:
            headers = {
                "Authorization": self.pexels_api_key
            }
            
            params = {
                "query": query,
                "per_page": count,
                "orientation": "landscape"
            }
            
            response = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                images = []
                for photo in data.get("photos", []):
                    images.append({
                        "url": photo["src"]["large"],
                        "download_url": photo["src"]["original"],
                        "description": photo.get("alt", ""),
                        "author": photo["photographer"],
                        "source": "pexels"
                    })
                return images
        except Exception as e:
            print(f"Pexels search failed: {e}")
        
        return []
    
    def download_image(self, image_url: str, output_path: str = None) -> Dict[str, Any]:
        """
        Tải hình ảnh về máy
        
        Args:
            image_url: URL hình ảnh
            output_path: Đường dẫn lưu file
        
        Returns:
            Dict với thông tin về file đã tải
        """
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"image_{uuid.uuid4().hex[:8]}.jpg")
        
        try:
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Lấy thông tin hình ảnh
            with Image.open(output_path) as img:
                width, height = img.size
            
            return {
                "success": True,
                "file_path": output_path,
                "width": width,
                "height": height,
                "size": os.path.getsize(output_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_enhanced_slide(self, text: str, image_path: str = None, 
                            width: int = 1280, height: int = 720) -> str:
        """
        Tạo slide với hình ảnh nền và text overlay
        
        Args:
            text: Nội dung text
            image_path: Đường dẫn hình ảnh nền
            width: Chiều rộng slide
            height: Chiều cao slide
        
        Returns:
            Đường dẫn file slide đã tạo
        """
        # Tạo slide mới
        slide = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(slide)
        
        # Thêm hình ảnh nền nếu có
        if image_path and os.path.exists(image_path):
            try:
                bg_image = Image.open(image_path)
                # Resize và crop để fit
                bg_image = self._fit_image(bg_image, width, height)
                slide.paste(bg_image, (0, 0))
                
                # Thêm overlay để text dễ đọc
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 120))
                slide = Image.alpha_composite(slide.convert("RGBA"), overlay).convert("RGB")
            except Exception as e:
                print(f"Failed to add background image: {e}")
        
        # Thêm text
        self._add_text_to_slide(draw, text, width, height)
        
        # Lưu slide
        output_path = os.path.join(tempfile.gettempdir(), f"enhanced_slide_{uuid.uuid4().hex[:8]}.png")
        slide.save(output_path)
        
        return output_path
    
    def _fit_image(self, image: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """Fit hình ảnh vào kích thước mục tiêu"""
        # Tính tỷ lệ
        ratio = min(target_width / image.width, target_height / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)
        
        # Resize
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop để fit chính xác
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        return image.crop((left, top, right, bottom))
    
    def _add_text_to_slide(self, draw: ImageDraw.Draw, text: str, width: int, height: int):
        """Thêm text vào slide với styling đẹp"""
        try:
            # Font lớn hơn
            font_size = 48
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("calibri.ttf", font_size)
                except:
                    font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Wrap text
        lines = textwrap.wrap(text, width=50)
        
        # Vẽ text với shadow effect
        y = 120
        for line in lines[:12]:  # Giới hạn số dòng
            if not line.strip():
                y += 20
                continue
            
            # Shadow
            draw.text((102, y+2), line, fill=(0, 0, 0, 120), font=font)
            # Text chính
            draw.text((100, y), line, fill=(255, 255, 255), font=font)
            y += 50

# Global instance
image_service = ImageService()

def get_image_service() -> ImageService:
    """Lấy instance của ImageService"""
    return image_service

def search_images_for_content(content: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    Function tiện ích để tìm hình ảnh phù hợp với nội dung
    
    Args:
        content: Nội dung cần tìm hình ảnh
        count: Số lượng hình ảnh
    
    Returns:
        List các dict chứa thông tin hình ảnh
    """
    service = get_image_service()
    
    # Sử dụng AI phân tích thông minh để tạo query
    try:
        from services.smart_image_analyzer_simple import create_smart_image_query
        query = create_smart_image_query(content, "educational")
        print(f"Smart image query: {query}")
    except ImportError:
        # Fallback: Tạo query từ nội dung (cải thiện)
        words = content.split()[:5]  # Lấy 5 từ đầu
        query = " ".join(words) + " illustration concept"
        print(f"Using fallback query: {query}")
    
    return service.search_images(query, count)

def is_image_service_available() -> bool:
    """Kiểm tra xem image service có khả dụng không"""
    service = get_image_service()
    return service.is_available()
