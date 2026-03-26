# 🚗 Driver Safety Monitoring System

A real-time computer vision project that observes a driver through a
webcam and identifies unsafe driving behaviour such as **drowsiness,
phone usage, and emotional stress**.

The idea behind the project is simple: instead of relying on one
indicator, the system combines several signals and produces a **single
safety score** that represents the driver's current condition. When this
score crosses certain thresholds, the system generates alerts to warn
the driver.

This type of monitoring approach is similar to what modern **ADAS
(Advanced Driver Assistance Systems)** attempt to implement in smart
vehicles.

------------------------------------------------------------------------

# 🎯 What This Project Detects

The system analyzes the driver in three different ways.

### 1. Driver Fatigue (Eye Closure)

Using facial landmarks, the system tracks the driver's eyes and
calculates the **Eye Aspect Ratio (EAR)**.\
If the eyes remain closed for too long, the driver is likely becoming
drowsy.

### 2. Phone Usage / Distraction

A YOLOv8 object detection model is used to identify when a **mobile
phone** appears in the driver's hand or near the face.

### 3. Emotional State

Facial expressions are analyzed using a pretrained model to estimate
emotions such as **stress, anger, or sadness**, which may indicate
unsafe driving conditions.

Each module contributes to the overall driver risk score.

------------------------------------------------------------------------

# 🧠 How the System Works

The program processes frames from the camera continuously and sends them
through multiple detection modules.

Camera Feed\
→ Frame Processing\
→ Eye Detector (EAR + PERCLOS)\
→ Phone Detector (YOLOv8)\
→ Emotion Detector (DeepFace)\
→ Risk Engine\
→ Alert System + Dashboard

The final output is shown on a **live dashboard** that displays the
camera feed, risk score, and warning messages.

------------------------------------------------------------------------

# 📐 Fatigue Detection Method

EAR = (\|\|p2 - p6\|\| + \|\|p3 - p5\|\|) / (2 × \|\|p1 - p4\|\|)

If this value drops below a defined threshold for multiple frames, the
system marks the driver as **drowsy**.

Another metric used is **PERCLOS**, which measures the percentage of
time the eyes stay closed within a time window.

------------------------------------------------------------------------

# 📊 Risk Score Logic

Risk Score =\
0.45 × Drowsiness\
+ 0.35 × Distraction\
+ 0.20 × Emotion

The score is smoothed using an **Exponential Moving Average (EMA)**.

------------------------------------------------------------------------

# 🚨 Alert Levels

  Risk Score   Status          System Action
  ------------ --------------- -----------------
  0 -- 30      Safe            No warning
  30 -- 55     Mild Risk       Event logged
  55 -- 75     Moderate Risk   Warning beep
  75 -- 90     High Risk       Voice alert
  90 -- 100    Critical        Repeated alerts

------------------------------------------------------------------------

# 🖥️ Dashboard

The dashboard provides:

-   Live annotated camera feed
-   Driver risk score gauge
-   Individual component scores
-   Risk timeline graph
-   Alert log

------------------------------------------------------------------------

# 📂 Project Structure

driver_safety_system/

main.py\
config.py\
annotator.py\
requirements.txt

detectors/\
eye_detector.py\
phone_detector.py\
emotion_detector.py

core/\
risk_engine.py\
alert_system.py

dashboard/\
app.py

------------------------------------------------------------------------

# ⚙️ Installation

git clone `<repo-link>`{=html}\
cd driver_safety_system

python -m venv venv

Windows:\
venv`\Scripts`{=tex}`\activate  `{=tex}

Linux / macOS:\
source venv/bin/activate

pip install -r requirements.txt

------------------------------------------------------------------------

# ▶️ Running the Project

python main.py

python main.py --camera 1

python main.py --demo video.mp4

python main.py --no-dashboard

------------------------------------------------------------------------

# 🧰 Libraries Used

OpenCV\
MediaPipe\
Ultralytics YOLOv8\
DeepFace\
SciPy\
Matplotlib\
Pillow\
pygame\
pyttsx3

------------------------------------------------------------------------

# 📜 License

MIT License
