from threading import Event
from unittest.mock import Mock, mock_open, patch
from nio import Signal
from nio.block.terminals import DEFAULT_TERMINAL
from nio.testing.block_test_case import NIOBlockTestCase
from nio.util.discovery import not_discoverable
from ..barcode_scanner_block import BarcodeScanner


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
        _mock = mock_open(read_data='foo')
        with patch ('builtins.open', _mock) as mock_file:
            mock_fd = Mock()
            mock_file.return_value = mock_fd
            mock_fd.read.side_effect = self.barcodes[expected_code]
            self.configure_block(blk, {})
            blk.start()
            e.wait(1)  # wait up to 1 sec for signals from block
            blk.stop()
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'barcode': expected_code}
        )
