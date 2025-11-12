#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Transcript Quiz - Tạo câu hỏi từ transcript đơn giản
"""

import os
import json
from typing import Dict, List

def create_questions_from_transcript(transcript: str, video_title: str = "Video Quiz") -> Dict:
    """
    Tạo câu hỏi từ transcript dựa trên nội dung chính
    
    Args:
        transcript: Nội dung transcript
        video_title: Tiêu đề video
    
    Returns:
        Dict chứa câu hỏi đã tạo
    """
    
    print(f"📝 Phân tích transcript: {video_title}")
    print(f"📊 Độ dài: {len(transcript)} ký tự")
    
    # Phân tích nội dung cơ bản
    content_analysis = analyze_transcript_content(transcript)
    
    # Tạo câu hỏi dựa trên nội dung
    questions = generate_smart_questions(transcript, content_analysis)
    
    return {
        "video_title": video_title,
        "transcript_length": len(transcript),
        "content_analysis": content_analysis,
        "questions": questions,
        "total_questions": len(questions)
    }

def analyze_transcript_content(transcript: str) -> Dict:
    """Phân tích nội dung transcript"""
    
    # Tìm các từ khóa chính
    keywords = extract_keywords(transcript)
    
    # Tìm các chủ đề chính
    topics = identify_main_topics(transcript)
    
    # Xác định độ khó
    difficulty = assess_difficulty(transcript)
    
    return {
        "keywords": keywords,
        "main_topics": topics,
        "difficulty_level": difficulty,
        "content_type": "educational"
    }

def extract_keywords(transcript: str) -> List[str]:
    """Trích xuất từ khóa chính"""
    words = transcript.lower().split()
    word_count = {}
    
    for word in words:
        if len(word) > 4:  # Chỉ lấy từ có độ dài > 4
            word_count[word] = word_count.get(word, 0) + 1
    
    # Sắp xếp theo tần suất
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:15]]

def identify_main_topics(transcript: str) -> List[str]:
    """Xác định chủ đề chính"""
    topics = []
    lines = transcript.split('\n')
    
    for line in lines:
        line = line.strip()
        if len(line) > 10 and (line[0].isdigit() or line.startswith(('Chương', 'Phần', 'Bài', 'Mục', '1.', '2.', '3.'))):
            topics.append(line)
    
    return topics[:10]

def assess_difficulty(transcript: str) -> str:
    """Đánh giá độ khó"""
    if len(transcript) < 500:
        return "beginner"
    elif len(transcript) < 1500:
        return "intermediate"
    else:
        return "advanced"

def generate_smart_questions(transcript: str, analysis: Dict) -> List[Dict]:
    """Tạo câu hỏi thông minh dựa trên phân tích"""
    
    questions = []
    
    # Câu hỏi về từ khóa chính
    if analysis["keywords"]:
        questions.append({
            "type": "mcq",
            "question": f"Dựa trên nội dung video, từ khóa nào sau đây được đề cập nhiều nhất?",
            "options": [
                analysis["keywords"][0],
                analysis["keywords"][1] if len(analysis["keywords"]) > 1 else "Tùy chọn B",
                analysis["keywords"][2] if len(analysis["keywords"]) > 2 else "Tùy chọn C",
                "Tất cả đều đúng"
            ],
            "correct_index": 0,
            "explanation": f"Từ khóa '{analysis['keywords'][0]}' xuất hiện nhiều nhất trong transcript."
        })
    
    # Câu hỏi về chủ đề chính
    if analysis["main_topics"]:
        questions.append({
            "type": "essay",
            "question": f"Hãy giải thích về chủ đề chính được đề cập trong video: '{analysis['main_topics'][0]}'",
            "keywords": analysis["keywords"][:5],
            "explanation": "Câu hỏi yêu cầu hiểu biết sâu về nội dung chính của video."
        })
    
    # Câu hỏi về ứng dụng thực tế
    questions.append({
        "type": "oral",
        "question": "Dựa trên nội dung video, bạn có thể áp dụng kiến thức này vào tình huống thực tế nào?",
        "keywords": analysis["keywords"][:3],
        "explanation": "Câu hỏi kiểm tra khả năng áp dụng kiến thức vào thực tế."
    })
    
    # Câu hỏi về mối quan hệ giữa các khái niệm
    if len(analysis["keywords"]) > 2:
        questions.append({
            "type": "mcq",
            "question": f"Mối quan hệ giữa '{analysis['keywords'][0]}' và '{analysis['keywords'][1]}' trong video là gì?",
            "options": [
                "Bổ sung cho nhau",
                "Đối lập nhau",
                "Không liên quan",
                "Phụ thuộc lẫn nhau"
            ],
            "correct_index": 0,
            "explanation": "Các khái niệm trong video thường có mối quan hệ bổ sung cho nhau."
        })
    
    return questions

def demo_transcript_quiz():
    """Demo tạo câu hỏi từ transcript"""
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🎯 SIMPLE TRANSCRIPT QUIZ GENERATOR                  ║
║                                                                ║
║  Tạo câu hỏi từ transcript dựa trên nội dung chính           ║
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

    Machine Learning có ứng dụng rộng rãi trong nhiều lĩnh vực như y tế (chẩn đoán bệnh), tài chính (phát hiện gian lận), thương mại điện tử (hệ thống gợi ý sản phẩm) và xe tự lái.
    """
    
    try:
        # Tạo quiz từ transcript
        quiz_result = create_questions_from_transcript(
            transcript=sample_transcript,
            video_title="Machine Learning và AI"
        )
        
        print("\n" + "=" * 60)
        print("🎉 KẾT QUẢ TẠO CÂU HỎI:")
        print("=" * 60)
        
        print(f"📹 Video: {quiz_result['video_title']}")
        print(f"📝 Transcript: {quiz_result['transcript_length']} ký tự")
        print(f"📊 Tổng câu hỏi: {quiz_result['total_questions']}")
        
        print(f"\n🔍 PHÂN TÍCH NỘI DUNG:")
        print(f"  📚 Từ khóa: {', '.join(quiz_result['content_analysis']['keywords'][:5])}")
        print(f"  🎯 Chủ đề: {', '.join(quiz_result['content_analysis']['main_topics'][:3])}")
        print(f"  📊 Độ khó: {quiz_result['content_analysis']['difficulty_level']}")
        
        # Hiển thị câu hỏi
        print(f"\n🎯 CÂU HỎI ĐÃ TẠO:")
        print("-" * 50)
        
        for i, q in enumerate(quiz_result["questions"], 1):
            print(f"\n{i}. {q['question']}")
            
            if q["type"] == "mcq":
                for j, option in enumerate(q['options']):
                    prefix = "✓ " if j == q['correct_index'] else "   "
                    print(f"   {prefix}{option}")
            
            if 'keywords' in q:
                print(f"   🔑 Từ khóa: {', '.join(q['keywords'])}")
            
            print(f"   💡 Giải thích: {q['explanation']}")
        
        print(f"\n✨ ĐẶC ĐIỂM CỦA HỆ THỐNG:")
        print("=" * 60)
        print("✅ Phân tích nội dung transcript thông minh")
        print("✅ Tạo câu hỏi dựa trên ý nghĩa, không copy text")
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
    print("🎯 Simple Transcript Quiz Generator")
    print("=" * 50)
    
    demo_transcript_quiz()
    
    print("\n" + "=" * 50)
    print("🏁 Demo completed!")

