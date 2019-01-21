from .hid_map import *
from nio import GeneratorBlock, Signal
from nio.properties import VersionProperty
from nio.util.threading import spawn


class BarcodeScanner(GeneratorBlock):

    version = VersionProperty('0.1.0')
    
    def __init__(self):
        super().__init__()
        self.file_descriptor = None
        self._kill = None
        self._thread = None

    def configure(self, context):
        super().configure(context)
        self._kill = False
        self.file_descriptor = open('/dev/hidraw0', 'rb')
        self._thread = spawn(self._delimited_reader)

    def stop(self):
        self._kill = True
        self._thread.join()
        super().stop()

    def _delimited_reader(self):
        delimiter = 40  # carriage return
        buffer = []
        while not self._kill:
            try:
                new_byte = self.file_descriptor.read(1)
            except:
                self.logger.exception('Read from HID device failed')
            if new_byte == delimiter:
                signal_dict = {'barcode': self._decode_buffer(buffer)}
                self.notify_signals([Signal(signal_dict)])
                buffer = []
                continue
            buffer.append(new_byte)

    def _decode_buffer(self, buffer):
        shift = False
        output = ''
        for b in buffer:
            if b > 0:
                if b == 2:  # shift the next character
                    shift = True
                    continue
                map = 'reg' if not shift else 'shift'
                output += hid_map[map][b]
                shift = False
        return output
