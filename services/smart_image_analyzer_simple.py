# services/smart_image_analyzer_simple.py
"""
Simple Smart Image Analyzer without Unicode issues
"""

import os
import re
import json
from typing import List, Dict, Any, Optional

class SimpleSmartImageAnalyzer:
    """Simple AI content analysis for image keywords"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    def analyze_content_for_images(self, content: str, context: str = "educational") -> Dict[str, Any]:
        """Analyze content to generate image keywords"""
        try:
            if self.gemini_api_key:
                return self._analyze_with_gemini(content, context)
            else:
                return self._analyze_manually(content, context)
        except Exception as e:
            print(f"Error in content analysis: {e}")
            return self._analyze_manually(content, context)
    
    def _analyze_with_gemini(self, content: str, context: str) -> Dict[str, Any]:
        """Analyze content using Gemini AI"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            prompt = f"""
You are an expert content analyst for creating appropriate images for educational videos.

CONTENT TO ANALYZE:
{content[:2000]}

CONTEXT: {context}

TASK:
1. ANALYZE main content and important concepts
2. CREATE specific and appropriate image keywords
3. REMOVE inappropriate keywords (people, faces, etc.)
4. PRIORITIZE illustration images, charts, diagrams, icons
5. AVOID human images, faces, portraits

REQUIREMENTS:
- Keywords must be SPECIFIC and DIRECTLY related to content
- Priority: illustration, diagram, chart, icon, concept art
- Avoid: people, faces, portraits, human figures
- Keywords in English for better search
- Each keyword must have clear meaning

