from threading import Event
from unittest.mock import Mock, mock_open, patch
from nio import Signal
from nio.block.terminals import DEFAULT_TERMINAL
from nio.testing.block_test_case import NIOBlockTestCase
from nio.util.discovery import not_discoverable
from ..barcode_scanner_block import BarcodeScanner


class ReadSizeBytes():
    def __init__(self, data=""):
        self._data = data

    def __call__(self, l=0):
        if not self._data:
            return ""
        if not l:
            l = len(self._data)
        r, self._data = self._data[:l], self._data[l:]
        return r

@not_discoverable
class ReadEvent(BarcodeScanner):

    def __init__(self, event):
        super().__init__()
        self._event = event

    def notify_signals(self, signals):
        super().notify_signals(signals)
        self._event.set()

class TestBarcodeScanner(NIOBlockTestCase):

    barcodes = {
        'LS01': (
            b'\x02\x00\x00\x00\x00\x00\x00\x00\x02\x00\x0f\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x02\x00\x00\x00\x00\x00\x00\x00\x02\x00\x16\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x27\x00\x00\x00\x00\x00\x00\x00\x1e\x00'
            b'\x00\x00\x00\x00\x00\x00\x28'
        ),
    }

    def test_read(self):
        """When a barcode is scanned a signal is notified"""
        expected_code = 'LS01'
        e = Event()
        blk = ReadEvent(e)
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            mock_file.return_value.read.side_effect = ReadSizeBytes(self.barcodes['LS01'])
            self.configure_block(blk, {})
            blk.start()
            e.wait(1)  # wait up to 1 sec for signals from block
            blk.stop()
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'barcode': expected_code}
        )
