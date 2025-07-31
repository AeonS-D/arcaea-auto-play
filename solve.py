import numpy as np
import math

from chart import Chart, Arc, Tap, Hold, TimingGroup
from algo.algo_base import TouchAction, TouchEvent


class CoordConv:
    trans_mat: np.ndarray

    def __init__(
        self, dl: tuple[float, float], ul: tuple[float, float], ur: tuple[float, float], dr: tuple[float, float]
    ):
        x0, y0 = dl
        x1, y1 = ul
        x2, y2 = ur
        x3, y3 = dr
        a, b, c = x3 - x2, x1 - x2, x1 + x3 - x0 - x2
        d, e, f = y3 - y2, y1 - y2, y1 + y3 - y0 - y2

        g = b * d - a * e
        h = (a * f - c * d) / g
        g = (c * e - b * f) / g

        c, f = x0, y0
        a = (g + 1) * x3 - c
        b = (h + 1) * x1 - c
        d = (g + 1) * y3 - f
        e = (h + 1) * y1 - f

        self.trans_mat = np.array(((a, b, c), (d, e, f), (g, h, 1))).T

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        x_, y_, z_ = np.array((x, y, 1)) @ self.trans_mat
        return x_ / z_, y_ / z_


def solve(chart: Chart, converter: CoordConv) -> dict[int, list[TouchEvent]]:
    result = {}

    def ins(ms: int, ev: TouchEvent):
        if ms not in result:
            result[ms] = []
        result[ms].append(ev)

    current_arctap_id = 1000

    arc_search_range = 20 

    prev_arcs = {}

    def process_note(note, group_properties=None):
        nonlocal current_arctap_id
        group_properties = group_properties or {}
        
        if group_properties.get('noinput', False):
            return
            
        def rotate_point(x, y, anglex, angley):
            ax = math.radians(anglex / 10)
            ay = math.radians(angley / 10)
            
            x_trans = x
            y_trans = y
            
            y_rot = y_trans * math.cos(ax) - 1 * math.sin(ax)
            z_rot = y_trans * math.sin(ax) + 1 * math.cos(ax)
            
            x_rot = x_trans * math.cos(ay) + z_rot * math.sin(ay)
            
            return x_rot, y_rot
        
        if isinstance(note, Arc):
            anglex = group_properties.get('anglex', 0)
            angley = group_properties.get('angley', 0)
            
            start_x, start_y = rotate_point(note.start_x, note.start_y, anglex, angley)
            end_x, end_y = rotate_point(note.end_x, note.end_y, anglex, angley)
            
            start = (start_x, start_y, 1)
            end = (end_x, end_y, 1)
            delta = note.end - note.start
            pointer_id = note.color + 5
            
            connect_prev = False
            if pointer_id in prev_arcs:
                prev_arc = prev_arcs[pointer_id]
                time_gap = note.start - prev_arc['end']
                
                if time_gap < 50 and distance_of(
                    (prev_arc['end_x'], prev_arc['end_y']),
                    (note.start_x, note.start_y)
                ) < 100:
                    connect_prev = True
                    for t in range(prev_arc['end'] - arc_search_range, prev_arc['end'] + arc_search_range + 1):
                        if t in result:
                            for idx, ev in enumerate(result[t]):
                                if ev.pointer == pointer_id and ev.action == TouchAction.UP:
                                    result[t].pop(idx)
                                    break
            
            if note.trace_arc:
                for tap in note.taps:
                    t = (tap.tick - note.start) / delta
                    px, py, _ = note.easing.value(start, end, t)
                    px, py = converter(px, py)
                    ins(tap.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, current_arctap_id))
                    ins(tap.tick + 2, TouchEvent((round(px), round(py)), TouchAction.UP, current_arctap_id))
                    current_arctap_id += 1
                    if current_arctap_id > 2000:
                        current_arctap_id = 1000
            else:
                if not connect_prev:
                    px, py, _ = note.easing.value(start, end, 0)
                    px, py = converter(px, py)
                    ins(note.start, TouchEvent((round(px), round(py)), TouchAction.DOWN, pointer_id))
                
                min_step = 10 
                max_step = 30 
                step_size = max(min_step, min(max_step, delta // 50))
                
                for tick in range(note.start + step_size, note.end, step_size):
                    t = (tick - note.start) / delta
                    px, py, _ = note.easing.value(start, end, t)
                    
                    if anglex != 0 or angley != 0:
                        px, py = rotate_point(px, py, anglex, angley)
                    
                    px, py = converter(px, py)
                    ins(tick, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))
                
                px, py, _ = note.easing.value(start, end, 1)
                px, py = converter(px, py)
                ins(note.end, TouchEvent((round(px), round(py)), TouchAction.UP, pointer_id))
                
                prev_arcs[pointer_id] = {
                    'start': note.start,
                    'end': note.end,
                    'start_x': note.start_x,
                    'end_x': note.end_x,
                    'start_y': note.start_y,
                    'end_y': note.end_y
                }
        elif isinstance(note, Tap):
            px, py = converter(-0.75 + note.track * 0.5, 0)
            ins(note.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, note.track))
            ins(note.tick + 20, TouchEvent((round(px), round(py)), TouchAction.UP, note.track))
        elif isinstance(note, Hold):
            px, py = converter(-0.75 + note.track * 0.5, 0)
            ins(note.start, TouchEvent((round(px), round(py)), TouchAction.DOWN, note.track))
            
            if group_properties.get('fadingholds', False):
                duration = note.end - note.start
                for t in range(note.start + 50, note.end, 50):
                    alpha = 1.0 - (t - note.start) / duration
                    fade_pointer = note.track + 100
                    ins(t, TouchEvent((round(px), round(py)), TouchAction.MOVE, fade_pointer, alpha))
            
            ins(note.end, TouchEvent((round(px), round(py)), TouchAction.UP, note.track))

    def process_timing_group(group):
        group_properties = group.properties
        for note in group.notes:
            if isinstance(note, TimingGroup):
                process_timing_group(note)
            else:
                process_note(note, group_properties)

    for note in chart.notes:
        if isinstance(note, TimingGroup):
            process_timing_group(note)
        else:
            process_note(note)
    
    return result


def distance_of(pos1, pos2):
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5


if __name__ == '__main__':
    conv = CoordConv((760, 920), (650, 340), (1690, 340), (1580, 920))
    print(conv(0, 0))
    print(conv(0.5, 0))
    print(conv(0.5, 0.5))
    print(conv(1, 1))
    print(conv(-0.5, 0))
    print(conv(1.5, 0))