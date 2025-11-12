# services/smart_image_analyzer.py
"""
Smart Image Analyzer - AI content analysis for image generation
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
import requests

class SmartImageAnalyzer:
    """AI content analysis for accurate image keywords"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    def analyze_content_for_images(self, content: str, context: str = "educational") -> Dict[str, Any]:
        """
        Analyze content to generate appropriate image keywords
        
        Args:
            content: Text content to analyze
            context: Context (educational, technical, business, etc.)
        
        Returns:
            Dict containing keywords and image suggestions
        """
        try:
            # Try using Gemini AI first
            if self.gemini_api_key:
                return self._analyze_with_gemini(content, context)
            
            # Fallback: Manual analysis
            return self._analyze_manually(content, context)
            
        except Exception as e:
            print(f"Error in content analysis: {e}")
            return self._analyze_manually(content, context)
    
    def _analyze_with_gemini(self, content: str, context: str) -> Dict[str, Any]:
        """Analyze content using Gemini AI"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
Bạn là chuyên gia phân tích nội dung để tạo hình ảnh phù hợp cho video giáo dục.

NỘI DUNG CẦN PHÂN TÍCH:
{content[:2000]}  # Giới hạn độ dài

NGỮ CẢNH: {context}

NHIỆM VỤ:
1. PHÂN TÍCH nội dung chính và các khái niệm quan trọng
2. TẠO từ khóa hình ảnh cụ thể và phù hợp
3. LOẠI BỎ từ khóa không phù hợp (con người, khuôn mặt, etc.)
4. ƯU TIÊN hình ảnh minh họa, biểu đồ, sơ đồ, icon, illustration
5. TRÁNH hình ảnh con người, khuôn mặt, chân dung

YÊU CẦU:
- Từ khóa phải CỤ THỂ và LIÊN QUAN trực tiếp đến nội dung
- Ưu tiên: illustration, diagram, chart, icon, concept art
- Tránh: people, faces, portraits, human figures
- Từ khóa bằng tiếng Anh để tìm kiếm tốt hơn
- Mỗi từ khóa phải có ý nghĩa rõ ràng

TRẢ VỀ JSON:
{{
  "main_concepts": ["khái niệm chính 1", "khái niệm chính 2"],
  "image_keywords": [
    {{
      "keyword": "từ khóa tiếng Anh",
      "priority": "high|medium|low",
      "description": "mô tả hình ảnh mong muốn",
      "avoid": ["từ khóa cần tránh"]
    }}
  ],
  "visual_style": "illustration|diagram|chart|icon|concept",
  "content_type": "technical|educational|business|scientific",
  "suggested_colors": ["màu chủ đạo"],
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
                    
                    # Validate và cải thiện kết quả
                    return self._validate_and_improve_result(result, content)
                    
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                
        except Exception as e:
            print(f"Gemini analysis failed: {e}")
        
        # Fallback to manual analysis
        return self._analyze_manually(content, context)
    
    def _analyze_manually(self, content: str, context: str) -> Dict[str, Any]:
        """Phân tích thủ công khi AI không khả dụng"""
        
        # Tách từ khóa từ nội dung
        words = re.findall(r'\b[A-Za-zÀ-ỹ]{3,}\b', content.lower())
        
        # Loại bỏ từ không quan trọng
        stop_words = {
            'của', 'và', 'trong', 'cho', 'với', 'từ', 'đến', 'là', 'có', 'được',
            'the', 'and', 'for', 'with', 'from', 'to', 'is', 'are', 'was', 'were',
            'this', 'that', 'these', 'those', 'can', 'will', 'should', 'would',
            'may', 'might', 'must', 'have', 'has', 'had', 'do', 'does', 'did'
        }
        
        important_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Tạo từ khóa hình ảnh - TUYỆT ĐỐI KHÔNG CÓ CON NGƯỜI
        image_keywords = []
        for word in important_words[:10]:  # Lấy 10 từ quan trọng nhất
            # Chuyển đổi từ khóa thành hình ảnh phù hợp
            keyword_mapping = self._create_image_keyword(word, context)
            if keyword_mapping and self._is_safe_keyword(keyword_mapping.get('keyword', '')):
                image_keywords.append(keyword_mapping)
        
        return {
            "main_concepts": important_words[:5],
            "image_keywords": image_keywords,
            "visual_style": "illustration",
            "content_type": context,
            "suggested_colors": ["blue", "green", "purple"],
            "mood": "professional"
        }
    
    def _is_safe_keyword(self, keyword: str) -> bool:
        """Kiểm tra từ khóa có an toàn không (không chứa từ liên quan đến con người)"""
        if not keyword:
            return False
        
        keyword_lower = keyword.lower()
        
        # Danh sách từ cần tránh
        unsafe_words = [
            'people', 'person', 'human', 'man', 'woman', 'boy', 'girl',
            'face', 'faces', 'portrait', 'portraits', 'head', 'heads',
            'body', 'bodies', 'hand', 'hands', 'foot', 'feet', 'leg', 'legs',
            'team', 'group', 'crowd', 'audience', 'student', 'students',
            'teacher', 'teachers', 'professor', 'professors', 'worker', 'workers',
            'employee', 'employees', 'businessman', 'businesswoman', 'executive',
            'meeting', 'meetings', 'conference', 'presentation', 'presentations'
        ]
        
        # Kiểm tra từ khóa có chứa từ không an toàn không
        for unsafe_word in unsafe_words:
            if unsafe_word in keyword_lower:
                print(f"Unsafe keyword detected: {keyword} (contains: {unsafe_word})")
                return False
        
        return True
    
    def _create_image_keyword(self, word: str, context: str) -> Optional[Dict[str, Any]]:
        """Tạo từ khóa hình ảnh từ từ gốc"""
        
        # Mapping từ khóa thành hình ảnh phù hợp
        keyword_mappings = {
            # Technical terms
            'programming': {'keyword': 'programming code illustration', 'priority': 'high'},
            'algorithm': {'keyword': 'algorithm flowchart diagram', 'priority': 'high'},
            'database': {'keyword': 'database schema diagram', 'priority': 'high'},
            'network': {'keyword': 'network topology diagram', 'priority': 'high'},
            'security': {'keyword': 'cybersecurity shield icon', 'priority': 'high'},
            'cloud': {'keyword': 'cloud computing illustration', 'priority': 'high'},
            'ai': {'keyword': 'artificial intelligence brain diagram', 'priority': 'high'},
            'machine': {'keyword': 'machine learning neural network', 'priority': 'high'},
            
            # Educational terms
            'learning': {'keyword': 'education book illustration', 'priority': 'high'},
            'teaching': {'keyword': 'teaching method diagram', 'priority': 'high'},
            'student': {'keyword': 'education concept illustration', 'priority': 'medium'},
            'course': {'keyword': 'online course platform', 'priority': 'medium'},
            'lesson': {'keyword': 'lesson plan diagram', 'priority': 'medium'},
            
            # Business terms
            'business': {'keyword': 'business strategy diagram', 'priority': 'high'},
            'marketing': {'keyword': 'marketing funnel illustration', 'priority': 'high'},
            'finance': {'keyword': 'financial chart diagram', 'priority': 'high'},
            'management': {'keyword': 'management hierarchy chart', 'priority': 'high'},
            
            # Scientific terms
            'science': {'keyword': 'scientific method diagram', 'priority': 'high'},
            'research': {'keyword': 'research process flowchart', 'priority': 'high'},
            'analysis': {'keyword': 'data analysis chart', 'priority': 'high'},
            'experiment': {'keyword': 'laboratory equipment illustration', 'priority': 'high'},
        }
        
        # Tìm mapping phù hợp
        word_lower = word.lower()
        for key, mapping in keyword_mappings.items():
            if key in word_lower or word_lower in key:
                return {
                    'keyword': mapping['keyword'],
                    'priority': mapping['priority'],
                    'description': f"Illustration for {word} concept",
                    'avoid': ['people', 'faces', 'portraits']
                }
        
        # Tạo từ khóa chung
        return {
            'keyword': f"{word} concept illustration",
            'priority': 'medium',
            'description': f"Conceptual illustration for {word}",
            'avoid': ['people', 'faces', 'portraits']
        }
    
    def _validate_and_improve_result(self, result: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Validate và cải thiện kết quả từ AI"""
        
        # Đảm bảo có image_keywords
        if 'image_keywords' not in result:
            result['image_keywords'] = []
        
        # Cải thiện từ khóa
        improved_keywords = []
        for kw in result['image_keywords']:
            if isinstance(kw, dict):
                # Đảm bảo có từ khóa cần tránh
                if 'avoid' not in kw:
                    kw['avoid'] = ['people', 'faces', 'portraits', 'human figures']
                
                # Đảm bảo từ khóa không chứa từ cần tránh
                keyword = kw.get('keyword', '')
                if not any(avoid_word in keyword.lower() for avoid_word in kw['avoid']):
                    improved_keywords.append(kw)
        
        result['image_keywords'] = improved_keywords
        
        # Đảm bảo có các field cần thiết
        if 'visual_style' not in result:
            result['visual_style'] = 'illustration'
        if 'content_type' not in result:
            result['content_type'] = 'educational'
        if 'mood' not in result:
            result['mood'] = 'professional'
        
        return result
    
    def get_best_image_keywords(self, analysis_result: Dict[str, Any], count: int = 3) -> List[str]:
        """Lấy từ khóa tốt nhất để tìm hình ảnh"""
        
        keywords = analysis_result.get('image_keywords', [])
        
        # Sắp xếp theo priority
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        sorted_keywords = sorted(
            keywords, 
            key=lambda x: priority_order.get(x.get('priority', 'medium'), 2),
            reverse=True
        )
        
        # Lấy từ khóa tốt nhất
        best_keywords = []
        for kw in sorted_keywords[:count]:
            if isinstance(kw, dict) and 'keyword' in kw:
                best_keywords.append(kw['keyword'])
        
        return best_keywords
    
    def create_image_search_query(self, content: str, context: str = "educational") -> str:
        """Tạo query tìm kiếm hình ảnh từ nội dung - TUYỆT ĐỐI KHÔNG CÓ CON NGƯỜI"""
        
        analysis = self.analyze_content_for_images(content, context)
        best_keywords = self.get_best_image_keywords(analysis, count=1)
        
        if best_keywords:
            keyword = best_keywords[0]
            # Đảm bảo từ khóa an toàn
            if self._is_safe_keyword(keyword):
                return f"{keyword} illustration concept diagram chart abstract professional educational absolutely no people no humans no faces no portraits"
            else:
                print(f"Unsafe keyword filtered: {keyword}")
        
        # Fallback: Tạo query đơn giản và an toàn
        words = re.findall(r'\b[A-Za-zÀ-ỹ]{4,}\b', content.lower())
        important_words = [w for w in words if len(w) > 4 and self._is_safe_keyword(w)][:3]
        
        if important_words:
            return f"{' '.join(important_words)} concept illustration diagram chart abstract professional educational absolutely no people no humans no faces no portraits"
        
        return "educational concept illustration diagram chart abstract professional absolutely no people no humans no faces no portraits"

# Global instance
smart_image_analyzer = SmartImageAnalyzer()

def analyze_content_for_smart_images(content: str, context: str = "educational") -> Dict[str, Any]:
    """Function tiện ích để phân tích nội dung"""
    return smart_image_analyzer.analyze_content_for_images(content, context)

def get_smart_image_keywords(content: str, context: str = "educational", count: int = 3) -> List[str]:
    """Function tiện ích để lấy từ khóa hình ảnh thông minh"""
    analysis = smart_image_analyzer.analyze_content_for_images(content, context)
    return smart_image_analyzer.get_best_image_keywords(analysis, count)

def create_smart_image_query(content: str, context: str = "educational") -> str:
    """Function tiện ích để tạo query tìm kiếm thông minh"""
    return smart_image_analyzer.create_image_search_query(content, context)
