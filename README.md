# Smart Glasses: An image description system powered by Vision Language Models.
Send images from a mobile device (Flutter app) or Raspberry Pi and receive descriptions via a Python server.

**Repository structure:** 3 autonomous projects in 1 monorepo
- **v2/** - Python backend (code)
- **flutter_app/** - Mobile app (iOS/Android)
- **raspberrypi/** - RPi integration script

## Functionalities
-  **Image capture** from mobile or Raspberry Pi
-  **Image description** using Qwen3-VL (or BLIP, LLaVA)
-  **Traffic light detection** (YOLO) - optional
-  **Results storage**
-  **Performance timing logs**

## Project Structure

```
Smart_Glasses/
├── v2/                          ← Python FastAPI server (code)
├── Data/                        ← Data, logs and config files
│   ├── certs/
│   ├── Generated_Text/
│   ├── logs/
│   ├── Output_image/
│   ├── received_images/
│   └── system_prompts_qwen/
├── flutter_app/                 ← Mobile application
│   └── tts_cam_test2/           ← Flutter project
├── raspberrypi/                 ← RPi integration
│   ├── requirements.txt
│   └── send_images.py
├── requirements.txt             ← Server dependencies
└── README.md                    ← This file (Root guide)
```

**Version:** 2.0
**Python Version:** 3.9
**License:** GNU GENERAL PUBLIC LICENSE
