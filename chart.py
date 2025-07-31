from typing import Any, Union, List, Optional

from easing import Easing


class ArcTap:
    tick: int

    def __init__(self, tick: int):
        self.tick = tick

    def __str__(self):
        return f'arctap(tick={self.tick})'


class Arc:  # 虹弧Arc & 天空Note
    start: int
    end: int
    start_x: float
    end_x: float
    easing: Easing
    start_y: float
    end_y: float
    color: int
    trace_arc: bool
    taps: list[ArcTap]

    def __init__(
        self,
        start: int,
        end: int,
        start_x: float,
        end_x: float,
        easing: Easing,
        start_y: float,
        end_y: float,
        color: int,
        _,
        trace_arc: Union[bool, str],
    ):
        self.start = start
        self.end = end
        self.start_x = start_x
        self.end_x = end_x
        self.easing = easing
        self.start_y = start_y
        self.end_y = end_y
        self.color = color
        
        if trace_arc == "designant":
            self.trace_arc = True
        else:
            self.trace_arc = bool(trace_arc)
        
        self.taps = []

    def __getitem__(self, taps):
        if isinstance(taps, tuple):
            self.taps = list(taps)
        else:
            self.taps = [taps]
        return self

    def __str__(self):
        return f'arc(({self.start_x:.02f}, {self.start_y:.02f})@{self.start} -> ({self.end_x:.02f}, {self.end_y:.02f})@{self.end} using {self.easing}, color={self.color}, trace_arc={self.trace_arc}){self.taps}'


class Tap:  # 地键Tap
    tick: int
    track: int

    def __init__(self, tick: int, track: int):
        self.tick = tick
        self.track = track

    def __str__(self):
        return f'tap(tick={self.tick}, track={self.track})'


class Hold:  # 地面Hold
    start: int
    end: int
    track: int

    def __init__(self, start: int, end: int, track: int):
        self.start = start
        self.end = end
        self.track = track

    def __str__(self):
        return f'hold(start={self.start}, end={self.end}, track={self.track})'


class Timing:
    tick: int
    bpm: float
    beats_per_measure: float

    def __init__(self, tick: int, bpm: float, beats_per_measure: float):
        self.tick = tick
        self.bpm = bpm
        self.beats_per_measure = beats_per_measure

    def __str__(self):
        return f'timing(tick={self.tick}, bpm={self.bpm}, beats_per_measure={self.beats_per_measure})'


class TimingGroup:
    properties: dict[str, Any]
    notes: List[Union['TimingGroup', 'Timing', 'Tap', 'Hold', 'Arc']]

    def __init__(self, properties: dict[str, Any], notes: List[Union['TimingGroup', 'Timing', 'Tap', 'Hold', 'Arc']]):
        self.properties = properties
        self.notes = notes

    def __str__(self):
        return f'timinggroup({self.properties}, notes={self.notes})'


class Chart:
    notes: List[Union[Timing, Tap, Hold, Arc, TimingGroup]]
    options: dict[str, Any] | None

    def __init__(self, notes: List[Union[Timing, Tap, Hold, Arc, TimingGroup]], options: dict[str, Any] | None = None):
        self.notes = notes
        self.options = options

    @classmethod
    def loads(cls, content: str) -> 'Chart':
        lines = content.splitlines()
        options = {}
        notes = []
        line_iter = iter(lines)
        lcls = {
            'true': True,
            'false': False,
            'none': None,
            'arc': Arc,
            'tap': Tap,
            'arctap': ArcTap,
            'hold': Hold,
            'timing': Timing,
            'timinggroup': TimingGroup,
            's': Easing.Linear,
            'b': Easing.CubicBezier,
            'so': Easing.So,
            'si': Easing.Si,
            'soso': Easing.SoSo,
            'sisi': Easing.SiSi,
            'sosi': Easing.SoSi,
            'siso': Easing.SiSo,
        }

        for line in line_iter:
            if ':' in line:
                key, value = line.split(':', 1)
                options[key.strip()] = value.strip()
            else:
                break

        stack = []
        current_notes = notes
        current_properties = None

        for line in line_iter:
            line = line.strip()
            if not line or line.startswith('//'):
                continue  

            if line.startswith('timinggroup'):
                attr_start = line.find('(')
                attr_end = line.rfind(')')
                if attr_start == -1 or attr_end == -1:
                    continue
                properties_str = line[attr_start + 1:attr_end]
                
                properties = {}
                for item in properties_str.split('_'):
                    item = item.strip()
                    if not item:
                        continue
                    if item.startswith('anglex'):
                        try:
                            angle_value = int(item[5:])
                            properties['anglex'] = angle_value
                        except ValueError:
                            properties[item] = True
                    elif item.startswith('angley'):
                        try:
                            angle_value = int(item[5:])
                            properties['angley'] = angle_value
                        except ValueError:
                            properties[item] = True
                    else:
                        properties[item] = True
                for item in properties_str.split(','):
                    item = item.strip()
                    if not item:
                        continue
                    if '=' in item:
                        key, value = item.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if value.lower() == 'true':
                            properties[key] = True
                        elif value.lower() == 'false':
                            properties[key] = False
                        elif value.lower() == 'none':
                            properties[key] = None
                        elif value.isdigit():
                            properties[key] = int(value)
                        elif '.' in value and all(part.isdigit() for part in value.split('.')):
                            properties[key] = float(value)
                        else:
                            properties[key] = value
                    else:
                        properties['type'] = item
                
                stack.append((current_notes, current_properties))
                group = TimingGroup(properties, [])
                current_notes.append(group)
                current_notes = group.notes
                current_properties = properties
                
                if '{' in line[attr_end + 1:]:
                    continue 
            elif line.startswith('};'):
                if stack:
                    current_notes, current_properties = stack.pop()
            else:
                if line.endswith(';'):
                    line = line[:-1] 
                import re
                line = re.sub(r'(?<=[\(, ])(\b(?!true|false|none|\d+\.?\d*|s|b|so|si|soso|sisi)\w+\b)(?=[,\) ])', r'"\1"', line)
                try:
                    note = eval(line, {}, lcls)
                    if isinstance(note, tuple):
                        note = Tap(*note)
                    current_notes.append(note)
                except Exception as e:
                    print(f"Error parsing line: {line}\n{str(e)}")

        return Chart(notes, options)