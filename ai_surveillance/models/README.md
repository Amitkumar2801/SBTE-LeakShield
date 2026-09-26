# Detection Models & Cascade Classifiers

This directory houses pre-trained weights and cascade classifier XML files used by `detect.py`:

- **Haar Cascades:**
  - `haarcascade_frontalface_default.xml` (Used for face localization & posture tracking)
  - `haarcascade_eye.xml` (Optional eye-contact tracking)
- **Deep Learning Weights (Optional / Advanced):**
  - MobileNet-SSD / YOLOv8 (.onnx or .pt) for dedicated smartphone detection classes (COCO class ID 67: `cell phone`).

## Adding Custom Weights
Place any trained `.onnx`, `.weights`, or `.xml` classifier files into this folder and reference them inside `ai_surveillance/detect.py`.
