import re
from typing import List, Tuple, Dict, Optional
from chart import TimingGroup, Arc, Tap, Hold, Chart

class SixKModeManager:
    def __init__(self):
        self.camera_intervals = []  # [(start_time, end_time), ...] - 用于Arc
        self.lanes_intervals = []   # [(start_time, end_time), ...] - 用于地面Note
        self.camera_events = []     # [(t, mt, event_type), ...] - 原始camera事件
        self.lanes_events = []      # [(t, mt, event_type), ...] - 原始lanes事件
        self.max_time = 0
        
    def analyze_chart_for_6k(self, chart_content: str, chart: Chart = None):
        camera_pattern = r'scenecontrol\((\d+),enwidencamera,([\d\.]+),(\d)\);'
        camera_matches = list(re.finditer(camera_pattern, chart_content))
        lanes_pattern = r'scenecontrol\((\d+),enwidenlanes,([\d\.]+),(\d)\);'
        lanes_matches = list(re.finditer(lanes_pattern, chart_content))
        
        self.camera_events = self._extract_events(camera_matches)
        self.lanes_events = self._extract_events(lanes_matches)
        
        self.camera_intervals = self._process_events(self.camera_events)
        self.lanes_intervals = self._process_events(self.lanes_events)
        
        if chart:
            self.max_time = self._get_max_time(chart)
        
        return self.camera_intervals, self.lanes_intervals, self.max_time
    
    def _extract_events(self, matches):
        events = []
        for match in matches:
            t = int(match.group(1))
            mt = float(match.group(2))
            event_type = int(match.group(3))
            events.append((t, mt, event_type))
        return sorted(events, key=lambda x: x[0])
    
    def _process_events(self, events):
        intervals = []
        
        start_events = [e for e in events if e[2] == 1]  # 淡入事件
        end_events = [e for e in events if e[2] == 0]    # 淡出事件
        
        for i, start in enumerate(start_events):
            if i < len(end_events):
                end = end_events[i]
                start_time = start[0] + int(start[1] / 2)
                end_time = end[0] + int(end[1] / 2)
                intervals.append((start_time, end_time))
        
        return intervals
    
    def create_segments(self, events: List[Tuple[int, float, int]]) -> List[Tuple[int, int, str]]:
        segments = []
        current_mode = '4k'
        current_time = 0
        
        if not events:
            return [(0, self.max_time, '4k')]
        
        for t, mt, event_type in events:
            if current_time < t:
                segments.append((current_time, t, current_mode))
                current_time = t
            
            half_time = t + int(mt / 2)
            if current_time < half_time:
                segments.append((current_time, half_time, current_mode))
                current_time = half_time
            
            if event_type == 1: 
                current_mode = '6k'
            else: 
                current_mode = '4k'
        
        if current_time < self.max_time:
            segments.append((current_time, self.max_time, current_mode))
        
        return segments
    
    def get_sky_segments(self) -> List[Tuple[int, int, str]]:
        return self.create_segments(self.camera_events)
    
    def get_ground_segments(self) -> List[Tuple[int, int, str]]:
        return self.create_segments(self.lanes_events)
    
    def collect_notes_by_segments(self, chart: Chart, segments: List[Tuple[int, int, str]], note_type: str = 'all') -> Dict[Tuple[int, int, str], List]:
        segments_notes = {}
        
        for segment in segments:
            start, end, mode = segment
            notes_in_segment = []
            
            for note in chart.notes:
                if hasattr(note, 'start') and hasattr(note, 'end') and hasattr(note, 'x1'):  # Arc
                    note_time = note.start
                    note_valid = note_type in ['arc', 'all']
                elif hasattr(note, 'tick'):  # Tap
                    note_time = note.tick
                    note_valid = note_type in ['tap', 'ground', 'all']
                elif hasattr(note, 'start') and hasattr(note, 'end'):  # Hold
                    note_time = note.start
                    note_valid = note_type in ['hold', 'ground', 'all']
                else:
                    continue
                
                if note_valid and start <= note_time <= end:
                    notes_in_segment.append(note)
            
            segments_notes[segment] = notes_in_segment
        
        return segments_notes
    
    def split_and_solve_chart(self, chart: Chart, conv, solve_4k_func, solve_6k_func):
        all_events = {}
        
        sky_segments = self.get_sky_segments()
        ground_segments = self.get_ground_segments()
        
        sky_notes_by_segment = self.collect_notes_by_segments(chart, sky_segments, 'arc')
        
        for (start, end, mode), notes in sky_notes_by_segment.items():
            if notes:
                segment_chart = Chart(notes, chart.options)
                
                if mode == '6k':
                    segment_events = solve_6k_func(segment_chart, conv)
                else:
                    segment_events = solve_4k_func(segment_chart, conv)
                
                for time_ms, events in segment_events.items():
                    if time_ms not in all_events:
                        all_events[time_ms] = []
                    all_events[time_ms].extend(events)
        
        ground_notes_by_segment = self.collect_notes_by_segments(chart, ground_segments, 'ground')
        
        for (start, end, mode), notes in ground_notes_by_segment.items():
            if notes:
                segment_chart = Chart(notes, chart.options)
                
                if mode == '6k':
                    segment_events = solve_6k_func(segment_chart, conv)
                else:
                    segment_events = solve_4k_func(segment_chart, conv)
                
                for time_ms, events in segment_events.items():
                    if time_ms not in all_events:
                        all_events[time_ms] = []
                    all_events[time_ms].extend(events)
        
        return all_events
    
    def _get_max_time(self, chart: Chart) -> int:
        max_time = 0
        for note in chart.notes:
            if hasattr(note, 'end'):
                max_time = max(max_time, note.end)
            elif hasattr(note, 'tick'):
                max_time = max(max_time, note.tick)
        return max_time