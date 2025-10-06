import json
import time
import msvcrt
import threading
import re
import sys
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
    },
    "delay": 2.0
}

time_offset = 0.0
base_delay = 0.0
time_lock = threading.Lock()
input_listener_active = False
automation_started = False

def choose_aff_file():
    root = Tk()
    root.withdraw()
    file_path = askopenfilename(
        title="Select AFF Chart File",
        filetypes=[("Chart files", "*.aff")]
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
        
        if stripped_line.startswith('hold(') and stripped_line.endswith(');'):
            parts = stripped_line[5:-2].split(',')
            if parts:
                try:
                    time_ms = int(parts[0])
                    delay = -time_ms / 1000
                    break
                except (ValueError, IndexError):
                    pass
        
        elif stripped_line.startswith('(') and stripped_line.endswith(');'):
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
            key = msvcrt.getch().decode()
            flush_input()
            return key
    return None

def load_config():
    global base_delay
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "mode1" in config:
                config["delay"] = config["mode1"]["delay"]
                del config["mode1"]
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
            print(prompt + f" (current {default}): ", end="", flush=True)
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
    print("[2] Chart Path")
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
        new_path = choose_aff_file()
        if new_path:
            config["global"]["chart_path"] = new_path
            save_config(config)
            print(f"Chart path updated to: {new_path}")
        else:
            print("No file selected, keeping original value")

def incremented():
    global time_offset
    with time_lock:
        time_offset += 0.05
    print(f"[Fine-tune] Advance 0.05s, current offset: {time_offset:.3f}s")

def decremented():
    global time_offset
    with time_lock:
        time_offset -= 0.05
    print(f"[Fine-tune] Delay 0.05s, current offset: {time_offset:.3f}s")

def reset_time_offset():
    global time_offset
    with time_lock:
        time_offset = 0.0
    print(f"[Fine-tune] Offset reset: {time_offset:.3f}s")

def start_input_listener():
    def input_listener():
        global input_listener_active, automation_started
        while input_listener_active:
            try:
                if not automation_started:
                    time.sleep(0.1)
                    continue
                    
                user_input = input().strip().lower()
                
                if user_input == '+':
                    incremented()
                elif user_input == '-':
                    decremented()
                elif user_input == '0':
                    reset_time_offset()
                else:
                    print(f"[Hint] Unknown command: {user_input}, available commands: + (advance), - (delay), 0 (reset)")
            except EOFError:
                break
            except Exception as e:
                print(f"[Input listener error] {e}")
                break
    
    listener_thread = threading.Thread(target=input_listener, daemon=True)
    listener_thread.start()
    return listener_thread

def run_automation(config):
    global base_delay, time_offset, input_listener_active, automation_started

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
    time_offset = 0.0
    
    print("\n" + "="*40)
    print(f"Current base delay: {base_delay}s")
    print("Fine-tuning control:")
    print("  Enter + then Enter: Advance 0.05s")
    print("  Enter - then Enter: Delay 0.05s") 
    print("  Enter 0 then Enter: Reset fine-tuning offset")
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
    sorted_ans = sorted(ans.items())
    if not sorted_ans:
        print("\n[Error] No touch events generated, please check:")
        print(f"- Chart path: {config['global']['chart_path']}")
        print(f"- Delay compensation: {base_delay}s")
        return
    ans_iter = iter(sorted_ans)
    try:
        ms, evs = next(ans_iter)
    except StopIteration:
        print("[Warning] Event sequence terminated unexpectedly")
        return

    ctl = DeviceController(server_dir='.')
    
    input_listener_active = True
    start_input_listener()
    
    print("\nReady, press Enter twice to start...")
    flush_input()
    input()
    
    automation_started = True
    
    start_time = time.time() + base_delay
    print('[INFO] Auto play started')
    print('[INFO] Fine-tuning enabled, enter commands below to adjust')
    
    try:
        while input_listener_active:
            with time_lock:
                current_offset = time_offset
                
            now = (time.time() - start_time + current_offset) * 1000
            
            if now >= ms:  
                for ev in evs:
                    ctl.touch(*ev.pos, ev.action, ev.pointer)
                try:
                    ms, evs = next(ans_iter)
                except StopIteration:
                    break
            else:
                time.sleep(0.001)
                
    except StopIteration:
        print('[INFO] Auto play finished')
    except Exception as e:
        print(f'[ERROR] Execution error: {e}')
    finally:
        input_listener_active = False
        automation_started = False

if __name__ == '__main__':
    config = load_config()

    print("="*40)
    print("Arcaea Auto Play Script v2.3") 
    print("="*40)

    quick_edit_params(config)

    run_automation(config)

    print("\nExecution completed, exiting in 3 seconds...")
    time.sleep(3)
