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
    "mode1": {"delay": 2.0},
    "mode2": {"delay": 3.0, "retry_button": (600, 600)},
    "current_mode": 1
}

time_offset = 0.0
base_delay = 0.0
time_lock = threading.Lock()

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
            parts = arc_content.split(',')
            if parts:
                try:
                    time_ms = int(parts[0])
                    delay = -time_ms / 1000
                    break
                except (ValueError, IndexError):
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
            if "retry_button" in config.get("mode1", {}):
                del config["mode1"]["retry_button"]
                save_config(config)
            base_delay = config[f"mode{config['current_mode']}"]["delay"]
            return config
    except FileNotFoundError:
        base_delay = DEFAULT_CONFIG[f"mode{DEFAULT_CONFIG['current_mode']}"]["delay"]
        return DEFAULT_CONFIG
    except Exception as e:
        print(f"配置加载失败: {e}")
        base_delay = DEFAULT_CONFIG[f"mode{DEFAULT_CONFIG['current_mode']}"]["delay"]
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else x)

def show_config(config):
    params = config["global"]
    print("\n当前配置：")
    print(f"模式：模式{config['current_mode']}")
    print(f"基础延迟：{base_delay}s")
    print(f"底部轨道：{params['bottom_left']} → {params['bottom_right']}")
    print(f"空线：{params['top_left']} → {params['top_right']}")
    print(f"谱面路径：{params['chart_path']}")

def input_coord(prompt, default):
    while True:
        try:
            flush_input()
            print(prompt + f"（当前 {default}）：", end="", flush=True)
            raw = input().strip()
            if not raw:
                return default
            x, y = map(int, raw.replace("，", ",").split(","))
            return (x, y)
        except:
            print("格式错误！按回车使用当前值或重新输入")

def quick_edit_params(config):
    """快捷参数编辑"""
    global base_delay
    params = {**config["global"], **config[f"mode{config['current_mode']}"]}
    
    print("\n参数快捷编辑：")
    print("[1] 编辑坐标")
    print("[2] 基础延迟")
    print("[3] 谱面路径")
    if config['current_mode'] == 2:
        print("[4] 重试按钮坐标")
    print("按对应数字键编辑，其他键跳过...")

    key = wait_key(5)
    
    if key == '1':
        print("\n请按顺序设置四个坐标（按回车保持当前值）")
        config["global"]["bottom_left"] = input_coord("底部轨道左坐标 (x,y)", config["global"]["bottom_left"])
        config["global"]["top_left"] = input_coord("天空线左坐标 (x,y)", config["global"]["top_left"])
        config["global"]["top_right"] = input_coord("天空线右坐标 (x,y)", config["global"]["top_right"])
        config["global"]["bottom_right"] = input_coord("底部轨道右坐标 (x,y)", config["global"]["bottom_right"])
        save_config(config)
        print("坐标已更新！")
    elif key == '2':
        new_delay = input(f"基础延迟（当前 {base_delay}）：")
        if new_delay:
            try:
                config[f"mode{config['current_mode']}"]['delay'] = float(new_delay)
                base_delay = float(new_delay)
                save_config(config)
            except ValueError:
                print("输入无效，保持原值")
    elif key == '3':
        new_path = choose_aff_file()
        if new_path:
            config["global"]["chart_path"] = new_path
            save_config(config)
            print(f"谱面路径已更新为：{new_path}")
        else:
            print("未选择文件，保持原值")
    elif key == '4' and config['current_mode'] == 2:
        config["mode2"]["retry_button"] = input_coord("重试按钮坐标 (x,y)", config["mode2"]["retry_button"])
        save_config(config)
        print("重试按钮坐标已更新！")

def run_automation(config):
    global base_delay

    chart_path = config["global"]["chart_path"]
    try:
        delay = extract_delay_from_aff(chart_path)
        if delay is not None:
            config['mode1']['delay'] = delay
            print(f"已根据AFF文件调整mode1延迟为: {delay}秒")
        else:
            print("警告：未找到有效的初始延迟，使用配置中的值")
    except Exception as e:
        print(f"文件处理失败: {e}")
        return

    base_delay = config[f"mode{config['current_mode']}"]["delay"]
    
    print("\n" + "="*40)
    print(f"当前基础延迟: {base_delay}s")
    print("="*40)
    show_config(config)
    
    try:
        chart = Chart.loads(Path(chart_path).read_text())
    except Exception as e:
        print(f"谱面加载失败: {e}")
        return

    conv = CoordConv(config["global"]["bottom_left"], 
                   config["global"]["top_left"],
                   config["global"]["top_right"],
                   config["global"]["bottom_right"])
    
    ans = solve(chart, conv)
    ans_iter = iter(sorted(ans.items()))
    ms, evs = next(ans_iter)

    ctl = DeviceController(server_dir='.')
    
    if config['current_mode'] == 2:
        ctl.tap(*config["mode2"]["retry_button"])
    
    if config['current_mode'] == 1:
        print("\n[模式1] 准备就绪，按两次回车键以开始...")
        flush_input()
        msvcrt.getch()

    start_time = time.time() + base_delay
    print('[INFO] 自动打歌启动')
    
    try:
        while True:
            now = (time.time() - start_time) * 1000
            if now >= ms:  
                for ev in evs:
                    ctl.touch(*ev.pos, ev.action, ev.pointer)
                ms, evs = next(ans_iter)
    except StopIteration:
        print('[INFO] 自动打歌结束')
    except Exception as e:
        print(f'[ERROR] 执行出错: {e}')

if __name__ == '__main__':
    config = load_config()

    print("="*40)
    print("Arcaea自动打歌脚本 v2.0") 
    print("="*40)

    print(f"\n当前模式：模式{config['current_mode']}")
    print("[1] 切换模式1")
    print("[2] 切换模式2")
    print("3秒内按数字键切换，其他键跳过...")
    
    key = wait_key(3)
    if key in ('1', '2'):
        new_mode = int(key)
        config["current_mode"] = new_mode
        save_config(config)
        base_delay = config[f"mode{new_mode}"]["delay"]
        print(f"\n已切换到模式{new_mode}！")

    quick_edit_params(config)

    run_automation(config)

    print("\n执行完毕，3秒后自动退出...")
    time.sleep(3)
