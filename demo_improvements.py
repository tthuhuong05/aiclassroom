#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script để kiểm tra các cải tiến video bài giảng AI
- Hình ảnh phù hợp với nội dung
- Nội dung chuyên sâu thay vì chỉ giới thiệu
- Giọng người thật thay vì giọng Google
"""

import os
import sys
import tempfile
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent))

from services.doc_video_service import make_gemini_lecture_video, is_human_voice_available
from services.human_voice_service import human_voice_service

def check_voice_setup():
    """Kiểm tra cấu hình giọng người thật"""
    print("🔍 Kiểm tra cấu hình giọng người thật...")
    
    if is_human_voice_available():
        print("✅ ElevenLabs đã được cấu hình!")
        
        # Test voice synthesis
        try:
            test_text = "Xin chào! Đây là test giọng người thật từ ElevenLabs."
            result = human_voice_service.synthesize_speech(test_text)
            if result.get("success"):
                print("✅ Test giọng người thật thành công!")
                return True
            else:
                print(f"❌ Test giọng người thật thất bại: {result.get('error')}")
        except Exception as e:
            print(f"❌ Lỗi test giọng người thật: {e}")
    else:
        print("❌ ElevenLabs chưa được cấu hình!")
        print("📖 Vui lòng xem hướng dẫn trong VOICE_SETUP_GUIDE.md")
    
    return False

def create_sample_document():
    """Tạo tài liệu mẫu để test"""
    sample_content = """
# Machine Learning và Deep Learning

## Giới thiệu
Machine Learning (ML) là một nhánh của trí tuệ nhân tạo (AI) tập trung vào việc phát triển các thuật toán và mô hình thống kê cho phép máy tính học và cải thiện hiệu suất từ dữ liệu mà không cần được lập trình rõ ràng.

## Các loại Machine Learning

### 1. Supervised Learning (Học có giám sát)
Supervised learning sử dụng dữ liệu đã được gắn nhãn để huấn luyện mô hình. Mô hình học từ các ví dụ đầu vào và đầu ra tương ứng.

**Ví dụ:**
- Phân loại email spam/không spam
- Dự đoán giá nhà dựa trên diện tích, vị trí
- Nhận dạng hình ảnh

**Thuật toán phổ biến:**
- Linear Regression
- Decision Trees
- Random Forest
- Support Vector Machines (SVM)
- Neural Networks

### 2. Unsupervised Learning (Học không giám sát)
Unsupervised learning tìm kiếm các pattern ẩn trong dữ liệu không có nhãn.

**Ví dụ:**
- Phân nhóm khách hàng
- Phát hiện anomaly
- Giảm chiều dữ liệu

**Thuật toán phổ biến:**
- K-Means Clustering
- Hierarchical Clustering
- Principal Component Analysis (PCA)
- DBSCAN

### 3. Reinforcement Learning (Học tăng cường)
Reinforcement learning học thông qua tương tác với môi trường và nhận feedback dưới dạng reward hoặc penalty.

**Ví dụ:**
- Game AI (AlphaGo, Chess AI)
- Autonomous vehicles
- Trading algorithms

## Deep Learning

Deep Learning là một nhánh của Machine Learning sử dụng Neural Networks với nhiều lớp ẩn để học các pattern phức tạp từ dữ liệu.

### Kiến trúc Deep Learning

#### 1. Convolutional Neural Networks (CNN)
CNN được thiết kế đặc biệt cho xử lý dữ liệu có cấu trúc grid như hình ảnh.

**Ứng dụng:**
- Computer Vision
- Image Classification
- Object Detection
- Medical Image Analysis

#### 2. Recurrent Neural Networks (RNN)
RNN được thiết kế để xử lý dữ liệu tuần tự như text, speech, time series.

**Ứng dụng:**
- Natural Language Processing
- Speech Recognition
- Time Series Prediction
- Machine Translation

#### 3. Transformer Architecture
Transformer sử dụng attention mechanism để xử lý các sequence dài hiệu quả hơn RNN.

**Ứng dụng:**
- GPT models
- BERT
- Machine Translation
- Text Generation

## Quy trình Machine Learning

### 1. Data Collection
Thu thập dữ liệu từ các nguồn khác nhau, đảm bảo chất lượng và tính đại diện.

### 2. Data Preprocessing
- Data cleaning
- Feature engineering
- Data normalization
- Handling missing values

### 3. Model Selection
Chọn thuật toán phù hợp dựa trên:
- Loại bài toán
- Kích thước dữ liệu
- Tính chất dữ liệu
- Yêu cầu hiệu suất

### 4. Model Training
Huấn luyện mô hình trên training data với các hyperparameters phù hợp.

### 5. Model Evaluation
Đánh giá mô hình trên test data sử dụng các metrics phù hợp:
- Accuracy, Precision, Recall, F1-score
- RMSE, MAE cho regression
- Cross-validation

### 6. Model Deployment
Triển khai mô hình vào production environment.

## Ứng dụng thực tế

### Healthcare
- Medical diagnosis
- Drug discovery
- Personalized treatment
- Medical image analysis

