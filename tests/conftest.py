# tests/conftest.py
# Lightweight stubs so importing campusevents.views (via urls) doesn't require numpy/cv2.
import sys
import types

# ----- Stub numpy -----
def _np_frombuffer(data, dtype=None):
    # We only need something passable to cv2.imdecode in your code path.
    # Returning the original bytes is fine because our cv2 stub ignores it anyway.
    return data

fake_numpy = types.SimpleNamespace(
    uint8=object,          # placeholder dtype
    frombuffer=_np_frombuffer,
)

# Only register the stubs if the real modules aren't installed
sys.modules.setdefault("numpy", fake_numpy)

# ----- Stub cv2 -----
def _cv2_imdecode(arr, flag):
    # Simulate "can't decode" -> returns None, which your code handles.
    return None

class _FakeQRCodeDetector:
    def detectAndDecode(self, img):
        # Return "no QR" by default; tests that need success monkeypatch _decode_qr_from_uploaded.
        return ("", None, None)

fake_cv2 = types.SimpleNamespace(
    IMREAD_COLOR=1,
    imdecode=_cv2_imdecode,
    QRCodeDetector=_FakeQRCodeDetector,
)

sys.modules.setdefault("cv2", fake_cv2)
