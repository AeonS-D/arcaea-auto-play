# ARCAEA Autoplay Project - Major Update for arcaea-sap

Extracts `.aff` chart files directly from Arcaea installation packages.

## Disclaimer:

This project is intended for educational and research purposes only. The project team bears no responsibility for disputes arising from malicious usage.

---

## Project Modifications:

1. **Added support for `timinggroup()` in chart files**  
   Implemented by creating temporary chart files and using regex to remove `timinggroup()` and whitespace (simple but effective).

2. **Added real support for timinggroup in v2.0，so we don’t need 1. anyone anymore**

3. **New Modes**   Manual simulation start - triggers touch simulation when notes approach judgment line.  
     *Do not manually adjust delay; script auto-calibrates. Ideal for world mode.*  

4. **Memory Function**  
   Coordinates are now preserved between sessions.  
   **⚠️ Do NOT delete config files - may cause crashes (yeah im lazy,so i didnt want to fix it).**

5. **Parameter Customization**  
   All settings can be modified via configuration file.

6. **"Spaghetti Code" Warning**  
   Contains experimental/unoptimized implementations.

---

## Requirements & Setup

1. **Python 3.11 Recommended**  
   Compatible with 3.11 only (tested; fails on 3.13).

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
<img width="2670" height="1200" alt="image" src="https://github.com/user-attachments/assets/c8ccea6b-6c39-47b7-84a4-12fe33297645" />


## Planned Features
Dynamic delay compensation during touch simulation (theoretical)

GUI implementation (exploratory)
