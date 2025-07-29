# ARCAEA Autoplay Project - Major Update for arcaea-sap

Extracts `.aff` chart files directly from Arcaea installation packages.

## Disclaimer:

This project is intended for educational and research purposes only. The project team bears no responsibility for disputes arising from malicious usage.

---

## Project Modifications:

1. **Added support for `timinggroup()` in chart files**  
   Implemented by creating temporary chart files and using regex to remove `timinggroup()` and whitespace (simple but effective).

2. **Dual Operation Modes**  
   - `Mode1`: Manual simulation start - triggers touch simulation when notes approach judgment line.  
     *Do not manually adjust delay; script auto-calibrates. Ideal for score climbing.*  
   - `Mode2`: Auto simulation start - triggers after tapping "Retry" in pause menu with configurable delay.  
     *Network/device variability may affect consistency. Delay adjustable in config.*

3. **Memory Function**  
   Coordinates are now preserved between sessions.  
   **⚠️ Do NOT delete config files - may cause crashes (intentionally unpatched).**

4. **Parameter Customization**  
   All settings can be modified via configuration file.

5. **"Spaghetti Code" Warning**  
   Contains experimental/unoptimized implementations.

---

## Requirements & Setup

1. **Python 3.11 Recommended**  
   Compatible with 3.11 only (tested; fails on 3.13+).

2. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt

3. **scrcpy-server Setup**
Download from scrcpy releases and place in root directory.

4. **ADB Configuration**
Install Android Debug Bridge and configure environment variables.

5. **Device Presets**
Config defaults to Xiaomi Pad 5 parameters (theoretically compatible with 11" tablets).

6. **Touch Coordinates Reference**
https://github.com/user-attachments/assets/b1c6e676-9016-4349-a4bf-f14583dae300
Original author notes: "Uncertain if this remains accurate - open issues if problematic."

## Planned Features
Dynamic delay compensation during touch simulation (theoretical)

GUI implementation (exploratory)
