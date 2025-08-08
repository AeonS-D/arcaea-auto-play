import numpy as np
import math

from chart import Chart, Arc, Tap, Hold, TimingGroup
from algo.algo_base import TouchAction

class TouchEvent:
    def __init__(self, position, action, pointer, alpha=1.0):
        self.position = position 
        self.pos = position  
        self.action = action
        self.pointer = pointer
        self.alpha = alpha


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
    arc_chains = {} 

    def ins(ms: int, ev: TouchEvent):
        if ms not in result:
            result[ms] = []
        result[ms].append(ev)

    current_arctap_id = 1000  
    arc_search_range = 20
    prev_arcs = {}       
    active_arcs = {}        
    active_holds = {}         
    used_pointers = set()   
    next_arcs = {}          

    def is_overlap_with_arc(note_tick, note_x, note_y, threshold=0.05):
  
        for pointer_id, arc_info in prev_arcs.items():
            start, end = arc_info['start'], arc_info['end']
            
            if start <= note_tick <= end and end > start:
                t = (note_tick - start) / (end - start)
                arc_x, arc_y, _ = arc_info['easing'].value(
                    (arc_info['start_x'], arc_info['start_y'], 1),
                    (arc_info['end_x'], arc_info['end_y'], 1),
                    t
                )
                
                if note_y == 0:
                    if abs(note_x - arc_x) < threshold:
                        return True, pointer_id
                elif distance_of((note_x, note_y), (arc_x, arc_y)) < threshold:
                    return True, pointer_id
        return False, None

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
        
        anglex = group_properties.get('anglex', 0)
        angley = group_properties.get('angley', 0)
        
        if isinstance(note, Arc):
            if note.start == note.end:
                return
                
            start_x, start_y = rotate_point(note.start_x, note.start_y, anglex, angley)
            end_x, end_y = rotate_point(note.end_x, note.end_y, anglex, angley)
            
            start = (start_x, start_y, 1)
            end = (end_x, end_y, 1)
            delta = note.end - note.start
            pointer_id = note.color + 5
            used_pointers.add(pointer_id) 
            
            connect_prev = False
            if pointer_id in prev_arcs:
                prev_arc = prev_arcs[pointer_id]
                time_gap = note.start - prev_arc['end']
                
                if time_gap <= 1:
                    connect_prev = True
                elif time_gap < 50 and distance_of(
                    (prev_arc['end_x'], prev_arc['end_y']),
                    (note.start_x, note.start_y)
                ) < 100:
                    connect_prev = True
                    
                if connect_prev:
                    for t in range(prev_arc['end'] - arc_search_range, prev_arc['end'] + arc_search_range + 1):
                        if t in result:
                            for idx, ev in enumerate(result[t]):
                                if ev.pointer == pointer_id and ev.action == TouchAction.UP:
                                    result[t].pop(idx)
                                    break
            
            note.easing_info = {
                'easing': note.easing,
                'start': start,
                'end': end,
                'start_x': note.start_x,
                'start_y': note.start_y,
                'end_x': note.end_x,
                'end_y': note.end_y,
                'anglex': anglex,
                'angley': angley
            }
            
            shared_taps = []
            if not note.trace_arc and note.taps:
                for tap in note.taps:
                    if tap.tick == note.start or tap.tick == note.end:
                        shared_taps.append(tap)
            
            if note.trace_arc or shared_taps:
                for tap in note.taps:
                    t = (tap.tick - note.start) / delta
                    px, py, _ = note.easing.value(start, end, t)
                    px, py = converter(px, py)
                    is_overlap = False
                    if tap.tick == note.start or tap.tick == note.end:
                        if tap in shared_taps:
                            ins(tap.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, pointer_id))
                            ins(tap.tick + 1, TouchEvent((round(px), round(py)), TouchAction.UP, pointer_id))
                            continue
                    tap_pointer = current_arctap_id
                    ins(tap.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, tap_pointer))
                    ins(tap.tick + 10, TouchEvent((round(px), round(py)), TouchAction.UP, tap_pointer))
                    current_arctap_id += 1
                    used_pointers.add(tap_pointer)
                    if current_arctap_id > 2000:
                        current_arctap_id = 1000
            else:
                if not connect_prev:
                    px, py, _ = note.easing.value(start, end, 0)
                    px, py = converter(px, py)
                    ins(note.start, TouchEvent((round(px), round(py)), TouchAction.DOWN, pointer_id))
                
                sample_points = []
                min_step = 10 
                if delta > 100:
                    steps = max(5, delta // 20)
                    for i in range(steps + 1):
                        sample_points.append(note.start + int(i * delta / steps))
                else:

                    steps = max(2, math.ceil(delta / min_step))
                    for i in range(steps + 1):
                        sample_points.append(note.start + int(i * delta / steps))
                
                for tick in sample_points:
                    t = max(0.0, min(1.0, (tick - note.start) / delta))
                    px, py, _ = note.easing.value(start, end, t)
                    
                    if anglex != 0 or angley != 0:
                        px, py = rotate_point(px, py, anglex, angley)
                    
                    px, py = converter(px, py)
                    
                    if tick != note.start:
                        ins(tick, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))
                
                has_next_arc = False
                next_arc = None
                for other_note in chart.notes:
                    if isinstance(other_note, Arc) and not other_note.trace_arc:
                        if other_note.color + 5 == pointer_id:
                            time_gap = other_note.start - note.end
                            if time_gap <= 1:
                                has_next_arc = True
                                next_arc = other_note
                                break
                
                if not has_next_arc:
                    px, py, _ = note.easing.value(start, end, 1)
                    px, py = converter(px, py)
                    ins(note.end, TouchEvent((round(px), round(py)), TouchAction.UP, pointer_id))
                    if pointer_id in active_arcs:
                        del active_arcs[pointer_id]
                    if pointer_id in next_arcs:
                        del next_arcs[pointer_id]
                else:
                    if next_arc and abs(next_arc.start - note.end) <= 1:
                        next_arcs[pointer_id] = next_arc
                        next_start_x, next_start_y = rotate_point(next_arc.start_x, next_arc.start_y, anglex, angley)
                        px, py = converter(next_start_x, next_start_y)
                    else:
                        px, py, _ = note.easing.value(start, end, 1)
                        px, py = converter(px, py)
                    
                    ins(note.end, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))
                    active_arcs[pointer_id] = (note.end, (round(px), round(py)))
                
                prev_arcs[pointer_id] = {
                    'start': note.start,
                    'end': note.end,
                    'start_x': note.start_x,
                    'end_x': note.end_x,
                    'start_y': note.start_y,
                    'end_y': note.end_y,
                    'easing': note.easing
                }
        
        elif isinstance(note, Tap):
            note_x, note_y = -0.75 + note.track * 0.5, 0
            px, py = converter(note_x, note_y)
            
            is_overlap, arc_pointer = is_overlap_with_arc(note.tick, note_x, note_y)
            
            if is_overlap and arc_pointer is not None:
                tap_pointer = note.track + 300
                used_pointers.add(tap_pointer)
                
                ins(note.tick - 2, TouchEvent((round(px), round(py)), TouchAction.DOWN, tap_pointer))
                ins(note.tick, TouchEvent((round(px), round(py)), TouchAction.UP, tap_pointer))
                
                if arc_pointer in active_arcs:
                    last_tick, last_pos = active_arcs[arc_pointer]
                    ins(note.tick + 1, TouchEvent(last_pos, TouchAction.MOVE, arc_pointer))
            else:
                ins(note.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, note.track))
                ins(note.tick + 20, TouchEvent((round(px), round(py)), TouchAction.UP, note.track))
                used_pointers.add(note.track)
        
        elif isinstance(note, Hold):
            note_x, note_y = -0.75 + note.track * 0.5, 0
            is_overlap_start, arc_pointer_start = is_overlap_with_arc(note.start, note_x, note_y)
            is_overlap_end, arc_pointer_end = is_overlap_with_arc(note.end, note_x, note_y)
            
            px, py = converter(note_x, note_y)
            hold_pointer = note.track
            used_pointers.add(hold_pointer)

            ins(note.start, TouchEvent((round(px), round(py)), TouchAction.DOWN, hold_pointer))
            
            if group_properties.get('fadingholds', False):
                duration = note.end - note.start
                for t in range(note.start + 50, note.end, 50):
                    alpha = 1.0 - (t - note.start) / duration
                    fade_pointer = note.track + 100
                    used_pointers.add(fade_pointer) 
                    ins(t, TouchEvent((round(px), round(py)), TouchAction.MOVE, fade_pointer, alpha))
            
            ins(note.end, TouchEvent((round(px), round(py)), TouchAction.UP, hold_pointer))
            
            active_holds[note.track] = (note.start, (round(px), round(py)))

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

    max_time = max(result.keys()) if result else 0

    for pointer_id, (last_tick, last_pos) in active_arcs.items():
        ins(max_time + 50, TouchEvent(last_pos, TouchAction.UP, pointer_id))

    for track, (start_tick, last_pos) in active_holds.items():
        ins(max_time + 50, TouchEvent(last_pos, TouchAction.UP, track))
    
    for pointer_id in used_pointers:
        is_down = False
        last_pos = (0, 0)
        for t in sorted(result.keys(), reverse=True):
            for ev in result[t]:
                if ev.pointer == pointer_id:
                    if ev.action == TouchAction.DOWN or ev.action == TouchAction.MOVE:
                        is_down = True
                        last_pos = ev.position if hasattr(ev, 'position') else (0, 0)
                    break
            if is_down:
                break
        if is_down:
            ins(max_time + 100, TouchEvent(last_pos, TouchAction.UP, pointer_id))
    
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
