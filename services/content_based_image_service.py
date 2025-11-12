# services/content_based_image_service.py
"""
Content-Based Image Service - Tạo hình ảnh dựa trên nội dung cụ thể
"""

import os
import re
import json
import tempfile
import requests
import math
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap

class ContentBasedImageService:
    """Service tạo hình ảnh dựa trên nội dung cụ thể"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    def create_content_image(self, content: str, context: str = "educational", 
                           width: int = 1280, height: int = 720) -> Optional[str]:
        """
        Tạo hình ảnh dựa trên nội dung cụ thể
        
        Args:
            content: Nội dung text
            context: Ngữ cảnh (educational, technical, business)
            width: Chiều rộng hình ảnh
            height: Chiều cao hình ảnh
        
        Returns:
            Đường dẫn file hình ảnh được tạo
        """
        try:
            # Phân tích nội dung để tạo hình ảnh phù hợp
            image_concept = self._analyze_content_for_image(content, context)
            
            if not image_concept:
                print("Could not analyze content for image creation")
                return None
            
            # Tạo hình ảnh dựa trên concept
            image_path = self._create_concept_image(image_concept, width, height)
            
            return image_path
            
        except Exception as e:
            print(f"Error creating content-based image: {e}")
            return None
    
    def _analyze_content_for_image(self, content: str, context: str) -> Optional[Dict[str, Any]]:
        """Phân tích nội dung để tạo concept hình ảnh"""
        
        try:
            # Sử dụng Gemini AI để phân tích
            if self.gemini_api_key:
                return self._analyze_with_gemini(content, context)
            
            # Fallback: Phân tích thủ công
            return self._analyze_manually(content, context)
            
        except Exception as e:
            print(f"Error analyzing content: {e}")
            return self._analyze_manually(content, context)
    
    def _analyze_with_gemini(self, content: str, context: str) -> Optional[Dict[str, Any]]:
        """Phân tích nội dung bằng Gemini AI"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
Bạn là chuyên gia thiết kế hình ảnh cho video giáo dục. Hãy phân tích nội dung và tạo concept hình ảnh phù hợp.

NỘI DUNG:
{content[:1500]}

NGỮ CẢNH: {context}

NHIỆM VỤ:
1. PHÂN TÍCH nội dung chính và khái niệm quan trọng
2. TẠO concept hình ảnh minh họa phù hợp
3. TUYỆT ĐỐI KHÔNG CÓ con người, khuôn mặt, chân dung, bàn tay, bàn chân
4. ƯU TIÊN: biểu đồ, sơ đồ, icon, illustration, concept art, abstract shapes
5. TẠO mô tả chi tiết về hình ảnh cần tạo

YÊU CẦU:
- Hình ảnh phải LIÊN QUAN trực tiếp đến nội dung
- TUYỆT ĐỐI KHÔNG CÓ con người, khuôn mặt, chân dung, bàn tay, bàn chân
- Phong cách: illustration, diagram, concept art, abstract, geometric
- Màu sắc phù hợp với ngữ cảnh
- Layout rõ ràng và dễ hiểu
- Chỉ sử dụng: shapes, charts, diagrams, icons, symbols, abstract elements

