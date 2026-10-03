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

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIRECTORY, "config.json")

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
