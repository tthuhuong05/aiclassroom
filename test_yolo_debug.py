#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để debug YOLO detection
Chạy với: python test_yolo_debug.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Enable debug mode
os.environ["AI_DEBUG"] = "1"

def test_yolo_status():
    """Kiểm tra trạng thái YOLO model"""
    print("=" * 60)
    print("KIỂM TRA TRẠNG THÁI YOLO")
    print("=" * 60)
    
    try:
        from services.face_recognition_service import face_recognition_service
        
        status = face_recognition_service.debug_status()
        
        print("\n[YOLO Status]")
        print(f"  - YOLO Face: {'✓' if status.get('yolo_face') else '✗'}")
        print(f"  - COCO DNN: {'✓' if status.get('coco_dnn') else '✗'}")
        print(f"  - COCO Backend: {status.get('coco_backend', 'N/A')}")
        print(f"  - COCO Classes: {status.get('coco_num_classes', 0)}")
        print(f"  - Enhanced Object Detector: {status.get('ext_object_backend', 'disabled')}")
        
        print("\n[Config]")
        cfg = status.get('cfg', {})
        print(f"  - OBJ_CONF: {cfg.get('OBJ_CONF', 0.25)}")
        print(f"  - OBJ_SCORE: {cfg.get('OBJ_SCORE', 0.30)}")
        print(f"  - OBJ_INPUT: {cfg.get('OBJ_INPUT', 640)}")
        print(f"  - OBJECT_BACKEND: {cfg.get('OBJECT_BACKEND', 'auto')}")
        
        # Check model files
        print("\n[Model Files]")
        base = Path("services/models/coco")
        if base.exists():
            print(f"  - Model directory exists: {base}")
            for pattern in ["*.onnx", "*.pb", "*.pbtxt", "*.names"]:
                files = list(base.glob(pattern))
                if files:
                    for f in files:
                        size = f.stat().st_size / (1024 * 1024)  # MB
                        print(f"    ✓ {f.name} ({size:.2f} MB)")
        else:
            print(f"  ✗ Model directory not found: {base}")
            print(f"    Tạo thư mục và tải model theo INSTALL_YOLO.md")
        
        return status.get('coco_dnn') or status.get('yolo_face')
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yolo_detection():
    """Test YOLO detection với ảnh mẫu"""
    print("\n" + "=" * 60)
    print("TEST YOLO DETECTION")
    print("=" * 60)
    
    try:
        import cv2
        import numpy as np
        from services.face_recognition_service import face_recognition_service
        
        # Tạo ảnh test đơn giản (có thể thay bằng ảnh thật)
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        test_img[:] = (100, 100, 100)  # Màu xám
        
        # Vẽ một hình chữ nhật giả làm vật thể
        cv2.rectangle(test_img, (200, 150), (450, 350), (255, 255, 255), -1)
        
        # Encode thành bytes
        _, img_bytes = cv2.imencode('.jpg', test_img)
        img_bytes = img_bytes.tobytes()
        
        print("\n[Testing Object Detection]")
        result = face_recognition_service.detect_faces_and_objects(img_bytes)
        
        print(f"  - Face count: {result.get('face_count', 0)}")
        print(f"  - Object count: {result.get('object_count', 0)}")
        print(f"  - Suspicious objects: {len(result.get('suspicious_objects', []))}")
        
        if result.get('object_count', 0) > 0:
            print("\n  [Detected Objects]")
            for obj in result.get('suspicious_objects', []):
                print(f"    - {obj.get('type', 'unknown')}: {obj.get('score', 0):.3f} at {obj.get('position', (0,0,0,0))}")
        
        if result.get('face_count', 0) > 0:
            print("\n  [Detected Faces]")
            for face in result.get('faces', []):
                print(f"    - Face at {face}")
        
        if 'error' in result:
            print(f"\n  ✗ ERROR: {result['error']}")
        
        return result.get('object_count', 0) > 0 or result.get('face_count', 0) > 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_real_image():
    """Test với ảnh thật nếu có"""
    print("\n" + "=" * 60)
    print("TEST VỚI ẢNH THẬT (nếu có)")
    print("=" * 60)
    
    # Tìm ảnh test trong thư mục
    test_images = [
        Path("test_image.jpg"),
        Path("test_image.png"),
        Path("test.jpg"),
        Path("test.png"),
    ]
    
    for img_path in test_images:
        if img_path.exists():
            print(f"\n[Found test image: {img_path}]")
            try:
                import cv2
                from services.face_recognition_service import face_recognition_service
                
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                
                _, img_bytes = cv2.imencode('.jpg', img)
                img_bytes = img_bytes.tobytes()
                
                result = face_recognition_service.detect_faces_and_objects(img_bytes)
                
                print(f"  - Face count: {result.get('face_count', 0)}")
                print(f"  - Object count: {result.get('object_count', 0)}")
                
                if result.get('object_count', 0) > 0:
                    print("\n  [Detected Objects]")
                    for obj in result.get('suspicious_objects', []):
                        print(f"    - {obj.get('type', 'unknown')}: {obj.get('score', 0):.3f}")
                
                return True
                
            except Exception as e:
                print(f"  ERROR: {e}")
    
    print("  [No test images found]")
    print("  Đặt ảnh test.jpg hoặc test.png trong thư mục gốc để test")
    return False

def main():
    print("\n" + "=" * 60)
    print("YOLO DEBUG TEST SCRIPT")
    print("=" * 60)
    
    # Test 1: Status
    status_ok = test_yolo_status()
    
    # Test 2: Detection với ảnh test
    if status_ok:
        detection_ok = test_yolo_detection()
    else:
        print("\n⚠ YOLO model không được load. Kiểm tra:")
        print("  1. Thư mục services/models/coco/ có tồn tại không?")
        print("  2. File model (.onnx) có trong thư mục không?")
        print("  3. Xem hướng dẫn trong INSTALL_YOLO.md")
        detection_ok = False
    
    # Test 3: Ảnh thật
    test_with_real_image()
    
    print("\n" + "=" * 60)
    print("KẾT QUẢ")
    print("=" * 60)
    print(f"  Status: {'✓ OK' if status_ok else '✗ FAILED'}")
    print(f"  Detection: {'✓ OK' if detection_ok else '✗ FAILED'}")
    print("\nNếu có lỗi, kiểm tra logs ở trên với AI_DEBUG=1")
    print("=" * 60)

if __name__ == "__main__":
    main()














