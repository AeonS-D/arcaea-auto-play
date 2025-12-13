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
        title="选择AFF谱面文件",
        filetypes=[("谱面文件", "*.aff")]
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
        print(f"配置加载失败: {e}")
        base_delay = DEFAULT_CONFIG["delay"]
        return DEFAULT_CONFIG

def save_config(current_config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(current_config, f, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else x)

def show_config(current_config):
    config_params = current_config["global"]
    print("\n当前配置：")
    print(f"播放延迟：{base_delay}s")
    print(f"谱面路径：{config_params['chart_path']}")

def input_coord(prompt, default):
    while True:
        try:
            flush_input()
            print(prompt + f"（当前 {default}）：", end="", flush=True)
            raw = input().strip()
            if not raw:
                return default
            x, y = map(int, raw.replace("，", ",").split(","))
            return x, y
        except (ValueError, IndexError):
            print("格式错误！按回车使用当前值或重新输入")

def quick_edit_params(current_config):
    global base_delay
    
    print("\n参数快捷编辑：")
    print("[1] 编辑坐标")
    print("[2] 谱面路径")
    print("[3] 基础延迟")
    print("按对应数字键编辑，其他键跳过...")

    key = wait_key(5)
    
    if key == '1':
        print("\n请按顺序设置四个坐标（按回车保持当前值）")
        current_config["global"]["bottom_left"] = input_coord("底部轨道左坐标 (x,y)", current_config["global"]["bottom_left"])
        current_config["global"]["top_left"] = input_coord("天空线左坐标 (x,y)", current_config["global"]["top_left"])
        current_config["global"]["top_right"] = input_coord("天空线右坐标 (x,y)", current_config["global"]["top_right"])
        current_config["global"]["bottom_right"] = input_coord("底部轨道右坐标 (x,y)", current_config["global"]["bottom_right"])
        save_config(current_config)
        print("坐标已更新！")
    elif key == '2':
        new_path = choose_aff_file()
        if new_path:
            current_config["global"]["chart_path"] = new_path
            save_config(current_config)
            print(f"谱面路径已更新为：{new_path}")
        else:
            print("未选择文件，保持原值")
    elif key == '3':
        try:
            flush_input()
            print(f"当前基础延迟：{base_delay}s")
            print("请输入新的延迟值（秒）：", end="", flush=True)
            raw = input().strip()
            if raw:
                new_delay = float(raw)
                current_config["delay"] = new_delay
                base_delay = new_delay
                save_config(current_config)
                print(f"延迟已更新为：{new_delay}s")
        except ValueError:
            print("输入无效，保持原值")

def incremented():
    global time_offset
    with time_lock:
        time_offset += 0.01 #此处修改延迟值，单位ms
    print(f"[微调] 提前0.01秒，当前偏移: {time_offset:.3f}秒")

def decremented():
    global time_offset
    with time_lock:
        time_offset -= 0.01 #此处修改延迟值，单位ms
    print(f"[微调] 延后0.01秒，当前偏移: {time_offset:.3f}秒")

def reset_time_offset():
    global time_offset
    with time_lock:
        time_offset = 0.0
    print(f"[微调] 偏移已重置: {time_offset:.3f}秒")

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
                    print(f"[提示] 未知命令: {user_input}，可用命令: + (提前), - (延后), 0 (重置)")
            except EOFError:
                break
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                print(f"[输入监听错误] {e}")
                break
    
    listener_thread = threading.Thread(target=input_listener, daemon=True)
    listener_thread.start()
    return listener_thread

def run_automation_with_6k(current_config):
    global base_delay, time_offset, input_listener_active, automation_started

    chart_path = current_config["global"]["chart_path"]
    
    if not chart_path:
        print("错误：未设置谱面路径！")
        print("请在参数编辑中选择谱面文件")
        return
    
    try:
        with open(chart_path, 'r', encoding='utf-8') as f:
            chart_content = f.read()
        
        sixk_manager = SixKModeManager()
        camera_intervals, lanes_intervals = sixk_manager.analyze_chart_for_6k(chart_content)
        
        delay = extract_delay_from_aff(chart_path)
        if delay is not None:
            current_config['delay'] = delay
            print(f"已根据AFF文件调整延迟为: {delay}秒")
        else:
            print("警告：未找到有效的初始延迟，使用配置中的值")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"文件处理失败: {e}")
        return

    base_delay = current_config["delay"]
    time_offset = 0.0
    
    print("\n" + "="*40)
    print(f"当前基础延迟: {base_delay}s")
    
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
    
    print("微调控制:")
    print("  输入 + 然后回车: 提前0.01秒")
    print("  输入 - 然后回车: 延后0.01秒") 
    print("  输入 0 然后回车: 重置微调偏移")
    print("="*40)
    show_config(current_config)
    
    try:
        chart = Chart.loads(chart_content)
    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"谱面加载失败: {e}")
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
            
            # 创建子谱面
            segment_chart = Chart(notes, chart.options)
            
            if mode == '6k':
                # 使用6k解算
                segment_events = solve_6k(segment_chart, conv)
            else:
                # 使用4k解算
                segment_events = solve_4k(segment_chart, conv)
            
            # 合并事件
            for time_ms, events in segment_events.items():
                if time_ms not in all_events:
                    all_events[time_ms] = []
                all_events[time_ms].extend(events)
    else:
        all_events = solve_4k(chart, conv)
    
    if not all_events:
        print("\n[错误] 未生成任何触控事件")
        print("可能的原因：")
        print("1. 谱面文件为空或格式错误")
        print("2. 坐标配置不正确")
        print("3. 谱面中没有任何可播放的音符")
        return
    
    sorted_ans = sorted(all_events.items())
    
    ans_iter = iter(sorted_ans)
    
    try:
        ms, evs = next(ans_iter)
    except StopIteration:
        print("[警告] 事件序列意外终止")
        return

    ctl = DeviceController(server_dir='.')
    
    input_listener_active = True
    start_input_listener()
    
    print("\n准备就绪，按两次回车键以开始...")
    flush_input()
    input()
    
    automation_started = True
    
    start_time = time.time() + base_delay
    print('[INFO] 自动打歌启动')
    print('[INFO] 微调功能已启用，可在下方输入命令进行微调')
    
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
        print('[INFO] 自动打歌结束')
    except (KeyboardInterrupt, SystemExit):
        print('[INFO] 用户中断执行')
    except Exception as e:
        print(f'[ERROR] 执行出错: {e}')
    finally:
        input_listener_active = False
        automation_started = False

def main():
    main_config = load_config()

    print("="*40)
    print("Arcaea自动打歌脚本 v3.0.0") 
    print("="*40)
    
    if "chart_path" not in main_config["global"] or not main_config["global"]["chart_path"]:
        print("首次使用或未配置谱面路径，请选择谱面文件")
        chart_path = choose_aff_file()
        if chart_path:
            main_config["global"]["chart_path"] = chart_path
            save_config(main_config)
            print(f"已设置谱面路径: {chart_path}")
        else:
            print("未选择文件，程序退出")
            return

    quick_edit_params(main_config)

    run_automation_with_6k(main_config)

    print("\n执行完毕，3秒后自动退出...")
    time.sleep(3)

if __name__ == '__main__':
    main()