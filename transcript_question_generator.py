#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcript Question Generator - Tạo câu hỏi từ transcript video
AI Gemini phân tích nội dung và tạo câu hỏi dựa trên ý nghĩa, không copy text
"""

import os
import json
import random
from typing import Dict, List, Optional
from ai_gemini import generate_questions_from_transcript

class TranscriptQuestionGenerator:
    """Generator tạo câu hỏi từ transcript video"""
    
    def __init__(self):
        self.question_types = ["mcq", "essay", "oral"]
        self.analysis_strategies = [
            "Phân tích khái niệm cốt lõi và nguyên lý được trình bày",
            "Tập trung vào ứng dụng thực tế và tình huống sử dụng",
            "Kiểm tra mối quan hệ giữa các khái niệm",
            "Đánh giá khả năng phân tích và áp dụng kiến thức",
            "Tập trung vào điểm quan trọng và lưu ý chính",
            "Kiểm tra khả năng so sánh và đối chiếu",
            "Đánh giá hiểu biết về quy trình và các bước thực hiện",
            "Tập trung vào ví dụ cụ thể và case study"
        ]
    
    def generate_questions_from_video_transcript(self, transcript: str, video_title: str = "Video Transcript",
                                                question_types: List[str] = None, 
                                                n_questions_per_type: int = 2) -> Dict:
        """
        Tạo câu hỏi từ transcript video
        
        Args:
            transcript: Nội dung transcript của video
            video_title: Tiêu đề video
            question_types: Loại câu hỏi cần tạo
            n_questions_per_type: Số câu hỏi mỗi loại
        
        Returns:
            Dict chứa câu hỏi đã tạo
        """
        if question_types is None:
            question_types = self.question_types
        
        print(f"🤖 AI Gemini đang phân tích transcript: {video_title}")
        print(f"📝 Độ dài transcript: {len(transcript)} ký tự")
        print(f"🎯 Loại câu hỏi: {', '.join(question_types)}")
        print(f"📊 Số câu hỏi mỗi loại: {n_questions_per_type}")
        
        all_questions = {
            "mcq_questions": [],
            "essay_questions": [],
            "oral_questions": []
        }
        
        total_questions = 0
        
        for q_type in question_types:
            print(f"\n🎯 Tạo câu hỏi {q_type.upper()}...")
            
            try:
                # Sử dụng AI Gemini để tạo câu hỏi
                questions_data = generate_questions_from_transcript(
                    transcript=transcript,
                    question_type=q_type,
                    n_questions=n_questions_per_type
                )
                
                if questions_data and questions_data.get("questions"):
                    if q_type == "mcq":
                        all_questions["mcq_questions"].extend(questions_data["questions"])
                    elif q_type == "essay":
                        all_questions["essay_questions"].extend(questions_data["questions"])
                    elif q_type == "oral":
                        all_questions["oral_questions"].extend(questions_data["questions"])
                    
                    total_questions += len(questions_data["questions"])
                    print(f"✅ Tạo thành công {len(questions_data['questions'])} câu hỏi {q_type.upper()}")
                else:
                    print(f"⚠️ Không thể tạo câu hỏi {q_type.upper()}")
                    
            except Exception as e:
                print(f"❌ Lỗi tạo câu hỏi {q_type.upper()}: {e}")
        
        print(f"\n✅ Hoàn thành tạo câu hỏi!")
        print(f"📊 Tổng cộng: {total_questions} câu hỏi")
        
        return {
            "video_title": video_title,
            "transcript_length": len(transcript),
            "total_questions": total_questions,
            "question_types": question_types,
            "analysis_strategy": random.choice(self.analysis_strategies),
            **all_questions
        }
    
    def analyze_transcript_content(self, transcript: str) -> Dict:
        """
        Phân tích nội dung transcript để hiểu cấu trúc
        
        Args:
            transcript: Nội dung transcript
        
        Returns:
            Dict chứa phân tích nội dung
        """
        print("🔍 AI Gemini đang phân tích cấu trúc nội dung...")
        
        # Phân tích cơ bản
        content_analysis = {
            "total_length": len(transcript),
            "estimated_duration": len(transcript) / 200,  # Ước tính 200 ký tự/phút
            "main_topics": [],
            "key_concepts": [],
            "difficulty_level": "intermediate",
            "content_type": "educational"
        }
        
        # Tìm các từ khóa chính
        keywords = self._extract_keywords(transcript)
        content_analysis["key_concepts"] = keywords[:10]
        
        # Xác định chủ đề chính
        topics = self._identify_main_topics(transcript)
        content_analysis["main_topics"] = topics[:5]
        
        return content_analysis
    
    def _extract_keywords(self, transcript: str) -> List[str]:
        """Trích xuất từ khóa chính từ transcript"""
        # Đơn giản hóa: tìm các từ xuất hiện nhiều lần
        words = transcript.lower().split()
        word_count = {}
        
        for word in words:
            if len(word) > 4:  # Chỉ lấy từ có độ dài > 4
                word_count[word] = word_count.get(word, 0) + 1
        
        # Sắp xếp theo tần suất
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:20]]
    
    def _identify_main_topics(self, transcript: str) -> List[str]:
        """Xác định chủ đề chính từ transcript"""
        # Đơn giản hóa: tìm các cụm từ có thể là chủ đề
        topics = []
        
        # Tìm các cụm từ bắt đầu bằng số hoặc từ khóa
        lines = transcript.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 10 and (line[0].isdigit() or line.startswith(('Chương', 'Phần', 'Bài', 'Mục'))):
                topics.append(line)
        
        return topics[:10]

def create_quiz_from_transcript(transcript: str, video_title: str = "Video Quiz",
                               question_types: List[str] = None,
                               n_questions_per_type: int = 2) -> Dict:
    """
    Function tiện ích để tạo quiz từ transcript
    
    Args:
        transcript: Nội dung transcript
        video_title: Tiêu đề video
        question_types: Loại câu hỏi
        n_questions_per_type: Số câu hỏi mỗi loại
    
    Returns:
        Dict chứa quiz đã tạo
    """
    generator = TranscriptQuestionGenerator()
    return generator.generate_questions_from_video_transcript(
        transcript=transcript,
        video_title=video_title,
        question_types=question_types,
        n_questions_per_type=n_questions_per_type
    )

def demo_transcript_question_generator():
    """Demo tạo câu hỏi từ transcript"""
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🎯 TRANSCRIPT QUESTION GENERATOR                    ║
║                                                                ║
║  AI Gemini phân tích transcript và tạo câu hỏi thông minh    ║
║  Dựa trên ý nghĩa, không copy y nguyên text                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Sample transcript
    sample_transcript = """
    Chào mừng các bạn đến với bài giảng về Machine Learning và Trí Tuệ Nhân Tạo.

    Machine Learning là một nhánh của Trí Tuệ Nhân Tạo cho phép máy tính học và cải thiện từ kinh nghiệm mà không cần được lập trình rõ ràng. Có ba loại chính: Supervised Learning, Unsupervised Learning và Reinforcement Learning.

    Supervised Learning sử dụng dữ liệu có nhãn để huấn luyện mô hình. Ví dụ: phân loại email spam, nhận dạng hình ảnh. Các thuật toán phổ biến bao gồm Linear Regression, Logistic Regression, Support Vector Machines và Neural Networks.

    Unsupervised Learning làm việc với dữ liệu không có nhãn, tìm kiếm các pattern hoặc cấu trúc ẩn trong dữ liệu. Ví dụ: phân nhóm khách hàng theo hành vi mua sắm, giảm chiều dữ liệu. Các thuật toán như K-Means Clustering, Hierarchical Clustering và Principal Component Analysis thường được sử dụng.

    Reinforcement Learning liên quan đến việc một agent học cách đưa ra quyết định thông qua tương tác với môi trường để tối đa hóa phần thưởng. Ví dụ: AI chơi game, robot học cách đi lại.

    Một vấn đề thường gặp trong Machine Learning là Overfitting, khi mô hình học quá kỹ dữ liệu huấn luyện và không thể tổng quát hóa tốt cho dữ liệu mới. Để tránh overfitting, chúng ta có thể sử dụng các kỹ thuật như cross-validation, regularization hoặc early stopping.

    Machine Learning có ứng dụng rộng rãi trong nhiều lĩnh vực như y tế (chẩn đoán bệnh), tài chính (phát hiện gian lận), thương mại điện tử (hệ thống gợi ý sản phẩm) và xe tự lái.
    """
    
    try:
        # Tạo quiz từ transcript
        quiz_result = create_quiz_from_transcript(
            transcript=sample_transcript,
            video_title="Machine Learning và AI",
            question_types=["mcq", "essay", "oral"],
            n_questions_per_type=2
        )
        
        print("\n" + "=" * 60)
        print("🎉 KẾT QUẢ TẠO CÂU HỎI:")
        print("=" * 60)
        
        print(f"📹 Video: {quiz_result['video_title']}")
        print(f"📝 Transcript: {quiz_result['transcript_length']} ký tự")
        print(f"📊 Tổng câu hỏi: {quiz_result['total_questions']}")
        print(f"🎯 Chiến lược: {quiz_result['analysis_strategy']}")
        
        # Hiển thị câu hỏi MCQ
        if quiz_result.get("mcq_questions"):
            print(f"\n🔹 CÂU HỎI TRẮC NGHIỆM ({len(quiz_result['mcq_questions'])} câu):")
            print("-" * 50)
            for i, q in enumerate(quiz_result["mcq_questions"], 1):
                print(f"{i}. {q['question']}")
                for j, option in enumerate(q['options']):
                    prefix = "✓ " if j == q['correct_index'] else "   "
                    print(f"   {prefix}{option}")
                print(f"   💡 Giải thích: {q['explanation']}")
                print("")
        
        # Hiển thị câu hỏi Essay
        if quiz_result.get("essay_questions"):
            print(f"\n🔹 CÂU HỎI TỰ LUẬN ({len(quiz_result['essay_questions'])} câu):")
            print("-" * 50)
            for i, q in enumerate(quiz_result["essay_questions"], 1):
                print(f"{i}. {q['question']}")
                if 'keywords' in q:
                    print(f"   🔑 Từ khóa: {', '.join(q['keywords'])}")
                print(f"   💡 Gợi ý: {q['explanation']}")
                print("")
        
        # Hiển thị câu hỏi Oral
        if quiz_result.get("oral_questions"):
            print(f"\n🔹 CÂU HỎI VẤN ĐÁP ({len(quiz_result['oral_questions'])} câu):")
            print("-" * 50)
            for i, q in enumerate(quiz_result["oral_questions"], 1):
                print(f"{i}. {q['question']}")
                if 'keywords' in q:
                    print(f"   🔑 Từ khóa: {', '.join(q['keywords'])}")
                print(f"   💡 Gợi ý: {q['explanation']}")
                print("")
        
        print("\n✨ ĐẶC ĐIỂM CỦA HỆ THỐNG:")
        print("=" * 60)
        print("✅ AI Gemini phân tích ý nghĩa transcript")
        print("✅ Tạo câu hỏi dựa trên khái niệm, không copy text")
        print("✅ Câu hỏi đa dạng: MCQ, Essay, Oral")
        print("✅ Kiểm tra hiểu biết sâu về nội dung")
        print("✅ Phù hợp cho giáo dục và đánh giá")
        
        return quiz_result
        
    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình tạo câu hỏi: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🎯 Transcript Question Generator Demo")
    print("=" * 50)
    
    # Load environment
    try:
        from dotenv import load_dotenv
        if os.path.exists('.env'):
            load_dotenv()
    except ImportError:
        pass
    
    # Check Gemini API key
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY not found")
        print("💡 Please set GEMINI_API_KEY in your .env file")
    else:
        print("✅ GEMINI_API_KEY found")
        demo_transcript_question_generator()
    
    print("\n" + "=" * 50)
    print("🏁 Demo completed!")