RESPOND IN JSON FORMAT:
{{
  "main_concepts": ["main concept 1", "main concept 2"],
  "image_keywords": [
    {{
      "keyword": "English keyword",
      "relevance": "high|medium|low",
      "description": "What this keyword represents",
      "visual_type": "illustration|diagram|chart|icon|concept"
    }}
  ],
  "avoid_keywords": ["people", "faces", "portraits"],
  "recommended_style": "illustration|diagram|infographic|concept_art"
}}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse JSON response
            try:
                # Extract JSON from response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                    return self._validate_and_improve_result(result, content)
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                
        except Exception as e:
            print(f"Gemini analysis failed: {e}")
        
        # Fallback to manual analysis
        return self._analyze_manually(content, context)
    
    def _analyze_manually(self, content: str, context: str) -> Dict[str, Any]:
        """Manual analysis when AI is not available"""
        
        # Extract keywords from content with priority for specific terms
        words = re.findall(r'\b[A-Za-z]{3,}\b', content.lower())
        
        # Priority mapping for specific content
        priority_terms = {
            'docker': 10, 'container': 9, 'kubernetes': 9, 'python': 8, 'javascript': 8,
            'java': 8, 'react': 8, 'angular': 8, 'vue': 8, 'mysql': 8, 'postgresql': 8,
            'mongodb': 8, 'aws': 8, 'azure': 8, 'gcp': 8, 'tensorflow': 8, 'pytorch': 8,
            'html': 7, 'css': 7, 'bootstrap': 7, 'linux': 7, 'ubuntu': 7, 'git': 7,
            'github': 7, 'api': 7, 'rest': 7, 'json': 7, 'blockchain': 7, 'bitcoin': 7,
            'ethereum': 7, 'firewall': 7, 'ssl': 7, 'oauth': 7, 'jwt': 7
        }
        
        # Score words by priority and frequency
        word_scores = {}
        for word in words:
            if len(word) >= 3:
                score = priority_terms.get(word, 1)
                word_scores[word] = word_scores.get(word, 0) + score
        
        # Sort by score and get top words
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        important_words = [word for word, score in sorted_words[:8]]
        
        # Create image keywords with priority for specific content
        image_keywords = []
        for word in important_words:
            if self._is_safe_keyword(word):
                keyword_data = self._create_image_keyword(word, context)
                if keyword_data:
                    image_keywords.append(keyword_data)
        
        return {
            "main_concepts": important_words[:3],
            "image_keywords": image_keywords,
            "avoid_keywords": ["people", "faces", "portraits"],
            "recommended_style": "specific_logo"
        }
    
    def _is_safe_keyword(self, keyword: str) -> bool:
        """Check if keyword is safe (no human-related terms)"""
        if not keyword:
            return False
        
        keyword_lower = keyword.lower()
        
        # List of unsafe words
        unsafe_words = [
            'people', 'person', 'human', 'man', 'woman', 'boy', 'girl',
            'face', 'faces', 'portrait', 'portraits', 'head', 'heads',
            'body', 'bodies', 'hand', 'hands', 'foot', 'feet', 'leg', 'legs',
            'team', 'group', 'crowd', 'audience', 'student', 'students',
            'teacher', 'teachers', 'professor', 'professors', 'worker', 'workers',
            'employee', 'employees', 'businessman', 'businesswoman', 'executive',
            'meeting', 'meetings', 'conference', 'presentation', 'presentations'
        ]
        
        # Check if keyword contains unsafe words
        for unsafe_word in unsafe_words:
            if unsafe_word in keyword_lower:
                print(f"Unsafe keyword detected: {keyword} (contains: {unsafe_word})")
                return False
        
        return True
    
    def _create_image_keyword(self, word: str, context: str) -> Optional[Dict[str, Any]]:
        """Create image keyword from word"""
        if not self._is_safe_keyword(word):
            return None
        
        # Map specific content to exact visual representations
        specific_content_mapping = {
            # Docker and Containerization - FIXED: More specific and accurate
            'docker': 'docker whale logo mascot',
            'dockerfile': 'docker whale logo configuration',
            'container': 'docker container box shipping',
            'containers': 'docker containers box shipping',
            'containerization': 'docker whale container logo',
            'kubernetes': 'kubernetes logo ship wheel',
            'k8s': 'kubernetes logo',
            'microservices': 'microservices architecture diagram',
            'devops': 'devops pipeline diagram cicd',
            'ci/cd': 'continuous integration pipeline logo',
            
            # Programming Languages
            'python': 'python snake logo programming',
            'javascript': 'javascript logo code brackets',
            'java': 'java coffee cup logo',
            'c++': 'c plus plus logo programming',
            'react': 'react atom logo framework',
            'angular': 'angular logo framework',
            'vue': 'vue logo framework',
            'nodejs': 'nodejs logo server',
            
            # Databases
            'mysql': 'mysql dolphin logo database',
            'postgresql': 'postgresql elephant logo',
            'mongodb': 'mongodb leaf logo database',
            'redis': 'redis logo database',
            'sqlite': 'sqlite logo database',
            
            # Cloud Platforms
            'aws': 'amazon web services cloud logo',
            'azure': 'microsoft azure cloud logo',
            'gcp': 'google cloud platform logo',
            'heroku': 'heroku logo cloud platform',
            
            # Frameworks and Tools
            'spring': 'spring framework logo',
            'django': 'django logo framework',
            'flask': 'flask logo framework',
            'express': 'express logo framework',
            'laravel': 'laravel logo framework',
            'rails': 'ruby on rails logo',
            
            # Data Science and AI
            'tensorflow': 'tensorflow logo machine learning',
            'pytorch': 'pytorch logo deep learning',
            'pandas': 'pandas logo data analysis',
            'numpy': 'numpy logo numerical computing',
            'scikit': 'scikit learn logo machine learning',
            
            # Web Technologies
            'html': 'html logo web markup',
            'css': 'css logo web styling',
            'bootstrap': 'bootstrap logo framework',
            'tailwind': 'tailwind css logo',
            'sass': 'sass logo css preprocessor',
            
            # Operating Systems
            'linux': 'linux penguin logo',
            'ubuntu': 'ubuntu logo operating system',
            'centos': 'centos logo linux',
            'windows': 'windows logo operating system',
            'macos': 'macos apple logo',
            
            # Version Control
            'git': 'git logo version control',
            'github': 'github logo git repository',
            'gitlab': 'gitlab logo git repository',
            'bitbucket': 'bitbucket logo git repository',
            
            # Monitoring and Tools
            'jenkins': 'jenkins logo ci cd',
            'ansible': 'ansible logo automation',
            'terraform': 'terraform logo infrastructure',
            'prometheus': 'prometheus logo monitoring',
            'grafana': 'grafana logo dashboard',
            
            # General Programming Concepts
            'api': 'api logo rest interface',
            'rest': 'rest api logo interface',
            'graphql': 'graphql logo query language',
            'json': 'json logo data format',
            'xml': 'xml logo markup language',
            'yaml': 'yaml logo configuration',
            
            # Business and Finance
            'blockchain': 'blockchain logo cryptocurrency',
            'bitcoin': 'bitcoin logo cryptocurrency',
            'ethereum': 'ethereum logo cryptocurrency',
            'fintech': 'fintech logo financial technology',
            'ecommerce': 'ecommerce logo online shopping',
            
            # Education and Learning
            'mooc': 'mooc logo online education',
            'coursera': 'coursera logo online learning',
            'udemy': 'udemy logo online courses',
            'khan': 'khan academy logo education',
            
            # Security
            'firewall': 'firewall logo network security',
            'ssl': 'ssl certificate logo security',
            'oauth': 'oauth logo authentication',
            'jwt': 'jwt token logo security'
        }
        
        # Fallback to general object mapping
        general_object_mapping = {
            'programming': 'programming code object symbol',
            'data': 'data visualization object chart',
            'algorithm': 'algorithm flowchart object diagram',
            'function': 'function diagram object symbol',
            'variable': 'programming variable object icon',
            'loop': 'programming loop object diagram',
            'condition': 'programming condition object flowchart',
            'class': 'object oriented programming object diagram',
            'method': 'programming method object symbol',
            'database': 'database schema object diagram',
            'network': 'network topology object diagram',
            'security': 'cybersecurity object symbol',
            'web': 'web development object icon',
            'mobile': 'mobile app object symbol',
            'cloud': 'cloud computing object architecture',
            'ai': 'artificial intelligence object symbol',
            'machine': 'machine learning object diagram',
            'neural': 'neural network object illustration',
            'deep': 'deep learning object concept',
            'business': 'business object symbol icon',
            'market': 'market analysis object chart',
            'financial': 'financial planning object diagram',
            'analysis': 'data analysis object chart',
            'strategy': 'business strategy object symbol',
            'planning': 'planning object flowchart',
            'education': 'education object symbol',
            'learning': 'learning object icon',
            'teaching': 'teaching object symbol',
            'student': 'student object icon',
            'course': 'course object symbol'
        }
        
        # Combine both mappings
        keyword_mapping = {**specific_content_mapping, **general_object_mapping}
        
        # Get specific keyword or use general one focused on objects/symbols
        specific_keyword = keyword_mapping.get(word.lower(), f"{word} object symbol icon")
        
        return {
            "keyword": specific_keyword,
            "relevance": "high",
            "description": f"Object/symbol representation of {word}",
            "visual_type": "object_symbol"
        }
    
    def _validate_and_improve_result(self, result: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Validate and improve AI result"""
        if not isinstance(result, dict):
            return self._analyze_manually(content, "educational")
        
        # Ensure required fields
        if "image_keywords" not in result:
            result["image_keywords"] = []
        
        if "main_concepts" not in result:
            result["main_concepts"] = []
        
        if "avoid_keywords" not in result:
            result["avoid_keywords"] = ["people", "faces", "portraits"]
        
        # Filter unsafe keywords
        safe_keywords = []
        for keyword_data in result.get("image_keywords", []):
            if isinstance(keyword_data, dict) and "keyword" in keyword_data:
                keyword = keyword_data["keyword"]
                if self._is_safe_keyword(keyword):
                    safe_keywords.append(keyword_data)
        
        result["image_keywords"] = safe_keywords
        
        return result
    
    def get_best_image_keywords(self, analysis: Dict[str, Any], count: int = 3) -> List[str]:
        """Get best image keywords from analysis"""
        keywords = []
        
        for keyword_data in analysis.get("image_keywords", []):
            if isinstance(keyword_data, dict) and "keyword" in keyword_data:
                keyword = keyword_data["keyword"]
                if self._is_safe_keyword(keyword):
                    keywords.append(keyword)
                    if len(keywords) >= count:
                        break
        
        return keywords
    
    def create_image_search_query(self, content: str, context: str = "educational") -> str:
        """Create image search query from content - ABSOLUTELY NO PEOPLE"""
        
        analysis = self.analyze_content_for_images(content, context)
        best_keywords = self.get_best_image_keywords(analysis, count=1)
        
        if best_keywords:
            keyword = best_keywords[0]
            # Ensure keyword is safe
            if self._is_safe_keyword(keyword):
                return f"{keyword} illustration concept diagram chart abstract professional educational absolutely no people no humans no faces no portraits"
            else:
                print(f"Unsafe keyword filtered: {keyword}")
        
        # Fallback: Create simple and safe query
        words = re.findall(r'\b[A-Za-z]{4,}\b', content.lower())
        important_words = [w for w in words if len(w) > 4 and self._is_safe_keyword(w)][:3]
        
        if important_words:
            return f"{' '.join(important_words)} concept illustration diagram chart abstract professional educational absolutely no people no humans no faces no portraits"
        
        return "educational concept illustration diagram chart abstract professional absolutely no people no humans no faces no portraits"

# Global instance
simple_smart_image_analyzer = SimpleSmartImageAnalyzer()

def get_smart_image_keywords(content: str, context: str = "educational", count: int = 3) -> List[str]:
    """Get smart image keywords"""
    analysis = simple_smart_image_analyzer.analyze_content_for_images(content, context)
    return simple_smart_image_analyzer.get_best_image_keywords(analysis, count)

def create_smart_image_query(content: str, context: str = "educational") -> str:
    """Create smart image search query"""
    return simple_smart_image_analyzer.create_image_search_query(content, context)
