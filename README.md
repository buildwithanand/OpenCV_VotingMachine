#  Multi-Modal Biometric Verification System

A Raspberry Pi and ESP32 based multi-modal biometric verification system that combines **face recognition, fingerprint verification, and physiological sensor verification** into a single integrated system.

The system performs multiple verification checks and controls Raspberry Pi GPIO outputs based on the verification results.

---

##  Overview

This project integrates multiple biometric and physiological verification techniques using a Raspberry Pi and ESP32.

The system includes:

-  Face Recognition
-  Fingerprint Verification
-  Heart Rate (BPM) Verification
-  Temperature Verification
-  SpO₂ Verification
-  Camera-Based Face Capture
-  Raspberry Pi GPIO Control
-  ESP32 Serial Communication
-  Flask-based Face Verification API

The Raspberry Pi acts as the central controller, while the ESP32 collects physiological sensor data and sends it to the Raspberry Pi through serial communication.

---

##  Features

- Multi-modal biometric verification
- Multiple face recognition algorithms
- Fingerprint-based authentication
- Real-time BPM verification
- Temperature verification
- SpO₂ verification
- Raspberry Pi GPIO control
- ESP32 to Raspberry Pi serial communication
- Flask REST API for face verification
- Face image preprocessing
- Face alignment
- Blur detection
- LBPH-based face recognition
- DeepFace-based face recognition
- Motion detection support
- Multi-threaded system controller

---

##  System Architecture
```text
                    ┌──────────────────────┐
                    │   System Controller  │
                    │ system_controller.py │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       Fingerprint        Face Recognition    ESP32
       Verification           │              Sensors
                              │                │
                              │                ├── BPM
                              │                ├── Temperature
                              │                └── SpO₂
                              │
                              ▼
                         Flask API
                              │
                              ▼
                     Verification Result
                              │
                              ▼
                    Raspberry Pi GPIO

```

## Project Structure

```text

Multi-Modal-Biometric-System/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── system_controller.py
│   │
│   ├── face/
│   │   ├── face_recognition_api.py
│   │   ├── deepface_api.py
│   │   ├── deepface_cosine_api.py
│   │   ├── lbph_face_api.py
│   │   ├── lbph_dataset_api.py
│   │   └── refined_lbph_face_api.py
│   │
│   ├── hardware/
│   │   ├── external_sensors.py
│   │   ├── fingerprint_verification.py
│   │   └── camera_capture.py
│   │
│   └── camera/
│       ├── pi_camera_capture.py
│       └── motion_detector.py
│
├── tests/
│   ├── sensor_hardware_test.py
│   └── biometric_hardware_test.py
│
├── models/
│   └── .gitkeep
│
└── dataset/
    └── .gitkeep

```
Motion Detection Pipeline
```text  
  Camera
     ↓
  Frame Difference
     ↓
  Grayscale
     ↓
  Gaussian Blur
     ↓
  Thresholding
     ↓
  Motion Pixel Count
     ↓
  Motion Detected
```
## System Workflow

                     START
                       │
                       ▼
              Start Flask Server
                       │
                       ▼
             Start Sensor Thread
                       │
                       ▼
              Wait for Fingerprint
                       │
                       ▼
            Fingerprint Verification
                       │
                       ▼
               Face Verification
                       │
                       ▼
             Sensor Stabilization
                       │
                       ▼
              Fresh Sensor Data
                       │
                       ▼
              Final Verification
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
        Face       Fingerprint    Sensors
                                   │
                          ┌────────┼────────┐
                          ▼        ▼        ▼
                         Temp     BPM      SpO₂
                          │        │        │
                          └────────┼────────┘
                                   ▼
                         GPIO Output Control
                                   │
                                   ▼
                                RESET
                                   │
                                   ▼
                                REPEAT