### Finance
- Fraud detection
- Algorithmic trading
- Credit scoring
- Risk assessment

### Technology
- Search engines
- Recommendation systems
- Autonomous vehicles
- Virtual assistants

### E-commerce
- Product recommendation
- Price optimization
- Customer segmentation
- Inventory management

## Thách thức và hạn chế

### 1. Data Quality
- Bias trong dữ liệu
- Missing data
- Noisy data
- Data privacy

### 2. Model Interpretability
- Black box problem
- Explainable AI
- Model transparency

### 3. Computational Resources
- High computational cost
- GPU requirements
- Energy consumption

### 4. Ethical Considerations
- Algorithmic bias
- Fairness
- Privacy concerns
- Job displacement

## Tương lai của Machine Learning

### 1. AutoML
Tự động hóa quá trình ML từ data preprocessing đến model deployment.

### 2. Federated Learning
Học tập phân tán mà không cần chia sẻ dữ liệu thô.

### 3. Edge AI
Triển khai AI trên các thiết bị edge với tài nguyên hạn chế.

### 4. Quantum Machine Learning
Kết hợp quantum computing với machine learning.

## Kết luận

Machine Learning và Deep Learning đang thay đổi cách chúng ta giải quyết các vấn đề phức tạp. Từ healthcare đến finance, từ technology đến e-commerce, ML đang tạo ra những cơ hội và thách thức mới. Việc hiểu rõ các khái niệm cơ bản, quy trình phát triển, và ứng dụng thực tế sẽ giúp chúng ta tận dụng tối đa tiềm năng của công nghệ này.

Tuy nhiên, chúng ta cũng cần nhận thức được các thách thức về đạo đức, privacy, và bias để phát triển AI một cách có trách nhiệm và bền vững.
"""
    
    # Tạo file tạm
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    return temp_file.name

def demo_video_generation():
    """Demo tạo video bài giảng với các cải tiến"""
    print("\n🎬 Demo tạo video bài giảng với các cải tiến...")
    
    # Tạo tài liệu mẫu
    sample_doc = create_sample_document()
    print(f"📄 Tạo tài liệu mẫu: {sample_doc}")
    
    # Tạo thư mục output
    output_dir = "demo_output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Tạo video với Gemini (có các cải tiến)
        print("\n🤖 Tạo video với AI Gemini (nội dung chuyên sâu + hình ảnh phù hợp + giọng người thật)...")
        result = make_gemini_lecture_video(
            src_path=sample_doc,
            out_dir=output_dir,
            title="Machine Learning và Deep Learning - Bài giảng chuyên sâu"
        )
        
        print("\n✅ Video đã được tạo thành công!")
        print(f"📹 Video: {result['video_path']}")
        print(f"📝 Caption: {result['caption_path']}")
        print(f"📄 Script: {len(result['script_text'])} ký tự")
        
        # Hiển thị thông tin bài giảng
        lecture_info = result.get('lecture_info', {})
        print(f"\n📊 Thông tin bài giảng:")
        print(f"   - Tiêu đề: {lecture_info.get('title', 'N/A')}")
        print(f"   - Chủ đề chính: {lecture_info.get('main_topic', 'N/A')}")
        print(f"   - Khái niệm cốt lõi: {', '.join(lecture_info.get('core_concepts', []))}")
        print(f"   - Số slides: {lecture_info.get('total_slides', 'N/A')}")
        print(f"   - Thời lượng: {lecture_info.get('total_duration_seconds', 'N/A'):.1f} giây")
        
        return result
        
    except Exception as e:
        print(f"❌ Lỗi tạo video: {e}")
        return None
    
    finally:
        # Xóa file tạm
        try:
            os.unlink(sample_doc)
        except:
            pass

def main():
    """Hàm main"""
    print("🚀 Demo Video Bài Giảng AI - Các Cải Tiến")
    print("=" * 50)
    
    # Kiểm tra cấu hình giọng người thật
    voice_ok = check_voice_setup()
    
    if not voice_ok:
        print("\n⚠️ Lưu ý: Giọng người thật chưa được cấu hình.")
        print("   Hệ thống sẽ sử dụng giọng máy fallback.")
        print("   Để có chất lượng tốt nhất, vui lòng cấu hình ElevenLabs.")
    
    # Demo tạo video
    result = demo_video_generation()
    
    if result:
        print("\n🎉 Demo hoàn thành!")
        print("\n📋 Các cải tiến đã được áp dụng:")
        print("   ✅ Hình ảnh phù hợp với nội dung (AI phân tích từ khóa)")
        print("   ✅ Nội dung chuyên sâu thay vì chỉ giới thiệu")
        print("   ✅ Giọng người thật ưu tiên (ElevenLabs)")
        print("   ✅ Script tự nhiên như giáo viên thật")
        print("   ✅ Cấu trúc logic từ cơ bản đến nâng cao")
        
        print(f"\n📁 Kết quả được lưu trong: {result['video_path']}")
    else:
        print("\n❌ Demo thất bại. Vui lòng kiểm tra lỗi và thử lại.")

if __name__ == "__main__":
    main()
