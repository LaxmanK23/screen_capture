import os
import time
import threading
from io import BytesIO
from functools import wraps

from flask import Flask, Response, request, abort
from flask_socketio import SocketIO, emit, disconnect
import mss
import numpy as np
import cv2

# Input control (mouse/keyboard)
import pyautogui

# ---------------------- Configuration ----------------------
PASSWORD = os.environ.get("LRC_PASSWORD", "change-me")  # <<< set a strong env var!
HOST = os.environ.get("LRC_HOST", "0.0.0.0")
PORT = int(os.environ.get("LRC_PORT", "8010"))
FPS = int(os.environ.get("LRC_FPS", "10"))
JPEG_QUALITY = int(os.environ.get("LRC_JPEG_QUALITY", "70"))
# -----------------------------------------------------------

app = Flask(__name__, static_folder=None)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# Track auth'd socket session IDs
authorized_sids = set()

def require_token_ws(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        sid = request.sid
        if sid not in authorized_sids:
            emit("error", {"message": "Unauthorized"})
            return
        return func(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return "LAN Remote Control server is running. Open client.html on the controller and point it here."

@app.route("/stream")
def stream():
    token = request.args.get("token")
    if token != PASSWORD:
        return abort(401)

    def gen_frames():
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # primary display
            target_interval = 1.0 / FPS
            while True:
                start = time.time()
                img = np.array(sct.grab(monitor))  # BGRA
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # Optional downscale for bandwidth (keep width <= 1280)
                h, w, _ = frame.shape
                max_w = 1280
                if w > max_w:
                    scale = max_w / float(w)
                    frame = cv2.resize(frame, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if not ok:
                    continue
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                       buf.tobytes() + b"\r\n")
                elapsed = time.time() - start
                if elapsed < target_interval:
                    time.sleep(target_interval - elapsed)

    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ---------------------- WebSocket auth ----------------------
@socketio.on("connect")
def on_connect():
    emit("need_auth", {"ok": True})

@socketio.on("auth")
def on_auth(data):
    pwd = (data or {}).get("password", "")
    if pwd == PASSWORD:
        authorized_sids.add(request.sid)
        emit("auth_ok", {"ok": True})
    else:
        emit("auth_failed", {"ok": False})
        socketio.start_background_task(lambda: (time.sleep(1), disconnect()))

@socketio.on("disconnect")
def on_disconnect():
    authorized_sids.discard(request.sid)

# ---------------------- Control handlers ----------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

@socketio.on("mouse_move")
@require_token_ws
def on_mouse_move(data):
    nx = float(data.get("nx", 0.0))
    ny = float(data.get("ny", 0.0))
    screen_w, screen_h = pyautogui.size()
    x = int(clamp(nx, 0, 1) * (screen_w - 1))
    y = int(clamp(ny, 0, 1) * (screen_h - 1))
    pyautogui.moveTo(x, y)

@socketio.on("mouse_click")
@require_token_ws
def on_mouse_click(data):
    button = data.get("button", "left")
    double = bool(data.get("double", False))
    if double:
        pyautogui.doubleClick(button=button)
    else:
        pyautogui.click(button=button)

@socketio.on("key_type")
@require_token_ws
def on_key_type(data):
    text = data.get("text", "")
    if text:
        pyautogui.typewrite(text)

@socketio.on("key_press")
@require_token_ws
def on_key_press(data):
    key = data.get("key", "")
    if key:
        pyautogui.press(key)

@socketio.on("mouse_scroll")
@require_token_ws
def on_mouse_scroll(data):
    # data: {"dx": int, "dy": int}
    dy = int(data.get("dy", 0))
    dx = int(data.get("dx", 0))
    # Positive dy = scroll up in pyautogui; flip if you prefer
    pyautogui.scroll(dy)
    if dx:
        pyautogui.hscroll(dx)

@socketio.on("mouse_down")
@require_token_ws
def on_mouse_down(data):
    button = data.get("button", "left")
    pyautogui.mouseDown(button=button)

@socketio.on("mouse_up")
@require_token_ws
def on_mouse_up(data):
    button = data.get("button", "left")
    pyautogui.mouseUp(button=button)


# ---------------------- Run ----------------------
if __name__ == "__main__":
    print(f"[*] LAN Remote Control server on {HOST}:{PORT}")
    print("[*] Set LRC_PASSWORD env var to change password (default: 'change-me').")
    socketio.run(app, host=HOST, port=PORT)
