import socket
import struct
import subprocess
import threading
import time
import random
import os

import av

from algo.algo_base import TouchAction


class DeviceController:
    serial: str | None
    session_id: str
    video_socket: socket.socket
    control_socket: socket.socket
    server_process: subprocess.Popen
    streaming_collector: threading.Thread
    control_collector: threading.Thread
    device_width: int
    device_height: int
    collector_running: bool
    immediate_send_lock: threading.Lock

    def __init__(self, serial: str | None = None, port: int = 27188, push_server: bool = True, server_dir: str = '.') -> None:
        self.serial = serial
        adb = ('adb',) if serial is None else ('adb', '-s', serial)
        self.session_id = format(random.randint(0, 0x7FFFFFFF), '08x')
        server_file = next(filter(lambda p: p.startswith('scrcpy-server-v'), os.listdir(server_dir)))
        server_file = os.path.join(server_dir, server_file)
        server_version = server_file.split('v')[-1]
        if push_server:
            subprocess.run([*adb, 'push', server_file, '/data/local/tmp/scrcpy-server.jar'])
        subprocess.run([*adb, 'reverse', f'localabstract:scrcpy_{self.session_id}', f'tcp:{port}'])
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        skt.bind(('localhost', port))
        skt.listen(1)
        command_line = [
            *adb,
            'shell',
            'CLASSPATH=/data/local/tmp/scrcpy-server.jar',
            'app_process',
            '/',
            'com.genymobile.scrcpy.Server',
            server_version,
            f'scid={self.session_id}',
            'log_level=info',
            'audio=false',
            'clipboard_autosync=false',
            'max_size=2768',
        ]
        self.server_process = subprocess.Popen(command_line)
        self.video_socket, _ = skt.accept()
        self.control_socket, _ = skt.accept()
        subprocess.run(
            [*adb, 'reverse', '--remove', f'localabstract:scrcpy_{self.session_id}']
        )

        self.collector_running = True
        self.immediate_send_lock = threading.Lock() 

        def streaming_decoder():
            codec = av.CodecContext.create('h264', 'r')
            try:
                while self.collector_running:
                    _pts = self.video_socket.recv(8)
                    size = int.from_bytes(self.video_socket.recv(4), 'big')
                    packets = codec.parse(self.video_socket.recv(size))
                    for packet in packets:
                        frames = codec.decode(packet)
                        for frame in frames:
                            if self.device_width != frame.width or self.device_height != frame.height:
                                print('[client]', f'device_size: {self.device_width}x{self.device_height} -> {frame.width}x{frame.height}')
                                self.device_width = frame.width
                                self.device_height = frame.height
                            break
                        break
            except Exception as e:
                print(e.with_traceback(None))
                self.collector_running = False

        def ctrlmsg_receiver():
            try:
                while self.collector_running:
                    _msg_type = self.control_socket.recv(1)
                    size = int.from_bytes(self.control_socket.recv(4), 'big')
                    self.control_socket.recv(size)
            except Exception as e:
                print(e.with_traceback(None))
                self.collector_running = False

        _device_name = self.video_socket.recv(64)
        codec_id = self.video_socket.recv(4).decode()
        self.device_width = int.from_bytes(self.video_socket.recv(4), 'big')
        self.device_height = int.from_bytes(self.video_socket.recv(4), 'big')

        print('[client]', f'device_size = {self.device_width}x{self.device_height}, codec_id = {codec_id}')

        self.streaming_collector = threading.Thread(target=streaming_decoder, daemon=True)
        self.streaming_collector.start()

        self.control_collector = threading.Thread(target=ctrlmsg_receiver, daemon=True)
        self.control_collector.start()

    def touch(self, x: int, y: int, action: TouchAction, pointer_id: int) -> None:
        self.control_socket.send(
            struct.pack(
                '!bbQiiHHHII',
                2,  # SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
                action.value,
                pointer_id,
                x,
                y,
                self.device_width,
                self.device_height,
                0xFFFF,  # pressure
                1,  # action_button: AMOTION_EVENT_BUTTON_PRIMARY
                1,  # buttons: AMOTION_EVENT_BUTTON_PRIMARY
            )
        )

    def tap(self, x: int, y: int, pointer_id: int = 1000, delay: float = 0.1) -> None:
        self.touch(x, y, TouchAction.DOWN, pointer_id)
        time.sleep(delay)
        self.touch(x, y, TouchAction.UP, pointer_id)

    @staticmethod
    def get_devices() -> list[str]:
        ret, output = subprocess.getstatusoutput('adb devices')
        if ret != 0:
            return []
        return [
            serial
            for serial, status in (
                line.split('\t')
                for line in output.splitlines()
                if not line.startswith('*') and line != 'List of devices attached'
            )
            if status == 'device'
        ]


if __name__ == '__main__':
    print(DeviceController.get_devices())
    controller = DeviceController()
    device_width = controller.device_width
    device_height = controller.device_height

    controller.tap(device_width >> 1, device_height >> 1)
