# ARCAEA Auto-Play Project (Major Update for arcaea-sap)

Extract `.aff` files from Arcaea installation packages.

## Disclaimer  

**This project is for educational purposes only. The developer bears no responsibility for disputes arising from malicious use.**

---

## Project Modifications  

+ 1. **Added `timinggroup()` Support**  
   *(Implemented via temporary chart file creation with regex removal of `timinggroup()` constructs)*  

+ 2. **Added Two Operation Modes**  
     - **Mode 1**: Manual Simulation  
       - Triggers touch simulation at note spawn  
       - **Do not adjust delay** - auto-calibrated for step chart climbing  
     - **Mode 2**: Automatic Simulation  
       - Activates after "Retry" + configurable delay  
       *(Less reliable for climbing due to device/network variance)*  

+ 3. **Configuration Memory**  
   - Persistent coordinate storage (requires `config.ini`)  
   - ⚠️ **Warning**: Deleting config file causes crashes (won't fix)  

+ 4. **Parameter Customization**  
   - Modify via runtime arguments or `config.ini`  

+ 5. **Spaghetti Code Warning**  
   - Contains intentionally unoptimized code (pls no bully 😅)  

---

## Critical Notes  

+ 1. **Python 3.11 Required**  
   - Confirmed incompatible with 3.13+  

+ 2. **Dependencies**:  
   ```bash
   pip install -r requirements.txt
