from time import sleep
from .hid_map import *
from nio import GeneratorBlock, Signal
from nio.properties import StringProperty, VersionProperty
from nio.util.threading import spawn


class BarcodeScanner(GeneratorBlock):

    version = VersionProperty('0.1.0')
    device = StringProperty(title='Device',
                            default='/dev/hidraw0',
                            advanced=True)

    def __init__(self):
        super().__init__()
        self.file_descriptor = None
        self._kill = None
        self._thread = None

    def configure(self, context):
        super().configure(context)
        self._connect()

    def stop(self):
        self._disconnect()
        super().stop()

    def _connect(self):
        self.logger.debug(
            'Opening HID Device {}'.format(self.device()))
        while not self.file_descriptor:
            try:
                self.file_descriptor = open(self.device(), 'rb')
            except:
                self.logger.error('Unable to open HID Device, trying again in 10 seconds')
                sleep(10)
        self._kill = False
        self._thread = spawn(self._delimited_reader)

    def _delimited_reader(self):
        self.logger.debug('Reader thread spawned')
        delimiter = b'\x28'  # carriage return
        buffer = []
        while not self._kill:
            try:
                new_byte = self.file_descriptor.read(1)
            except:
                self.logger.exception(
                    'Read operation from HID Device failed')
                self._disconnect()
                self._connect()
                break
            if new_byte == delimiter:
                signal_dict = {'barcode': self._decode_buffer(buffer)}
                self.notify_signals([Signal(signal_dict)])
                buffer = []
                continue
            buffer.append(new_byte)
        self.logger.debug('Reader thread terminated')

    def _decode_buffer(self, buffer):
        self.logger.debug('decoding {} bytes'.format(len(buffer)))
        shift = False
        output = ''
        for b in buffer:
            if b != b'\x00':
                if b == b'\x02':  # shift the next character
                    shift = True
                    continue
                map = 'reg' if not shift else 'shift'
                output += hid_map[map][ord(b)]
                shift = False
        return output

    def _disconnect(self):
        self.logger.debug('closing HID Device')
        self._kill = True
        self.file_descriptor.close()
        self.file_descriptor = None
