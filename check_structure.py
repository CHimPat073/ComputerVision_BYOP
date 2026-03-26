"""
check_structure.py
==================
Run this from your project folder to verify everything is in place.

Usage:
    python check_structure.py
"""

import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
print(f"\nProject root: {ROOT}\n")

REQUIRED = [
    "main.py",
    "config.py",
    "annotator.py",
    "requirements.txt",
    "detectors/__init__.py",
    "detectors/eye_detector.py",
    "detectors/phone_detector.py",
    "detectors/emotion_detector.py",
    "core/__init__.py",
    "core/risk_engine.py",
    "core/alert_system.py",
    "dashboard/__init__.py",
    "dashboard/app.py",
]

all_ok = True
for rel in REQUIRED:
    full = os.path.join(ROOT, rel)
    exists = os.path.isfile(full)
    status = "✅" if exists else "❌ MISSING"
    print(f"  {status}  {rel}")
    if not exists:
        all_ok = False

print()
if all_ok:
    print("✅ All files present. Try running:  python main.py\n")
else:
    print("❌ Some files are missing — see above.")
    print("   Make sure you have the full folder structure:\n")
    print("   files/")
    print("   ├── main.py")
    print("   ├── config.py")
    print("   ├── annotator.py")
    print("   ├── detectors/")
    print("   │   ├── __init__.py")
    print("   │   ├── eye_detector.py")
    print("   │   ├── phone_detector.py")
    print("   │   └── emotion_detector.py")
    print("   ├── core/")
    print("   │   ├── __init__.py")
    print("   │   ├── risk_engine.py")
    print("   │   └── alert_system.py")
    print("   └── dashboard/")
    print("       ├── __init__.py")
    print("       └── app.py")
    print()

# Also check Python path
print(f"🐍 Python: {sys.executable}")
print(f"   Version: {sys.version.split()[0]}\n")
