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
from sixk_manager import SixKModeManager

CONFIG_FILE = "auto_arcaea_config.json"
DEFAULT_CONFIG = {
    "global": {
        "bottom_left": (171, 1350),
        "top_left": (171, 300),
        "top_right": (2376, 300),
        "bottom_right": (2376, 1350),
        "chart_path": ""
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
            loaded_config = json.load(f)
            if "mode1" in loaded_config:
                loaded_config["delay"] = loaded_config["mode1"]["delay"]
                del loaded_config["mode1"]
                if "current_mode" in loaded_config:
                    del loaded_config["current_mode"]
                save_config(loaded_config)
            base_delay = loaded_config["delay"]
            return loaded_config
    except FileNotFoundError:
        base_delay = DEFAULT_CONFIG["delay"]
        return DEFAULT_CONFIG
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Failed to load config: {e}")
        base_delay = DEFAULT_CONFIG["delay"]
        return DEFAULT_CONFIG

def save_config(current_config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(current_config, f, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else x)

def show_config(current_config):
    config_params = current_config["global"]
    print("\nCurrent Config:")
    print(f"Base Delay: {base_delay}s")
    print(f"Chart Path: {config_params['chart_path']}")

def input_coord(prompt, default):
    while True:
        try:
            flush_input()
            print(prompt + f" (current {default}): ", end="", flush=True)
            raw = input().strip()
            if not raw:
                return default
            x, y = map(int, raw.replace("，", ",").split(","))
            return x, y
        except (ValueError, IndexError):
            print("Format error! Press Enter to use current value or re-enter")

def quick_edit_params(current_config):
    global base_delay
    
    print("\nQuick Parameter Edit:")
    print("[1] Edit Coordinates")
    print("[2] Chart Path")
    print("[3] Base Delay")
    print("Press the corresponding number key to edit, other keys to skip...")

    key = wait_key(5)
    
    if key == '1':
        print("\nPlease set the four coordinates in order (press Enter to keep current value)")
        current_config["global"]["bottom_left"] = input_coord("Bottom Track Left (x,y)", current_config["global"]["bottom_left"])
        current_config["global"]["top_left"] = input_coord("Sky Line Left (x,y)", current_config["global"]["top_left"])
        current_config["global"]["top_right"] = input_coord("Sky Line Right (x,y)", current_config["global"]["top_right"])
        current_config["global"]["bottom_right"] = input_coord("Bottom Track Right (x,y)", current_config["global"]["bottom_right"])
        save_config(current_config)
        print("Coordinates updated!")
    elif key == '2':
        new_path = choose_aff_file()
        if new_path:
            current_config["global"]["chart_path"] = new_path
            save_config(current_config)
            print(f"Chart path updated to: {new_path}")
        else:
            print("No file selected, keeping original value")
    elif key == '3':
        try:
            flush_input()
            print(f"Current base delay: {base_delay}s")
            print("Enter new delay value (seconds): ", end="", flush=True)
            raw = input().strip()
            if raw:
                new_delay = float(raw)
                current_config["delay"] = new_delay
                base_delay = new_delay
                save_config(current_config)
                print(f"Delay updated to: {new_delay}s")
        except ValueError:
            print("Invalid input, keeping original value")

def incremented():
    global time_offset
    with time_lock:
        time_offset += 0.01 # Modify delay value here, unit: ms
    print(f"[Fine-tune] Advance 0.01s, current offset: {time_offset:.3f}s")

def decremented():
    global time_offset
    with time_lock:
        time_offset -= 0.01 # Modify delay value here, unit: ms
    print(f"[Fine-tune] Delay 0.01s, current offset: {time_offset:.3f}s")

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
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                print(f"[Input listener error] {e}")
                break
    
    listener_thread = threading.Thread(target=input_listener, daemon=True)
    listener_thread.start()
    return listener_thread

def run_automation_with_6k(current_config):
    global base_delay, time_offset, input_listener_active, automation_started

    chart_path = current_config["global"]["chart_path"]
    
    if not chart_path:
        print("Error: No chart path set!")
        print("Please select chart file in parameter edit")
        return
    
    try:
        with open(chart_path, 'r', encoding='utf-8') as f:
            chart_content = f.read()
        
        sixk_manager = SixKModeManager()
        camera_intervals, lanes_intervals = sixk_manager.analyze_chart_for_6k(chart_content)
        
        delay = extract_delay_from_aff(chart_path)
        if delay is not None:
            current_config['delay'] = delay
            print(f"Delay adjusted based on AFF file: {delay}s")
        else:
            print("Warning: No valid initial delay found, using config value")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"File processing failed: {e}")
        return

    base_delay = current_config["delay"]
    time_offset = 0.0
    
    print("\n" + "="*40)
    print(f"Current base delay: {base_delay}s")
    
    if camera_intervals or lanes_intervals:
        if camera_intervals:
            for i, (start, end) in enumerate(camera_intervals):
                start_sec = start / 1000
                end_sec = end / 1000
        
        if lanes_intervals:
            for i, (start, end) in enumerate(lanes_intervals):
                start_sec = start / 1000
                end_sec = end / 1000
    else:
        print("")
    
    print("Fine-tuning control:")
    print("  Enter + then Enter: Advance 0.01s")
    print("  Enter - then Enter: Delay 0.01s") 
    print("  Enter 0 then Enter: Reset fine-tuning offset")
    print("="*40)
    show_config(current_config)
    
    try:
        chart = Chart.loads(chart_content)
    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"Failed to load chart: {e}")
        return

    conv = CoordConv(current_config["global"]["bottom_left"], 
                   current_config["global"]["top_left"],
                   current_config["global"]["top_right"],
                   current_config["global"]["bottom_right"])
    
    from sixk_solve import solve as solve_6k
    from solve import solve as solve_4k
    
    all_events = {}
    
    if camera_intervals or lanes_intervals:
        note_groups = sixk_manager.split_chart_by_note_type(chart)
        
        for group_name, notes in note_groups.items():
            if not notes:
                continue
                
            mode = '6k' if '6k' in group_name else '4k'
            note_type = group_name.split('_')[0]
            
            # Create sub-chart
            segment_chart = Chart(notes, chart.options)
            
            if mode == '6k':
                # Use 6k solving
                segment_events = solve_6k(segment_chart, conv)
            else:
                # Use 4k solving
                segment_events = solve_4k(segment_chart, conv)
            
            # Merge events
            for time_ms, events in segment_events.items():
                if time_ms not in all_events:
                    all_events[time_ms] = []
                all_events[time_ms].extend(events)
    else:
        all_events = solve_4k(chart, conv)
    
    if not all_events:
        print("\n[Error] No touch events generated")
        print("Possible reasons:")
        print("1. Chart file is empty or format error")
        print("2. Coordinate configuration incorrect")
        print("3. No playable notes in chart")
        return
    
    sorted_ans = sorted(all_events.items())
    
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
    except (KeyboardInterrupt, SystemExit):
        print('[INFO] User interrupted execution')
    except Exception as e:
        print(f'[ERROR] Execution error: {e}')
    finally:
        input_listener_active = False
        automation_started = False

def main():
    main_config = load_config()

    print("="*40)
    print("Arcaea Auto Play Script v3.0.0") 
    print("="*40)
    
    if "chart_path" not in main_config["global"] or not main_config["global"]["chart_path"]:
        print("First use or chart path not configured, please select chart file")
        chart_path = choose_aff_file()
        if chart_path:
            main_config["global"]["chart_path"] = chart_path
            save_config(main_config)
            print(f"Chart path set to: {chart_path}")
        else:
            print("No file selected, exiting program")
            return

    quick_edit_params(main_config)

    run_automation_with_6k(main_config)

    print("\nExecution completed, exiting in 3 seconds...")
    time.sleep(3)

if __name__ == '__main__':
    main()