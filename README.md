# 🤖 WALLY

> _"AUTO... WALLY"_ - But this time, he's got GPS, LiDAR, and face recognition! 🚀

## 📖 Overview

Meet WALLY! This isn't your average trash-compacting robot (from the WALL-E movie). Our WALLY is a sophisticated mobile robot that combines GPS waypoint navigation, obstacle avoidance using LiDAR and computer vision, plus a face recognition security system that would make any sci-fi movie proud.

Originally designed as an autonomous delivery robot, WALLY's modular architecture makes it perfect for repurposing into various applications - from security patrol bots to enviromental data collection and research platforms. Built on a Jetson Nano brain 🧠 with Arduino Mega muscles 💪, this robot can navigate complex environments while keeping unauthorized users at bay. It's like having a personal bodyguard that also happens to be great at not bumping into things!

## 📁 Project Structure

```
WALLY/
├── 🔧 arduino/                 # The robot's nervous system
│   ├── both.h                  # Shared functions header
│   ├── motor.h                 # Motor control magic
│   └── Robot.ino              # Main Arduino sketch
├── 🔐 authentication/          # "Papers, please!" module
│   ├── log_files/             # Access attempt records
│   ├── operations/            # Authentication operations
│   ├── main.py               # Auth system controller
│   └── requirements.txt      # Auth dependencies
├── 🎛️ devices/                # Hardware interface layer
│   ├── camera.py             # Eyes of the robot
│   ├── compass.py            # Digital compass
│   ├── gps.py                # GPS navigator
│   ├── lidar.py              # 360° obstacle scanner
│   └── ultrasonic.py         # Backup proximity sensor
├── 🧭 navigation/             # The brain's GPS
│   ├── ftg.py                # Follow-The-Gap algorithm
│   ├── hybrid.py             # Navigation mashup
│   ├── main_navigation.py    # Enhanced nav system
│   ├── nav_video_w_cp.py     # Navigation with video
│   ├── navigation_vision.py  # Vision-based navigation
│   ├── vision.py             # Computer vision utils
│   └── waypoint.py           # Point-to-point navigation
├── 🎮 simulation/             # Virtual testing ground
│   ├── nav_demo.py           # Navigation demo
│   └── utils.py              # Simulation utilities
├── 🧪 test_applications/      # Testing playground
│   ├── client.py             # Client application
│   ├── gps.py                # GPS testing
│   └── server.py             # Server for remote control
├── 🎯 main.py                 # Mission control center
├── 📋 requirements.txt        # Python dependencies
├── 📄 LICENSE                 # Legal stuff
└── 📖 README.md              # You are here!
```

## 🛠️ Hardware Arsenal

Our WALLY is equipped with some serious tech:

| Component                | Purpose                            | Status                |
| ------------------------ | ---------------------------------- | --------------------- |
| 🖥️ **Jetson Nano**       | AI brain for navigation & vision   | ✅ Primary compute    |
| 🔌 **Arduino Mega**      | Motor control & sensor interface   | ✅ Motor controller   |
| ⚡ **Polulu Motors**     | Movement and power                 | ✅ Locomotion         |
| 🧭 **Digital Compass**   | Heading information                | ✅ Navigation         |
| 📡 **GPS Module**        | Location tracking                  | ✅ Positioning        |
| 🔋 **20Ah 12V Battery**  | Power supply                       | ✅ Energy source      |
| 📡 **RPLidar A1**        | 360° obstacle detection            | ✅ Obstacle avoidance |
| 📷 **Logitech Webcam**   | Computer vision & face recognition | ✅ Vision system      |
| 📏 **Ultrasonic Sensor** | Backup proximity detection         | 🔄 Optional           |

_tip: Make sure the wires are connected properly! The motor controlers are really fragile; be careful with it!_

## 🚀 Quick Start

### Prerequisites

