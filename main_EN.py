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
        "chart_path": "",
        "fine_tune_step": 10,
    }
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
    """Traverse the entire chart to find the earliest note time as delay"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    earliest_time = None
    
    for line in lines:
        stripped_line = line.strip()
        
        if stripped_line.startswith('(') and stripped_line.endswith(');'):
            parts = stripped_line[1:-2].split(',')
            if parts:
                try:
                    time_ms = int(parts[0])
                    if earliest_time is None or time_ms < earliest_time:
                        earliest_time = time_ms
                except (ValueError, IndexError):
                    pass
        
        elif stripped_line.startswith('hold(') and stripped_line.endswith(');'):
            parts = stripped_line[5:-2].split(',')
            if parts:
                try:
                    time_ms = int(parts[0])
                    if earliest_time is None or time_ms < earliest_time:
                        earliest_time = time_ms
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
                        if earliest_time is None or time_ms < earliest_time:
                            earliest_time = time_ms
                    except (ValueError, IndexError):
                        pass
        
        elif 'arctap(' in stripped_line:
            arctap_match = re.search(r'arctap\((\d+)\)', stripped_line)
            if arctap_match:
                try:
                    time_ms = int(arctap_match.group(1))
                    if earliest_time is None or time_ms < earliest_time:
                        earliest_time = time_ms
                except ValueError:
                    pass
    
    if earliest_time is not None:
        delay = -earliest_time / 1000
        return delay
    else:
        return None

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
            base_delay = 0.0
            return loaded_config
    except FileNotFoundError:
        base_delay = 0.0
        return DEFAULT_CONFIG
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Failed to load config: {e}")
        base_delay = 0.0
        return DEFAULT_CONFIG

def save_config(current_config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(current_config, f, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else x)
        
def check_designant_in_chart(chart_path):
    if not chart_path or not Path(chart_path).exists():
        return False
    
    try:
        with open(chart_path, 'r', encoding='utf-8') as f:
            content = f.read()
            import re
            return bool(re.search(r'arc\([^)]*designant[^)]*\)', content))
    except:
        return False

def show_config(current_config):
    config_params = current_config["global"]
    chart_path = config_params.get("chart_path", "")
    
    print("\nCurrent Configuration:")
    print(f"Chart Path: {chart_path}")
    print(f"Fine-tune Step: {config_params.get('fine_tune_step', 10)} milliseconds")
    
    has_designant_in_chart = check_designant_in_chart(chart_path)
    
    if has_designant_in_chart:
        print("\n[Designant Phenomenon Detection]")
        print("Current chart contains notes specific to designant phenomenon")
        
        if 'designant_choice' in config_params:
            designant_choice = config_params['designant_choice']
            print(f"  *Designant Touch: {'Execute touch' if designant_choice else 'Do not execute touch'}")
            print("To toggle designant touch, select [4] in parameter edit")
        else:
            print("Designant Touch: Not configured")
            print("Will ask automatically on first play, or configure with [4] in parameter edit")
    else:
        pass

def quick_edit_params(current_config):
    chart_path = current_config["global"].get("chart_path", "")
    has_designant_in_chart = check_designant_in_chart(chart_path)
    
    print("\nQuick Parameter Edit:")
    print("[1] Edit Coordinates")
    print("[2] Chart Path")
    print("[3] Fine-tune Settings")
    
    if has_designant_in_chart:
        print("[4] Configure designant touch")
    
    print("Press corresponding number key to edit, other keys to skip...")

    key = wait_key(5)
    
    if key == '1':
        print("\nPlease set four coordinates in order (press Enter to keep current value)")
        current_config["global"]["bottom_left"] = input_coord("Bottom track left coordinate (x,y)", current_config["global"]["bottom_left"])
        current_config["global"]["top_left"] = input_coord("Skyline left coordinate (x,y)", current_config["global"]["top_left"])
        current_config["global"]["top_right"] = input_coord("Skyline right coordinate (x,y)", current_config["global"]["top_right"])
        current_config["global"]["bottom_right"] = input_coord("Bottom track right coordinate (x,y)", current_config["global"]["bottom_right"])
        save_config(current_config)
        print("Coordinates updated!")
    elif key == '2':
        new_path = choose_aff_file()
        if new_path:
            current_config["global"]["chart_path"] = new_path
            save_config(current_config)
            print(f"Chart path updated to: {new_path}")
            has_designant_in_chart = check_designant_in_chart(new_path)
            if has_designant_in_chart:
                print("Detected new chart contains notes specific to designant phenomenon")
        else:
            print("No file selected, keeping original value")
    elif key == '3':
        print("\nCurrent fine-tune step: {} milliseconds".format(current_config["global"].get("fine_tune_step", 10)))
        try:
            flush_input()
            new_step = input("Enter new fine-tune step (milliseconds, integer): ").strip()
            if new_step:
                new_step_int = int(new_step)
                if new_step_int > 0:
                    current_config["global"]["fine_tune_step"] = new_step_int
                    save_config(current_config)
                    print(f"Fine-tune step updated to: {new_step_int} milliseconds")
                else:
                    print("Step must be positive integer, update failed.")
            else:
                print("No input, keeping original value.")
        except ValueError:
            print("Invalid input, must be integer.")
    elif key == '4' and has_designant_in_chart:
        config_params = current_config["global"]
        
        if 'designant_choice' in config_params:
            current_choice = config_params['designant_choice']
            new_choice = not current_choice
            config_params['designant_choice'] = new_choice
            status = "Enabled" if new_choice else "Disabled"
            print(f"Designant touch toggled to: {status}")
            
            if new_choice:
                print("  * Note: Designant mode enabled, will process special designant notes")
            else:
                print("  * Note: Designant mode disabled, will ignore all designant notes")
        else:
            print("\nDetected chart contains notes specific to designant phenomenon")
            print("Are you playing designant?")
            print("  y - Yes, enable designant mode (process all notes)")
            print("  n - No, disable designant mode (ignore designant notes)")
            
            flush_input()
            user_input = input("Please choose (y/n): ").strip().lower()
            designant_choice = (user_input == 'y')
            config_params['designant_choice'] = designant_choice
            
            if designant_choice:
                print("Designant mode enabled")
            else:
                print("Designant mode disabled, will ignore all designant notes")
        
        save_config(current_config)
        
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

def incremented(current_config):
    global time_offset
    step_ms = current_config["global"].get("fine_tune_step", 10)
    step_seconds = step_ms / 1000.0
    with time_lock:
        time_offset += step_seconds
    print(f"[Fine-tune] Advance {step_ms} milliseconds, current offset: {time_offset:.3f} seconds")

def decremented(current_config):
    global time_offset
    step_ms = current_config["global"].get("fine_tune_step", 10)
    step_seconds = step_ms / 1000.0
    with time_lock:
        time_offset -= step_seconds
    print(f"[Fine-tune] Delay {step_ms} milliseconds, current offset: {time_offset:.3f} seconds")

def reset_time_offset():
    global time_offset
    with time_lock:
        time_offset = 0.0
    print(f"[Fine-tune] Offset reset: {time_offset:.3f} seconds")

def start_input_listener(current_config):
    def input_listener():
        global input_listener_active, automation_started
        while input_listener_active:
            try:
                if not automation_started:
                    time.sleep(0.1)
                    continue
                    
                user_input = input().strip().lower()
                
                if user_input == '+':
                    incremented(current_config)
                elif user_input == '-':
                    decremented(current_config)
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
            
        chart_content_for_regex = chart_content
        lines = chart_content.split('\n')
        filtered_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.lower().startswith('scenecontrol'):
                continue
            filtered_lines.append(line)
        chart_content_for_load = '\n'.join(filtered_lines)
        
        sixk_manager = SixKModeManager()
        chart = Chart.loads(chart_content_for_load)
        camera_intervals, lanes_intervals, max_time = sixk_manager.analyze_chart_for_6k(chart_content_for_regex, chart)
        
        delay = extract_delay_from_aff(chart_path)
        if delay is not None:
            base_delay = delay
            print(f"\nDelay adjusted to: {delay} seconds")
        else:
            print("Error: No valid note times found, cannot determine delay!")
            print("Please check if chart file contains valid notes")
            return
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"File processing failed: {e}")
        return
    except Exception as e:
        print(f"Chart loading failed: {e}")
        return

    time_offset = 0.0
    
    print("\n" + "="*40)
    print(f"Current base delay: {base_delay}s")
    print(f"Current fine-tune step: {current_config['global'].get('fine_tune_step', 10)} milliseconds")
    
    print("Fine-tuning control:")
    print(f"  Enter + then Enter: Advance {current_config['global'].get('fine_tune_step', 10)} milliseconds")
    print(f"  Enter - then Enter: Delay {current_config['global'].get('fine_tune_step', 10)} milliseconds") 
    print("  Enter 0 then Enter: Reset fine-tuning offset")
    print("="*40)
    show_config(current_config)

    conv = CoordConv(current_config["global"]["bottom_left"], 
                   current_config["global"]["top_left"],
                   current_config["global"]["top_right"],
                   current_config["global"]["bottom_right"])
    
    from sixk_solve import solve as solve_6k
    from solve import solve as solve_4k
    
    all_events = sixk_manager.split_and_solve_chart(chart, conv, solve_4k, solve_6k)
    
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
    start_input_listener(current_config)
    
    designant_choice = current_config["global"].get("designant_choice")
    
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
    print("Arcaea Auto Play Script v3.1.0") 
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