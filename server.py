import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import os
import sys
import time
import threading
import secrets
import webbrowser

import io
import math

try:
    import feather
    import feather.charts
    HAS_FEATHER = True
except ImportError:
    HAS_FEATHER = False

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIRECTORY, "config.json")

def render_feather_graphic(graphic_type="lamp", color_hex="#3b82f6", brightness=100, is_on=True, sku="H60A1", loc="Ceiling Light"):
    color_hex = color_hex if color_hex.startswith("#") else f"#{color_hex}"
    brightness = max(0, min(100, int(brightness)))
    
    if HAS_FEATHER:
        try:
            if graphic_type == "gauge":
                val = float(brightness if is_on else 0)
                display_color = color_hex if is_on else "#475569"
                title = f"{sku} OUTPUT" if is_on else f"{sku} (OFF)"
                gauge = feather.charts.Gauge(
                    value=val,
                    min_value=0.0,
                    max_value=100.0,
                    width=480,
                    height=260,
                    title=title,
                    unit="%",
                    theme="dark",
                    color=display_color,
                    arc_width=18.0
                )
                canvas = gauge.render()
                canvas.draw_text("RENDERED WITH FEATHER ENGINE", 140, 246, size=10, color="#475569")
                img = canvas.to_pillow()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
            else:
                # Architectural Lamp Fixture Render
                w, h = 480, 260
                canvas = feather.Canvas(w, h, background="#0a0e17")
                cx, cy = 240, 115
                
                # Housing outer rim
                canvas.draw_circle(cx, cy, 96, fill="#111622", stroke="#1e293b", stroke_width=2.0)
                canvas.draw_circle(cx, cy, 84, fill="#0f172a", stroke="#334155", stroke_width=1.0)
                
                if is_on:
                    canvas.draw_glow(cx, cy, 70, blur=24.0, color=color_hex)
                    canvas.draw_circle(cx, cy, 32, fill=color_hex, stroke="#ffffff", stroke_width=1.0)
                    for i in range(12):
                        angle = i * (2 * math.pi / 12)
                        sx = cx + math.cos(angle) * 60
                        sy = cy + math.sin(angle) * 60
                        canvas.draw_circle(sx, sy, 11, fill=color_hex, stroke="#ffffff", stroke_width=0.8)
                else:
                    canvas.draw_circle(cx, cy, 32, fill="#1e293b", stroke="#334155", stroke_width=1.0)
                    for i in range(12):
                        angle = i * (2 * math.pi / 12)
                        sx = cx + math.cos(angle) * 60
                        sy = cy + math.sin(angle) * 60
                        canvas.draw_circle(sx, sy, 11, fill="#1e293b", stroke="#334155", stroke_width=0.8)
                
                status_str = f"{loc.upper()}  •  {brightness}%" if is_on else f"{loc.upper()}  •  OFF / STANDBY"
                canvas.draw_text(status_str, 20, 240, size=11, color="#64748b")
                canvas.draw_text("FEATHER ENGINE", 365, 240, size=10, color="#38bdf8")
                
                img = canvas.to_pillow()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
        except Exception as e:
            print(f"Feather render error: {e}")

    # Fallback with PIL if feather is unavailable
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (480, 260), "#0a0e17")
        draw = ImageDraw.Draw(img)
        cx, cy = 240, 115
        fill_col = color_hex if is_on else "#1e293b"
        draw.ellipse([cx-80, cy-80, cx+80, cy+80], outline="#334155", width=2)
        draw.ellipse([cx-30, cy-30, cx+30, cy+30], fill=fill_col, outline="#ffffff" if is_on else "#334155")
        status_str = f"{sku}  •  {brightness}%" if is_on else f"{sku}  •  OFF"
        draw.text((20, 235), status_str, fill="#64748b")
        draw.text((370, 235), "FEATHER FALLBACK", fill="#38bdf8")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return {
        "govee_api_key": "YOUR_GOVEE_API_KEY_HERE",
        "access_pin": "1702",
        "device_locations": {}
    }

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config.json: {e}")

CONFIG = load_config()

# Sessions and timer state
VALID_TOKENS = set()
timer_lock = threading.Lock()
timer_target_time = None
timer_target_device = None
timer_target_sku = None
timer_thread = None

def call_govee_api(endpoint, method="POST", payload=None):
    url = f"https://openapi.api.govee.com/router/api/v1/{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Govee-API-Key": CONFIG.get("govee_api_key", "")
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        return {"code": e.code, "message": f"HTTP Error {e.code}: {err_body}"}
    except Exception as e:
        return {"code": 500, "message": str(e)}

def timer_worker():
    global timer_target_time, timer_target_device, timer_target_sku
    while True:
        with timer_lock:
            if timer_target_time is None:
                break
            remaining = timer_target_time - time.time()
            if remaining <= 0:
                dev = timer_target_device
                sku = timer_target_sku
                timer_target_time = None
                print(f"[Timer] Auto-off triggered for {dev}. Turning lamp off...")
                if dev and sku:
                    call_govee_api("device/control", "POST", {
                        "requestId": f"timer-off-{int(time.time())}",
                        "payload": {
                            "sku": sku,
                            "device": dev,
                            "capability": {
                                "type": "devices.capabilities.on_off",
                                "instance": "powerSwitch",
                                "value": 0
                            }
                        }
                    })
                break
        time.sleep(1)

class ControllerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def is_authenticated(self):
        auth_header = self.headers.get("X-Auth-Token", "")
        return auth_header in VALID_TOKENS

    def send_json(self, status_code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/devices":
            if not self.is_authenticated():
                self.send_json(401, {"error": "Unauthorized"})
                return

            res = call_govee_api("user/devices", method="GET")
            if res.get("code") == 200 and "data" in res:
                locations = CONFIG.get("device_locations", {})
                for d in res["data"]:
                    dev_id = d.get("device", "")
                    d["location"] = locations.get(dev_id, "Room not set")
            self.send_json(200, res)
            return

        elif path == "/api/status":
            if not self.is_authenticated():
                self.send_json(401, {"error": "Unauthorized"})
                return

            device = query.get("device", [""])[0]
            sku = query.get("sku", [""])[0]

            if not device or not sku:
                self.send_json(400, {"error": "Missing device or sku parameter"})
                return

            res = call_govee_api("device/state", method="POST", payload={
                "requestId": f"state-{int(time.time())}",
                "payload": {
                    "sku": sku,
                    "device": device
                }
            })
            self.send_json(200, res)
            return

        elif path == "/api/timer":
            with timer_lock:
                if timer_target_time and timer_target_time > time.time():
                    remaining = int(timer_target_time - time.time())
                    self.send_json(200, {
                        "active": True,
                        "remaining": remaining,
                        "device": timer_target_device
                    })
                else:
                    self.send_json(200, {"active": False, "remaining": 0})
            return

        elif path == "/api/check-auth":
            self.send_json(200, {"authenticated": self.is_authenticated()})
            return

        elif path == "/api/graphics/lamp.png":
            g_type = query.get("type", ["lamp"])[0]
            color = query.get("color", ["#3b82f6"])[0]
            try:
                brightness = int(query.get("brightness", ["100"])[0])
            except ValueError:
                brightness = 100
            power = query.get("power", ["1"])[0] in ["1", "true", "True"]
            sku = query.get("sku", ["H60A1"])[0]
            loc = query.get("loc", ["Ceiling Light"])[0]

            png_bytes = render_feather_graphic(
                graphic_type=g_type,
                color_hex=color,
                brightness=brightness,
                is_on=power,
                sku=sku,
                loc=loc
            )
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png_bytes)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(png_bytes)
            return

        # Serve static files (index.html, etc.)
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if self.path == "/api/login":
            entered_pin = str(req_data.get("pin", "")).strip()
            expected_pin = str(CONFIG.get("access_pin", "1702")).strip()
            if entered_pin == expected_pin:
                token = secrets.token_hex(16)
                VALID_TOKENS.add(token)
                self.send_json(200, {"success": True, "token": token})
            else:
                self.send_json(401, {"success": False, "error": "Invalid PIN"})
            return

        # Protected endpoints require auth
        if not self.is_authenticated():
            self.send_json(401, {"error": "Unauthorized"})
            return

        if self.path == "/api/control":
            sku = req_data.get("sku")
            device = req_data.get("device")
            capability = req_data.get("capability")

            if not sku or not device or not capability:
                self.send_json(400, {"error": "Missing sku, device, or capability"})
                return

            res = call_govee_api("device/control", method="POST", payload={
                "requestId": f"ctrl-{int(time.time() * 1000)}",
                "payload": {
                    "sku": sku,
                    "device": device,
                    "capability": capability
                }
            })
            self.send_json(200, res)
            return

        elif self.path == "/api/devices/location":
            dev_id = req_data.get("device")
            loc = req_data.get("location", "").strip()
            if dev_id and loc:
                CONFIG.setdefault("device_locations", {})[dev_id] = loc
                save_config(CONFIG)
                self.send_json(200, {"success": True, "device": dev_id, "location": loc})
            else:
                self.send_json(400, {"error": "Invalid device or location"})
            return

        elif self.path == "/api/timer":
            global timer_target_time, timer_target_device, timer_target_sku, timer_thread
            minutes = req_data.get("minutes", 0)
            sku = req_data.get("sku")
            device = req_data.get("device")

            with timer_lock:
                if minutes > 0 and device and sku:
                    timer_target_time = time.time() + (minutes * 60)
                    timer_target_device = device
                    timer_target_sku = sku
                    if timer_thread is None or not timer_thread.is_alive():
                        timer_thread = threading.Thread(target=timer_worker, daemon=True)
                        timer_thread.start()
                    self.send_json(200, {"success": True, "remaining": int(minutes * 60)})
                else:
                    timer_target_time = None
                    timer_target_device = None
                    timer_target_sku = None
                    self.send_json(200, {"success": True, "cancelled": True})
            return

        self.send_json(404, {"error": "Not found"})

socketserver.TCPServer.allow_reuse_address = True

def run():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), ControllerHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 55)
        print(" GOVEE MULTI-LAMP CONTROLLER")
        print("=" * 55)
        print(f" URL:        {url}")
        print(f" Access PIN: {CONFIG.get('access_pin', '1702')}")
        print(" Credentials loaded from config.json (protected).")
        print(" Press Ctrl+C to stop.")
        print("=" * 55)
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.shutdown()

if __name__ == "__main__":
    run()
