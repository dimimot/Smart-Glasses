# Smart Glasses - Raspberry Pi Integration

Script for Raspberry Pi that captures photos and sends them to the VLM server for image description.
Capture images from Raspberry Pi camera module and sends to the VLM server.

### Prerequisites
- Raspberry Pi Zero 2W
- Python 3.9
- Raspberry Pi V2.1 Camera Module
- Network connection (to the server): Change the `SERVER_URL` in `send_images.py` to point to your server's IP address and port.

### Installation

```bash
# 1. Clone repo to RPi
git clone <repo-url>
cd Smart_Glasses/raspberrypi

# 2. Create virtual environment
python3.9 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start script
python send_images.py

##  Project Structure
```

```
raspberrypi/
├── send_images.py          ← Main script
├── requirements.txt        ← Dependencies
└── README.md               ← This file
```
