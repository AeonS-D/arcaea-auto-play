import json
import time
import msvcrt
import threading
import re
from pathlib import Path
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from chart import Chart
from solve import solve, CoordConv
from control import DeviceController

CONFIG_FILE = "auto_arcaea_config.json"
DEFAULT_CONFIG = {
    "global": {
        "bottom_left": (171, 1350),
        "top_left": (171, 300),
        "top_right": (2376, 300),
        "bottom_right": (2376, 1350),
        "chart_path": "chart.txt"
    },
    "delay": 2.0
}

time_offset = 0.0
base_delay = 0.0
time_lock = threading.Lock()

def choose_aff_file():
    root = Tk()
    root.withdraw()
    file_path = askopenfilename(
        title="select aff file",
        filetypes=[("Beatmap files", "*.aff")]
    )
    root.destroy()
    return file_path

def extract_delay_from_aff(input_path):

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    delay = None

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('(') and stripped_line.endswith(');'):
            parts = stripped_line[1:-2].split(',')
            if parts:
                try:
                    time_ms = int(parts[0])
                    delay = -time_ms / 1000
                    break
                except (ValueError, IndexError):
                    pass
        elif stripped_line.startswith('arc(') and stripped_line.endswith(');'):
            arc_content = stripped_line[4:-2]
            parts = [p.strip() for p in arc_content.split(',')]
            
            if len(parts) >= 10:
                skyline_boolean = parts[-1].lower() == 'true'
                
                if not skyline_boolean:
                    try:
                        time_ms = int(parts[0])
                        delay = -time_ms / 1000
                        break
                    except (ValueError, IndexError):
                        pass
                else:
                    arctap_match = re.search(r'\[arctap\((\d+)\)\]', stripped_line)
                    if arctap_match:
                        try:
                            time_ms = int(arctap_match.group(1))
                            delay = -time_ms / 1000
                            break
                        except ValueError:
                            pass
        elif 'arctap(' in stripped_line:
            arctap_match = re.search(r'arctap\((\d+)\)', stripped_line)
            if arctap_match:
                try:
                    time_ms = int(arctap_match.group(1))
                    delay = -time_ms / 1000
                    break
                except ValueError:
                    pass
      
    return delay

def flush_input():
    while msvcrt.kbhit():
        msvcrt.getch()

def wait_key(timeout):
    start = time.time()
    while time.time() - start < timeout:
        if msvcrt.kbhit():
            return msvcrt.getch().decode()
    return None

def load_config():
    global base_delay
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Handle legacy config
            if "mode1" in config:
                config["delay"] = config["mode1"]["delay"]
                del config["mode1"]
                if "mode2" in config:
                    del config["mode2"]
                if "current_mode" in config:
                    del config["current_mode"]
                save_config(config)
            base_delay = config["delay"]
            return config
    except FileNotFoundError:
        base_delay = DEFAULT_CONFIG["delay"]
        return DEFAULT_CONFIG
    except Exception as e:
        print(f"Failed to load config: {e}")
        base_delay = DEFAULT_CONFIG["delay"]
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else x)

def show_config(config):
    params = config["global"]
    print("\nCurrent Config:")
    print(f"Base Delay: {base_delay}s")
    print(f"Bottom Track: {params['bottom_left']} → {params['bottom_right']}")
    print(f"Sky Line: {params['top_left']} → {params['top_right']}")
    print(f"Chart Path: {params['chart_path']}")

def input_coord(prompt, default):
    while True:
        try:
            flush_input()
            print(prompt + f"（current {default}）：", end="", flush=True)
            raw = input().strip()
            if not raw:
                return default
            x, y = map(int, raw.replace("，", ",").split(","))
            return (x, y)
        except:
            print("Format error! Press Enter to use current value or re-enter")

def quick_edit_params(config):
    global base_delay
    params = {**config["global"]}
    
    print("\nQuick Parameter Edit:")
    print("[1] Edit Coordinates")
    print("[2] Base Delay")
    print("[3] Chart Path")
    print("Press the corresponding number key to edit, other keys to skip...")

    key = wait_key(5)
    
    if key == '1':
        print("\nPlease set the four coordinates in order (press Enter to keep current value)")
        config["global"]["bottom_left"] = input_coord("Bottom Track Left (x,y)", config["global"]["bottom_left"])
        config["global"]["top_left"] = input_coord("Sky Line Left (x,y)", config["global"]["top_left"])
        config["global"]["top_right"] = input_coord("Sky Line Right (x,y)", config["global"]["top_right"])
        config["global"]["bottom_right"] = input_coord("Bottom Track Right (x,y)", config["global"]["bottom_right"])
        save_config(config)
        print("Coordinates updated!")
    elif key == '2':
        new_delay = input(f"Base Delay (current {base_delay}): ")
        if new_delay:
            try:
                config['delay'] = float(new_delay)
                base_delay = float(new_delay)
                save_config(config)
            except ValueError:
                print("Invalid input, keeping original value")
    elif key == '3':
        new_path = choose_aff_file()
        if new_path:
            config["global"]["chart_path"] = new_path
            save_config(config)
            print(f"Chart path updated to: {new_path}")
        else:
            print("No file selected, keeping original value")

def run_automation(config):
    global base_delay

    chart_path = config["global"]["chart_path"]
    try:
        delay = extract_delay_from_aff(chart_path)
        if delay is not None:
            config['delay'] = delay
            print(f"Delay adjusted based on AFF file: {delay}s")
        else:
            print("Warning: No valid initial delay found, using config value")
    except Exception as e:
        print(f"Failed to process file: {e}")
        return

    base_delay = config["delay"]
    
    print("\n" + "="*40)
    print(f"current delay: {base_delay}s")
    print("="*40)
    show_config(config)
    
    try:
        chart = Chart.loads(Path(chart_path).read_text())
    except Exception as e:
        print(f"Failed to load chart: {e}")
        return

    conv = CoordConv(config["global"]["bottom_left"], 
                   config["global"]["top_left"],
                   config["global"]["top_right"],
                   config["global"]["bottom_right"])
    
    ans = solve(chart, conv)
    ans_iter = iter(sorted(ans.items()))
    ms, evs = next(ans_iter)

    ctl = DeviceController(server_dir='.')
    
    print("\nReady, press Enter twice to start...")
    flush_input()
    msvcrt.getch()

    start_time = time.time() + base_delay
    print('[INFO] Auto play started')
    
    try:
        while True:
            now = (time.time() - start_time) * 1000
            if now >= ms:  
                for ev in evs:
                    ctl.touch(*ev.pos, ev.action, ev.pointer)
                ms, evs = next(ans_iter)
    except StopIteration:
        print('[INFO] Auto play finished')
    except Exception as e:
        print(f'[ERROR] Execution error: {e}')

if __name__ == '__main__':
    config = load_config()

    print("="*40)
    print("Arcaea Auto Play Script v2.2.1") 
    print("="*40)

    quick_edit_params(config)

    run_automation(config)

    print("\nExecution completed, exiting in 3 seconds...")
    time.sleep(3)
