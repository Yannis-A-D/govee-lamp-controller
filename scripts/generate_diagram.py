"""
Generates the project architecture graphic for the README using Feather.
Powered by: https://github.com/Yannis-A-D/feather
"""

import os
import feather

def generate_structure_graphic():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "structure.png")

    c = feather.Canvas(1040, 600, background="#07080b")

    # Title area
    c.draw_text("GOVEE LAMP CONTROLLER  —  SYSTEM ARCHITECTURE", 40, 48, size=18, color="#ffffff")
    c.draw_text("END-TO-END HYBRID CLOUD & LOCAL HARDWARE PIPELINE", 40, 72, size=11, color="#64748b")

    # Engine badge
    c.draw_rounded_rect(770, 36, 230, 32, rx=16, fill="#111827", stroke="#0284c7", stroke_width=1.5)
    c.draw_circle(785, 52, 5, fill="#38bdf8")
    c.draw_text("POWERED BY FEATHER", 798, 57, size=11, color="#38bdf8")

    # Column 1: Client
    c.draw_rounded_rect(40, 105, 290, 455, rx=18, fill="#0f1117", stroke="#1f2430", stroke_width=1.5)
    c.draw_text("CLIENT TIER (BROWSER)", 60, 138, size=13, color="#38bdf8")
    c.draw_text("Apple HomeKit Responsive UI", 60, 156, size=10, color="#64748b")

    items1 = [
        ("Apple HomeKit Interface", "Vanilla HTML5 / CSS3 / ES6", "#1a202c"),
        ("PIN Security Gate", "Protected 4-digit token unlock", "#1a202c"),
        ("Feather Dynamic Canvas", "Live luminaire & gauge stream", "#1e293b"),
        ("Web Audio Frequency Pulse", "Microphone FFT beat analysis", "#1a202c"),
        ("Screen Ambilight Mirror", "DisplayCapture color sync", "#1a202c"),
        ("Web Speech Controller", "Natural voice command engine", "#1a202c")
    ]
    y = 175
    for title, sub, fill in items1:
        c.draw_rounded_rect(56, y, 258, 52, rx=10, fill=fill, stroke="#2d3748", stroke_width=1.0)
        c.draw_text(title, 70, y + 22, size=11, color="#f1f5f9")
        c.draw_text(sub, 70, y + 38, size=9, color="#94a3b8")
        y += 62

    # Column 2: Backend Server
    c.draw_rounded_rect(375, 105, 290, 455, rx=18, fill="#0f1117", stroke="#1f2430", stroke_width=1.5)
    c.draw_text("LOCAL BACKEND SERVER", 395, 138, size=13, color="#34d399")
    c.draw_text("Python 3 Standard Library", 395, 156, size=10, color="#64748b")

    items2 = [
        ("HTTP Proxy Server (:8000)", "Zero-dependency socketserver", "#1a202c"),
        ("Session Auth Validator", "Cryptographic token handshake", "#1a202c"),
        ("Background Auto-Off Timer", "Threaded countdown worker", "#1a202c"),
        ("Feather Vector Engine", "Realtime PNG luminaire renderer", "#132e23"),
        ("Protected config.json", "Private API key & room locations", "#1a202c"),
        ("REST Proxy & Dispatcher", "Safe non-blocking JSON routing", "#1a202c")
    ]
    y = 175
    for title, sub, fill in items2:
        c.draw_rounded_rect(391, y, 258, 52, rx=10, fill=fill, stroke="#2d3748", stroke_width=1.0)
        c.draw_text(title, 405, y + 22, size=11, color="#f1f5f9")
        c.draw_text(sub, 405, y + 38, size=9, color="#94a3b8")
        y += 62

    # Column 3: Cloud & Device
    c.draw_rounded_rect(710, 105, 290, 455, rx=18, fill="#0f1117", stroke="#1f2430", stroke_width=1.5)
    c.draw_text("HARDWARE & CLOUD", 730, 138, size=13, color="#fbbf24")
    c.draw_text("Govee IoT OpenAPI Infrastructure", 730, 156, size=10, color="#64748b")

    items3 = [
        ("Govee Developer Cloud", "OpenAPI v1 REST Endpoints", "#1a202c"),
        ("Device Discovery API", "Multi-lamp enumeration & MACs", "#1a202c"),
        ("Realtime State Query", "Online, power, RGB, Kelvin status", "#1a202c"),
        ("Smart Ceiling Light (H60A1)", "Physical hardware luminaire", "#2e2413"),
        ("13 Addressable Segments", "Center dome & 12 perimeter zones", "#1a202c"),
        ("Wi-Fi & BLE Dual Stack", "Low-latency cloud execution", "#1a202c")
    ]
    y = 175
    for title, sub, fill in items3:
        c.draw_rounded_rect(726, y, 258, 52, rx=10, fill=fill, stroke="#2d3748", stroke_width=1.0)
        c.draw_text(title, 740, y + 22, size=11, color="#f1f5f9")
        c.draw_text(sub, 740, y + 38, size=9, color="#94a3b8")
        y += 62

    # Inter-tier connectors
    c.draw_line(330, 310, 375, 310, stroke="#38bdf8", stroke_width=2.0)
    c.draw_circle(352, 310, 4, fill="#38bdf8")

    c.draw_line(665, 310, 710, 310, stroke="#34d399", stroke_width=2.0)
    c.draw_circle(687, 310, 4, fill="#34d399")

    img = c.to_pillow()
    img.save(output_path, format="PNG")
    print(f"Architecture graphic saved to: {output_path}")

if __name__ == "__main__":
    generate_structure_graphic()
