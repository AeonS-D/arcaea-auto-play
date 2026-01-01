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
        title="选择AFF谱面文件",
        filetypes=[("谱面文件", "*.aff")]
    )
    root.destroy()
    return file_path

def extract_delay_from_aff(input_path):
    """遍历整个谱面，找到最早的音符时间作为延迟"""
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
        print(f"配置加载失败: {e}")
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
    
    print("\n当前配置：")
    print(f"谱面路径：{chart_path}")
    print(f"微调延迟：{config_params.get('fine_tune_step', 10)}毫秒")
    
    has_designant_in_chart = check_designant_in_chart(chart_path)
    
    if has_designant_in_chart:
        print("\n[蚂蚁异象检测]")
        print("当前谱面包含蚂蚁异象(designant)特有note")
        
        if 'designant_choice' in config_params:
            designant_choice = config_params['designant_choice']
            print(f"  *蚂蚁异象触控：{'执行触控' if designant_choice else '不执行触控'}")
            print("若要切换蚂蚁异象触控，请在参数编辑中选择[4]切换是否触控蚂蚁异象")
        else:
            print("蚂蚁异象触控：尚未配置")
            print("首次游玩时将自动询问，或可在参数编辑中选择[4]配置")
    else:
        pass

def quick_edit_params(current_config):
    chart_path = current_config["global"].get("chart_path", "")
    has_designant_in_chart = check_designant_in_chart(chart_path)
    
    print("\n参数快捷编辑：")
    print("[1] 编辑坐标")
    print("[2] 谱面路径")
    print("[3] 微调设置")
    
    if has_designant_in_chart:
        print("[4] 配置是否触控蚂蚁异象")
    
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
            has_designant_in_chart = check_designant_in_chart(new_path)
            if has_designant_in_chart:
                print("检测到新谱面包含蚂蚁异象(designant)特有note")
        else:
            print("未选择文件，保持原值")
    elif key == '3':
        print("\n当前微调延迟：{}毫秒".format(current_config["global"].get("fine_tune_step", 10)))
        try:
            flush_input()
            new_step = input("请输入新的微调延迟（毫秒，整数）：").strip()
            if new_step:
                new_step_int = int(new_step)
                if new_step_int > 0:
                    current_config["global"]["fine_tune_step"] = new_step_int
                    save_config(current_config)
                    print(f"微调延迟已更新为：{new_step_int}毫秒")
                else:
                    print("延迟必须为正整数，更新失败。")
            else:
                print("未输入，保持原值。")
        except ValueError:
            print("输入无效，必须为整数。")
    elif key == '4' and has_designant_in_chart:
        config_params = current_config["global"]
        
        if 'designant_choice' in config_params:
            current_choice = config_params['designant_choice']
            new_choice = not current_choice
            config_params['designant_choice'] = new_choice
            status = "开启" if new_choice else "关闭"
            print(f"蚂蚁异像触控已切换为：{status}")
            
            if new_choice:
                print("  * 提示：已启用蚂蚁异象模式，将处理特殊的蚂蚁异象note")
            else:
                print("  * 提示：已禁用蚂蚁异象模式，将忽略所有蚂蚁异象note")
        else:
            print("\n检测到谱面包含蚂蚁异象（designant）特有的note")
            print("您是否在游玩蚂蚁异象？")
            print("  y - 是，启用蚂蚁异象模式（处理所有note）")
            print("  n - 否，禁用蚂蚁异象模式（忽略蚂蚁异象note）")
            
            flush_input()
            user_input = input("请选择 (y/n): ").strip().lower()
            designant_choice = (user_input == 'y')
            config_params['designant_choice'] = designant_choice
            
            if designant_choice:
                print("已启用蚂蚁异象模式")
            else:
                print("已禁用蚂蚁异象模式，将忽略所有蚂蚁异象note")
        
        save_config(current_config)
        
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

def incremented(current_config):
    global time_offset
    step_ms = current_config["global"].get("fine_tune_step", 10)
    step_seconds = step_ms / 1000.0
    with time_lock:
        time_offset += step_seconds
    print(f"[微调] 提前{step_ms}毫秒，当前偏移: {time_offset:.3f}秒")

def decremented(current_config):
    global time_offset
    step_ms = current_config["global"].get("fine_tune_step", 10)
    step_seconds = step_ms / 1000.0
    with time_lock:
        time_offset -= step_seconds
    print(f"[微调] 延后{step_ms}毫秒，当前偏移: {time_offset:.3f}秒")

def reset_time_offset():
    global time_offset
    with time_lock:
        time_offset = 0.0
    print(f"[微调] 偏移已重置: {time_offset:.3f}秒")

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
            print(f"\n已调整延迟为: {delay}秒")
        else:
            print("错误：未找到任何有效的音符时间，无法确定延迟！")
            print("请检查谱面文件是否包含有效音符")
            return
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"文件处理失败: {e}")
        return
    except Exception as e:
        print(f"谱面加载失败: {e}")
        return

    time_offset = 0.0
    
    print("\n" + "="*40)
    print(f"当前基础延迟: {base_delay}s")
    print(f"当前微调延迟: {current_config['global'].get('fine_tune_step', 10)}毫秒")
    
    print("微调控制:")
    print(f"  输入 + 然后回车: 提前{current_config['global'].get('fine_tune_step', 10)}毫秒")
    print(f"  输入 - 然后回车: 延后{current_config['global'].get('fine_tune_step', 10)}毫秒") 
    print("  输入 0 然后回车: 重置微调偏移")
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
        print("\n[错误] 未生成任何触控事件")
        print("可能的原因：")
        print("1. 谱面文件为空或格式错误")
        print("2. 坐标配置不正确")
        print("3. 谱面中没有任何可播放的note")
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
    start_input_listener(current_config)
    
    designant_choice = current_config["global"].get("designant_choice")
    
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
    print("Arcaea自动打歌脚本 v3.1.0") 
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