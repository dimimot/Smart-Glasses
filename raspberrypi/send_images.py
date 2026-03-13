# Using Raspberry Pi camera (Picamera2 when available)
# Adds auto-recovery (reinitialize camera) if capture/upload fails.
# Reinit ONLY on camera errors (not on network/server/LM Studio errors)
# Kill zombie camera processes before reinit
# Clear logging per error type

import os
import sys
import time
import signal
import subprocess
import requests

# SETTINGS
SERVER_URL  = "http://192.168.1.13:5050/mobile/process?src=pi"  # Upload endpoint on your server
RESOLUTION  = (640, 480)                        # e.g., (1280, 720)
DELAY_S     = 1.0                               # Warm-up delay before capture
SKIP_N      = 5                                 # Frames to skip for exposure/white-balance stabilization
OUTFILE     = "/dev/shm/send_photo.jpg"         # Temporary image path (use /dev/shm to avoid SD writes)
INTERVAL_S  = 10.0                              # Capture + send every 10 seconds
TIMEOUT_S   = 20.0                              # HTTP timeout

running = True
camera = None
CamImpl = None

def _handle_sig(sig, frame):
    # Gracefully stop the main loop on SIGINT/SIGTERM
    global running
    running = False
    print("Stopping...")

def ensure_rpicamera():
    # Initialize camera: prefer Picamera2, fallback to legacy picamera
    global CamImpl, camera
    if CamImpl is not None:
        return

    # Prefer Picamera2
    try:
        from picamera2 import Picamera2
        CamImpl = "picamera2"
        camera = Picamera2()
        config = camera.create_still_configuration(
            main={"size": RESOLUTION, "format": "RGB888"},
            buffer_count=3
        )
        camera.configure(config)
        camera.start()
        time.sleep(DELAY_S)
        # Skip a few frames to stabilize exposure/white balance
        for _ in range(max(0, SKIP_N)):
            camera.capture_array()
        print("Picamera2 OK")
        return
    except Exception:
        pass

    # Fallback: legacy picamera
    try:
        import picamera
        CamImpl = "picamera-legacy"
        camera = picamera.PiCamera()
        camera.resolution = RESOLUTION
        camera.start_preview()
        time.sleep(DELAY_S)
        print("Legacy picamera OK")
        return
    except Exception:
        print("Picamera2 or legacy picamera not found.")
        print("Install: sudo apt update && sudo apt install -y python3-picamera2 libcamera-apps")
        sys.exit(1)

def capture_image():
    # Save a JPEG into OUTFILE
    if CamImpl == "picamera2":
        # Use capture_file to write directly to a file (fits the file-based flow)
        camera.capture_file(OUTFILE, format="jpeg")
    else:
        camera.capture(OUTFILE, format="jpeg", quality=90)

    # Basic sanity check on the produced file
    if not (os.path.exists(OUTFILE) and os.path.getsize(OUTFILE) > 0):
        raise RuntimeError("Image was not created or is empty.")

def send_image():
    # Send the file using multipart/form-data with field name 'image'
    with open(OUTFILE, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        r = requests.post(SERVER_URL, files=files, timeout=TIMEOUT_S)
        r.raise_for_status()

def cleanup():
    # Stop/close the camera safely
    global camera
    try:
        if camera is None:
            return
        if CamImpl == "picamera2":
            camera.stop()
        else:
            camera.stop_preview()
            camera.close()
    except Exception:
        pass

# Auto-recovery: close and re-open the camera when failures occur
def reinit_camera():
    global camera, CamImpl
    try:
        if camera:
            if CamImpl == "picamera2":
                camera.stop()
            else:
                camera.stop_preview()
                camera.close()
    except Exception:
        pass
    camera = None
    CamImpl = None

    # Kill any zombie camera processes before reinit to avoid "camera already in use" errors
    try:
        subprocess.run(["pkill", "-f", "libcamera"], capture_output=True)
        subprocess.run(["pkill", "-f", "rpicam"], capture_output=True)
    except Exception:
        pass

    time.sleep(1.0)  # slightly longer sleep after kill to let processes terminate
    ensure_rpicamera()

def main():
    # Prepare camera and signals, then run periodic capture/send loop
    ensure_rpicamera()
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    print(f"Sending a photo every {INTERVAL_S}s to: {SERVER_URL}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Temporary file: {OUTFILE}")

    next_time = time.monotonic()
    while running:
        camera_error = False

        # --- Step 1: Capture ---
        try:
            capture_image()
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] CAMERA ERROR: {e}")
            camera_error = True

        # --- Step 2: Send (only if capture succeeded) ---
        if not camera_error:
            try:
                send_image()
                print(f"[{time.strftime('%H:%M:%S')}] sent {OUTFILE} OK")
            except requests.exceptions.ConnectionError as e:
                print(f"[{time.strftime('%H:%M:%S')}] NETWORK/SERVER ERROR (no reinit): {e}")
            except requests.exceptions.Timeout as e:
                print(f"[{time.strftime('%H:%M:%S')}] TIMEOUT - server or LM Studio too slow (no reinit): {e}")
            except requests.exceptions.HTTPError as e:
                print(f"[{time.strftime('%H:%M:%S')}] HTTP ERROR {e.response.status_code} - server/LM Studio error (no reinit): {e}")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] UNKNOWN SEND ERROR (no reinit): {e}")

        # --- Step 3: Reinit ONLY on camera errors ---
        if camera_error:
            try:
                reinit_camera()
                print(f"[{time.strftime('%H:%M:%S')}] Camera reinitialized.")
            except Exception as e2:
                print(f"[{time.strftime('%H:%M:%S')}] Camera reinit failed: {e2}")

        next_time += INTERVAL_S
        sleep_for = max(0.0, next_time - time.monotonic())
        time.sleep(sleep_for)

    cleanup()
    print("Exited.")

if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()