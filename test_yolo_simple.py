#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test YOLO đơn giản - Kiểm tra từng bước
"""

import os
import sys
from pathlib import Path

# Enable debug
os.environ["AI_DEBUG"] = "1"

sys.path.append(str(Path(__file__).parent))

# Try to import cv2, but don't fail if not available
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("[WARN] OpenCV (cv2) not available - some tests will be skipped")

def test_yolo_model_load():
    """Test xem model co duoc load khong"""
    print("=" * 60)
    print("TEST 1: Kiem tra model YOLO")
    print("=" * 60)
    
    try:
        from services.face_recognition_service import face_recognition_service
        
        status = face_recognition_service.debug_status()
        
        print(f"\nYOLO Status:")
        print(f"  - COCO DNN loaded: {status.get('coco_dnn', False)}")
        print(f"  - COCO Backend: {status.get('coco_backend', 'N/A')}")
        print(f"  - COCO Classes: {status.get('coco_num_classes', 0)}")
        
        # Check model files
        base = Path("services/models/coco")
        if base.exists():
            print(f"\nModel directory exists: {base}")
            onnx_files = list(base.glob("*.onnx"))
            names_files = list(base.glob("*.names"))
            
            print(f"  ONNX files: {len(onnx_files)}")
            for f in onnx_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"    - {f.name} ({size_mb:.2f} MB)")
            
            print(f"  Names files: {len(names_files)}")
            for f in names_files:
                print(f"    - {f.name}")
        else:
            print(f"\n[FAIL] Model directory NOT found: {base}")
            print("  Tao thu muc va tai model theo INSTALL_YOLO.md")
        
        return status.get('coco_dnn', False)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yolo_inference():
    """Test YOLO inference với ảnh đơn giản"""
    print("\n" + "=" * 60)
    print("TEST 2: Test YOLO Inference")
    print("=" * 60)
    
    if not HAS_CV2:
        print("\n⚠ Skipping inference test - OpenCV not available")
        return False
    
    try:
        from services.face_recognition_service import face_recognition_service
        
        if face_recognition_service._obj_net is None:
            print("\n[FAIL] YOLO model not loaded - skipping inference test")
            return False
        
        # Tạo ảnh test đơn giản
        print("\nCreating test image...")
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (128, 128, 128)  # Màu xám
        cv2.rectangle(img, (200, 150), (450, 350), (255, 255, 255), -1)  # Hình chữ nhật trắng
        
        print(f"Test image shape: {img.shape}")
        
        # Test object detection
        print("\nTesting object detection...")
        result = face_recognition_service.detect_faces_and_objects(
            cv2.imencode('.jpg', img)[1].tobytes()
        )
        
        print(f"\nResults:")
        print(f"  - Face count: {result.get('face_count', 0)}")
        print(f"  - Object count: {result.get('object_count', 0)}")
        print(f"  - Suspicious objects: {len(result.get('suspicious_objects', []))}")
        
        if result.get('object_count', 0) > 0:
            print(f"\n  Detected objects:")
            for obj in result.get('suspicious_objects', []):
                print(f"    - {obj.get('type', 'unknown')}: {obj.get('score', 0):.3f} at {obj.get('position', (0,0,0,0))}")
        
        if 'error' in result:
            print(f"\n  [ERROR]: {result['error']}")
        
        return result.get('object_count', 0) > 0 or result.get('face_count', 0) > 0
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yolo_direct():
    """Test YOLO trực tiếp không qua wrapper"""
    print("\n" + "=" * 60)
    print("TEST 3: Test YOLO Direct (không qua wrapper)")
    print("=" * 60)
    
    if not HAS_CV2:
        print("\n⚠ Skipping direct test - OpenCV not available")
        return False
    
    try:
        from services.face_recognition_service import face_recognition_service
        
        if face_recognition_service._obj_net is None:
            print("\n[FAIL] YOLO model not loaded - skipping direct test")
            return False
        
        # Tạo ảnh test
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (128, 128, 128)
        cv2.rectangle(img, (200, 150), (450, 350), (255, 255, 255), -1)
        
        print(f"\nTesting direct YOLO call...")
        print(f"Input image shape: {img.shape}")
        
        # Test trực tiếp
        results = face_recognition_service._detect_objects_yolo_onnx(img)
        
        print(f"\nDirect YOLO results: {len(results)} detections")
        for i, obj in enumerate(results):
            print(f"  {i+1}. {obj.get('type', 'unknown')}: {obj.get('score', 0):.3f} at {obj.get('position', (0,0,0,0))}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("YOLO SIMPLE TEST")
    print("=" * 60)
    
    # Test 1: Model load
    model_loaded = test_yolo_model_load()
    
    # Test 2: Inference
    if model_loaded:
        inference_ok = test_yolo_inference()
        direct_ok = test_yolo_direct()
    else:
        print("\n[WARN] Skipping inference tests - model not loaded")
        inference_ok = False
        direct_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Model loaded: {'OK' if model_loaded else 'FAIL'}")
    print(f"  Inference test: {'OK' if inference_ok else 'FAIL'}")
    print(f"  Direct test: {'OK' if direct_ok else 'FAIL'}")
    
    if not model_loaded:
        print("\n[WARN] YOLO model khong duoc load!")
        print("  Kiem tra:")
        print("    1. File model co trong services/models/coco/ khong?")
        print("    2. Xem logs khi khoi dong: [OK] Object detector:")
        print("    3. Xem INSTALL_YOLO.md de tai model")
    elif not inference_ok and not direct_ok:
        print("\n[WARN] YOLO model duoc load nhung khong phat hien duoc gi!")
        print("  Kiem tra:")
        print("    1. Xem logs voi AI_DEBUG=1 de xem output shape")
        print("    2. Co the confidence threshold qua cao")
        print("    3. Co the output format khac voi expected")
    else:
        print("\n[OK] YOLO hoat dong!")
    
    print("=" * 60)

if __name__ == "__main__":
    main()

