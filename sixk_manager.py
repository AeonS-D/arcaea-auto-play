import re
from typing import List, Tuple, Dict
from chart import TimingGroup, Arc, Tap, Hold

class SixKModeManager:
    def __init__(self):
        self.camera_intervals = []  # [(start_time, end_time), ...] - 用于Arc
        self.lanes_intervals = []   # [(start_time, end_time), ...] - 用于地面Note
        
    def analyze_chart_for_6k(self, chart_content: str):
        camera_pattern = r'scenecontrol\((\d+),enwidencamera,([\d\.]+),(\d)\);'
        camera_matches = list(re.finditer(camera_pattern, chart_content))
        lanes_pattern = r'scenecontrol\((\d+),enwidenlanes,([\d\.]+),(\d)\);'
        lanes_matches = list(re.finditer(lanes_pattern, chart_content))
        self.camera_intervals = self._process_events(camera_matches)
        self.lanes_intervals = self._process_events(lanes_matches)
        
        return self.camera_intervals, self.lanes_intervals
    
    def _process_events(self, matches):
        intervals = []
        
        matches.sort(key=lambda m: int(m.group(1)))
        
        start_events = [m for m in matches if m.group(3) == '1']
        end_events = [m for m in matches if m.group(3) == '0']
        
        # 配对开始和结束事件
        for i, start in enumerate(start_events):
            if i < len(end_events):
                end = end_events[i]
                start_time = int(start.group(1)) + int(float(start.group(2)))
                end_time = int(end.group(1)) + int(float(end.group(2)))
                intervals.append((start_time, end_time))
        
        return intervals
    
    def get_mode_for_arc(self, time_ms: int) -> str:
        for start, end in self.camera_intervals:
            if start <= time_ms <= end:
                return '6k'
        return '4k'
    
    def get_mode_for_ground_note(self, time_ms: int) -> str:
        for start, end in self.lanes_intervals:
            if start <= time_ms <= end:
                return '6k'
        return '4k'
    
    def split_chart_by_note_type(self, chart):
        """根据音符类型和模式拆分谱面"""
        if not self.camera_intervals and not self.lanes_intervals:
            return {
                'arcs_4k': self._filter_notes_by_type(chart, ['Arc']),
                'taps_4k': self._filter_notes_by_type(chart, ['Tap']),
                'holds_4k': self._filter_notes_by_type(chart, ['Hold'])
            }
        
        arcs_4k = []
        arcs_6k = []
        taps_4k = []
        taps_6k = []
        holds_4k = []
        holds_6k = []
        
        def process_notes(notes_list):
         # 检查各部分是否在6k时间段内
            for note in notes_list:
                if isinstance(note, TimingGroup):
                    process_notes(note.notes)
                elif isinstance(note, Arc):
                    if self._is_note_in_intervals(note, self.camera_intervals):
                        arcs_6k.append(note)
                    else:
                        arcs_4k.append(note)
                elif isinstance(note, Tap):
                    if self._is_note_in_intervals(note, self.lanes_intervals):
                        taps_6k.append(note)
                    else:
                        taps_4k.append(note)
                elif isinstance(note, Hold):
                    if self._is_note_in_intervals(note, self.lanes_intervals):
                        holds_6k.append(note)
                    else:
                        holds_4k.append(note)
        
        process_notes(chart.notes)
        
        return {
            'arcs_4k': arcs_4k,
            'arcs_6k': arcs_6k,
            'taps_4k': taps_4k,
            'taps_6k': taps_6k,
            'holds_4k': holds_4k,
            'holds_6k': holds_6k
        }
    
    def _is_note_in_intervals(self, note, intervals):
        for start, end in intervals:
            if self._is_note_in_range(note, start, end):
                return True
        return False
    
    def _is_note_in_range(self, note, start_time, end_time):
        if isinstance(note, Arc):
            return (start_time <= note.start <= end_time or 
                    start_time <= note.end <= end_time or
                    (note.start <= start_time and note.end >= end_time))
        elif isinstance(note, Tap):
            return start_time <= note.tick <= end_time
        elif isinstance(note, Hold):
            return (start_time <= note.start <= end_time or 
                    start_time <= note.end <= end_time or
                    (note.start <= start_time and note.end >= end_time))
        return False
    
    def _filter_notes_by_type(self, chart, note_types):
        filtered_notes = []
        
        def process_notes(notes_list):
            for note in notes_list:
                if isinstance(note, TimingGroup):
                    process_notes(note.notes)
                elif note.__class__.__name__ in note_types:
                    filtered_notes.append(note)
        
        process_notes(chart.notes)
        return filtered_notes