TRẢ VỀ JSON:
{{
  "main_concept": "khái niệm chính",
  "visual_elements": [
    {{
      "element": "tên element",
      "description": "mô tả chi tiết",
      "position": "vị trí trong hình",
      "style": "phong cách"
    }}
  ],
  "color_scheme": {{
    "primary": "màu chính",
    "secondary": "màu phụ",
    "accent": "màu nhấn"
  }},
  "layout": "mô tả layout tổng thể",
  "style": "illustration|diagram|concept|infographic|abstract",
  "mood": "professional|friendly|serious|creative"
}}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse JSON response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                    
                    # Validate result
                    if self._validate_image_concept(result):
                        return result
                        
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                
        except Exception as e:
            print(f"Gemini analysis failed: {e}")
        
        return None
    
    def _analyze_manually(self, content: str, context: str) -> Dict[str, Any]:
        """Phân tích thủ công khi AI không khả dụng"""
        
        # Tách từ khóa quan trọng
        words = re.findall(r'\b[A-Za-zÀ-ỹ]{4,}\b', content.lower())
        
        # Loại bỏ từ không quan trọng
        stop_words = {
            'của', 'và', 'trong', 'cho', 'với', 'từ', 'đến', 'là', 'có', 'được',
            'the', 'and', 'for', 'with', 'from', 'to', 'is', 'are', 'was', 'were',
            'this', 'that', 'these', 'those', 'can', 'will', 'should', 'would'
        }
        
        important_words = [w for w in words if w not in stop_words and len(w) > 4]
        
        # Tạo concept dựa trên từ khóa
        main_concept = important_words[0] if important_words else "concept"
        
        return {
            "main_concept": main_concept,
            "visual_elements": [
                {
                    "element": f"{main_concept} illustration",
                    "description": f"Central illustration representing {main_concept}",
                    "position": "center",
                    "style": "modern illustration"
                }
            ],
            "color_scheme": {
                "primary": "blue",
                "secondary": "green", 
                "accent": "purple"
            },
            "layout": "centered with supporting elements",
            "style": "illustration",
            "mood": "professional"
        }
    
    def _validate_image_concept(self, concept: Dict[str, Any]) -> bool:
        """Validate image concept"""
        required_fields = ['main_concept', 'visual_elements', 'color_scheme', 'layout', 'style']
        return all(field in concept for field in required_fields)
    
    def _create_concept_image(self, concept: Dict[str, Any], width: int, height: int) -> Optional[str]:
        """Tạo hình ảnh dựa trên concept"""
        try:
            # Tạo file tạm
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Tạo hình ảnh
            image = self._draw_concept_image(concept, width, height)
            
            if image:
                image.save(temp_path, 'PNG')
                print(f"Created concept image: {temp_path}")
                return temp_path
            else:
                print("Failed to create concept image")
                return None
                
        except Exception as e:
            print(f"Error creating concept image: {e}")
            return None
    
    def _draw_concept_image(self, concept: Dict[str, Any], width: int, height: int) -> Optional[Image.Image]:
        """Vẽ hình ảnh dựa trên concept"""
        try:
            # Tạo background
            color_scheme = concept.get('color_scheme', {})
            primary_color = self._hex_to_rgb(color_scheme.get('primary', 'blue'))
            secondary_color = self._hex_to_rgb(color_scheme.get('secondary', 'green'))
            
            # Tạo gradient background
            image = Image.new('RGB', (width, height), primary_color)
            draw = ImageDraw.Draw(image)
            
            # Vẽ gradient
            for y in range(height):
                ratio = y / height
                r = int(primary_color[0] * (1 - ratio) + secondary_color[0] * ratio)
                g = int(primary_color[1] * (1 - ratio) + secondary_color[1] * ratio)
                b = int(primary_color[2] * (1 - ratio) + secondary_color[2] * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Vẽ các elements
            visual_elements = concept.get('visual_elements', [])
            for i, element in enumerate(visual_elements[:3]):  # Giới hạn 3 elements
                self._draw_visual_element(draw, element, width, height, i)
            
            # Thêm text overlay
            main_concept = concept.get('main_concept', 'Concept')
            self._add_text_overlay(draw, main_concept, width, height)
            
            return image
            
        except Exception as e:
            print(f"Error drawing concept image: {e}")
            return None
    
    def _draw_visual_element(self, draw: ImageDraw.Draw, element: Dict[str, Any], 
                           width: int, height: int, index: int):
        """Vẽ một visual element"""
        try:
            element_type = element.get('element', '').lower()
            position = element.get('position', 'center')
            
            # Tính toán vị trí
            if position == 'center':
                x, y = width // 2, height // 2
            elif position == 'left':
                x, y = width // 4, height // 2
            elif position == 'right':
                x, y = 3 * width // 4, height // 2
            else:
                x, y = width // 2, height // 2
            
            # Vẽ các hình dạng khác nhau dựa trên element type
            if 'chart' in element_type or 'graph' in element_type:
                self._draw_chart_element(draw, x, y, index)
            elif 'diagram' in element_type or 'flow' in element_type:
                self._draw_diagram_element(draw, x, y, index)
            elif 'icon' in element_type or 'symbol' in element_type:
                self._draw_icon_element(draw, x, y, index)
            else:
                self._draw_generic_element(draw, x, y, index)
                
        except Exception as e:
            print(f"Error drawing visual element: {e}")
    
    def _draw_chart_element(self, draw: ImageDraw.Draw, x: int, y: int, index: int):
        """Vẽ chart element"""
        colors = [(255, 99, 132), (54, 162, 235), (255, 205, 86), (75, 192, 192)]
        color = colors[index % len(colors)]
        
        # Vẽ bar chart
        bar_width = 40
        bar_height = 60 + index * 20
        draw.rectangle([x - bar_width//2, y - bar_height, x + bar_width//2, y], fill=color)
        
        # Vẽ axis
        draw.line([x - 60, y, x + 60, y], fill=(100, 100, 100), width=2)
        draw.line([x - 60, y - 80, x - 60, y], fill=(100, 100, 100), width=2)
    
    def _draw_diagram_element(self, draw: ImageDraw.Draw, x: int, y: int, index: int):
        """Vẽ diagram element"""
        colors = [(138, 43, 226), (30, 144, 255), (50, 205, 50)]
        color = colors[index % len(colors)]
        
        # Vẽ flowchart boxes
        box_width = 80
        box_height = 40
        draw.rectangle([x - box_width//2, y - box_height//2, x + box_width//2, y + box_height//2], 
                      fill=color, outline=(255, 255, 255), width=2)
        
        # Vẽ arrows
        if index > 0:
            draw.polygon([(x - 60, y), (x - 40, y - 10), (x - 40, y + 10)], fill=(100, 100, 100))
    
    def _draw_icon_element(self, draw: ImageDraw.Draw, x: int, y: int, index: int):
        """Vẽ icon element"""
        colors = [(255, 165, 0), (220, 20, 60), (0, 191, 255)]
        color = colors[index % len(colors)]
        
        # Vẽ circle icon
        radius = 30
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], 
                    fill=color, outline=(255, 255, 255), width=3)
        
        # Vẽ inner symbol
        inner_radius = 15
        draw.ellipse([x - inner_radius, y - inner_radius, x + inner_radius, y + inner_radius], 
                    fill=(255, 255, 255))
    
    def _draw_generic_element(self, draw: ImageDraw.Draw, x: int, y: int, index: int):
        """Vẽ generic element"""
        colors = [(128, 0, 128), (0, 128, 128), (128, 128, 0)]
        color = colors[index % len(colors)]
        
        # Vẽ hexagon
        points = []
        for i in range(6):
            angle = i * 60
            px = x + 25 * math.cos(math.radians(angle))
            py = y + 25 * math.sin(math.radians(angle))
            points.append((px, py))
        
        draw.polygon(points, fill=color, outline=(255, 255, 255), width=2)
    
    def _add_text_overlay(self, draw: ImageDraw.Draw, text: str, width: int, height: int):
        """Thêm text overlay"""
        try:
            # Load font
            try:
                font = ImageFont.truetype("arial.ttf", 36)
            except:
                font = ImageFont.load_default()
            
            # Wrap text
            wrapped_text = textwrap.fill(text, width=20)
            lines = wrapped_text.split('\n')
            
            # Calculate position
            text_height = len(lines) * 40
            y_start = height - text_height - 50
            
            # Draw background
            draw.rectangle([20, y_start - 10, width - 20, height - 20], 
                          fill=(0, 0, 0, 150), outline=(255, 255, 255), width=2)
            
            # Draw text
            for i, line in enumerate(lines):
                y = y_start + i * 40
                draw.text((40, y), line, fill=(255, 255, 255), font=font)
                
        except Exception as e:
            print(f"Error adding text overlay: {e}")
    
    def _hex_to_rgb(self, color: str) -> tuple:
        """Chuyển đổi hex color sang RGB"""
        color_map = {
            'blue': (59, 130, 246),
            'green': (34, 197, 94),
            'purple': (168, 85, 247),
            'red': (239, 68, 68),
            'orange': (249, 115, 22),
            'yellow': (234, 179, 8),
            'pink': (236, 72, 153),
            'indigo': (99, 102, 241)
        }
        return color_map.get(color.lower(), (59, 130, 246))

# Global instance
content_based_image_service = ContentBasedImageService()

def create_content_based_image(content: str, context: str = "educational", 
                             width: int = 1280, height: int = 720) -> Optional[str]:
    """Function tiện ích để tạo hình ảnh dựa trên nội dung"""
    return content_based_image_service.create_content_image(content, context, width, height)

def is_content_based_image_available() -> bool:
    """Kiểm tra xem service có khả dụng không"""
    return (content_based_image_service.gemini_api_key is not None and 
            len(content_based_image_service.gemini_api_key) > 0)
