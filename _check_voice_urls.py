"""Check which piper voice URLs are valid at v1.0.0 tag."""
import urllib.request
import urllib.error

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

CANDIDATES = [
    # Missing voices — check multiple path variants
    f"{BASE}/en/en_IN/medium/en_IN-female-medium.onnx",
    f"{BASE}/en/en_US/amy/medium/en_US-amy-medium.onnx",
    f"{BASE}/en/en_US/joe/medium/en_US-joe-medium.onnx",
    f"{BASE}/en/en_US/arctic/medium/en_US-arctic-medium.onnx",
    f"{BASE}/hi/hi_IN/hemant/medium/hi_IN-hemant-medium.onnx",
    f"{BASE}/hi/hi_IN/hemant/medium/hi_IN-hemant-medium.onnx",
    # Already working (verify tag works)
    f"{BASE}/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
    f"{BASE}/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
    f"{BASE}/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
]

print("Checking voice URLs (v1.0.0 tag):")
for url in CANDIDATES:
    name = url.split("/")[-1]
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=10)
        cl = resp.headers.get("Content-Length", "?")
        mb = round(int(cl) / 1024 / 1024, 1) if cl != "?" else "?"
        print(f"  OK  ({mb} MB) {name}")
    except urllib.error.HTTPError as e:
        print(f"  {e.code}       {name}")
    except Exception as e:
        print(f"  ERR  {name}  -- {e}")