- Python 3.7+ (because we're not living in the stone age)
- OpenCV (for those sweet computer vision features)
- A sense of adventure! 🎭

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/abtonmoy/Wally.git
   cd WALLY
   ```

2. **Install dependencies:**

   ```bash
   pip3 install -r requirements.txt
   ```

   _Pro tip: Use a virtual environment to avoid dependency conflicts!_

3. **Hardware Setup:**

   - Connect Arduino Mega to Jetson Nano via USB
   - Wire up sensors according to your hardware configuration
   - Connect the 20Ah battery (carefully! ⚡)
   - Double-check serial port settings

4. **Launch Mission Control:**
   ```bash
   python3 main.py
   ```

## 🎮 Features & Capabilities

### 🗺️ Navigation System

- **GPS Waypoint Following**: Give WALLY coordinates, watch him go!
- **Follow-The-Gap Algorithm**: Smoothly navigates around obstacles
- **Hybrid Navigation**: Best of both worlds - GPS accuracy with obstacle intelligence

### 🔒 Security System

- **Face Recognition**: Uses OpenCV's LBPHFaceRecognizer
- **User Management**: Add, remove, and manage authorized users
- **Access Logging**: Keeps track of who's been visiting
- **Admin Controls**: Because someone needs to be in charge

### 🎯 Smart Features

- **Real-time Obstacle Detection**: LiDAR-powered awareness
- **Computer Vision**: Object detection and tracking
- **Data Management**: Automatic logging and data storage
- **Remote Control**: Client-server architecture for remote operation (you can use it as a RC car if you want)

## 🎪 Usage

Run `main.py` for the navigation and run `authentication/main.py` for face recognition. You can configure both funtionalities according to your usecases.

## 🔧 Core Algorithms

### Follow-The-Gap (FTG)

Our implementation of the Follow-The-Gap algorithm is the heart of WALLY's obstacle avoidance system. Here's how it works:

- **360° LiDAR Scanning**: The RPLidar A1 continuously scans the environment, providing distance measurements at 1-degree intervals
- **Gap Detection**: The algorithm processes these measurements to identify "gaps" (spaces between obstacles) that are wide enough for the robot to pass through
- **Safety Margins**: Each gap is evaluated with safety buffers to ensure WALLY doesn't get too close to obstacles
- **Dynamic Target Selection**: The largest viable gap closest to the desired heading is selected as the navigation target
- **Smooth Steering**: Instead of sharp turns, the algorithm provides smooth steering commands to avoid jerky movements

Think of it as the robot's way of saying "I'll find a way through!" - but with mathematical precision and safety built-in.

### Hybrid Navigation

This is where the magic happens! Our hybrid system seamlessly blends two powerful navigation approaches:

**GPS Waypoint Layer:**

- Uses GPS coordinates to maintain overall direction and mission objectives
- Calculates bearing and distance to target waypoints
- Provides high-level path planning for long-distance navigation

**Local Obstacle Avoidance Layer:**

- FTG algorithm handles immediate obstacle detection and avoidance
- Real-time decision making for dynamic environments
- Maintains forward progress while avoiding collisions

**Smart Arbitration:**

- When obstacles are detected, the system temporarily prioritizes local avoidance
- Once clear, it smoothly transitions back to GPS waypoint following
- Continuous recalculation ensures optimal path selection

It's like having a GPS that actually knows there's construction ahead - and automatically finds the best detour!

### Face Recognition System

Our security system uses a sophisticated multi-stage approach:

**Face Detection Pipeline:**

- **Haar Cascade Classifiers**: Initial face detection in real-time video streams
- **Region of Interest (ROI) Extraction**: Isolates face regions for processing
- **Preprocessing**: Converts to grayscale, normalizes lighting, and applies histogram equalization

**Training Process:**

- **Multiple Sample Capture**: Collects 30+ images per user in various lighting conditions
- **Data Augmentation**: Applies slight rotations and brightness adjustments to improve robustness
- **LBPH Training**: Uses Local Binary Pattern Histograms for feature extraction and model training

**Recognition Engine:**

- **Real-time Processing**: Processes video at 15+ FPS for responsive authentication
- **Confidence Scoring**: Each recognition includes a confidence score (lower = better match)
- **Adaptive Thresholding**: Adjusts sensitivity based on environmental conditions
- **Multi-frame Verification**: Requires consistent recognition across multiple frames to prevent false positives

**Security Features:**

- **Local Storage**: All face data stays on the device - no cloud uploads
- **Encryption**: Face templates are stored in encrypted format
- **Access Logging**: Every authentication attempt is logged with timestamps
- **Admin Controls**: Separate admin users can manage the system

The system is designed to be both secure and user-friendly, with privacy as a core principle!

## 🐛 Troubleshooting

**Serial Connection Issues?**

- Check your Arduino connection
- Verify the serial port in `main.py`
- Try unplugging and reconnecting (the classic IT solution)

**Camera Not Working?**

- Ensure the webcam is connected
- Check OpenCV installation
- Try `lsusb` to see if the system detects it

**Face Recognition Acting Up?**

- Capture more face samples in different lighting
- Clean the camera lens
- Make sure you're not wearing a mask (unless that's intentional!)

**Navigation Problems?**

- Check GPS signal strength (go outside!)
- Calibrate the compass
- Verify LiDAR is spinning and detecting obstacles

## 👥 About Us

This project was born from a summer of caffeine, determination, and a shared love of robotics! 🌟

**🔬 Research and Project Supervisor:**

- **Dr. Qixin Deng** - dengq@wabash.edu

**🎯 Team Members:**

- **Abdul Basit Tonmoy** - [@yabtonmoy](https://github.com/abtonmoy)
- **Gregory Powers** - [@amoldybuffalo](https://github.com/amoldybuffalo)

**🏆 Summer 2025 Achievements:**

- ✅ Created the whole platform from ground up
- ✅ Successfully implemented hybrid navigation system
- ✅ Built robust face recognition security system
- ✅ Created seamless Jetson Nano + Arduino integration
- ✅ Developed comprehensive testing frameworks
- ✅ Achieved autonomous navigation in complex environments
- ✅ Learned that debugging hardware is 90% checking connections
- ✅ Discovered that robots are basically very expensive pets

**💡 What We Learned:**
Before this internship, none of us had any kind of prior experience in robotics. This project pushed us deep into robotics, computer vision, and embedded systems. We went from "How do you make a robot move?" to "How do you make a robot navigate autonomously while recognizing faces?" It's been an incredible journey of problem-solving, long debugging sessions, and celebrating small victories!

## 🔮 Future Enhancements

- 🗺️ **Advanced Path Planning**: Implement A\* or RRT algorithms
- 🔗 **Sensor Fusion**: Combine multiple sensors for better accuracy
- 📱 **Mobile App**: Control WALLY from your phone
- 🌐 **Web Interface**: Browser-based control panel
- 🎵 **Voice Commands**: "WALLY, go to the kitchen!"
- 🤖 **Machine Learning**: Better obstacle prediction
- 🔋 **Battery Monitoring**: Smart power management

## 🎨 Contributing

Found a bug? Have a cool feature idea? We'd love to hear from you!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

_Made with ❤️, lots of ☕, and a healthy dose of 🤖 by the WALLY team_

**"Sometimes you just have to take a leap of faith. The trust part comes later."** - _Not actually a WALLY quote, but it applies to robotics!_
