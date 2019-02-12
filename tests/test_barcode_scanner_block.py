from threading import Event
from unittest.mock import Mock, patch
from nio import Signal
from nio.block.terminals import DEFAULT_TERMINAL
from nio.testing.block_test_case import NIOBlockTestCase
from nio.util.discovery import not_discoverable
from ..barcode_scanner_block import BarcodeScanner


class ReadSizeBytes():
    """Adds partial read functionality to mocked file descriptors.

    Args:
        data: Bytes over which to iterate.

    """

    def __init__(self, data=''):
        self._data = data

    def __call__(self, l=0):
        # returns the next `l` number of bytes from self._data
        if not self._data:
            return ''
        if not l:
            l = len(self._data)
        r, self._data = self._data[:l], self._data[l:]
        return r

@not_discoverable
class ScannerEvents(BarcodeScanner):
    """Block extension for testing which sets (optional) Events.

    Args:
        notify_event: Event to be set when signals are notified
        ok_event: Event to be set when 'ok' status is set
        warning_event: Event to be set when 'warning' status is set

    """

    def __init__(self, notify_event=None, ok_event=None, warning_event=None):
        super().__init__()
        self.notify_event = notify_event
        self.ok_event = ok_event
        self.warning_event = warning_event

    def notify_signals(self, signals):
        super().notify_signals(signals)
        if self.notify_event:
            self.notify_event.set()

    def set_status(self, status,  message=''):
        super().set_status(status)
        if status == 'ok' and self.ok_event:
            self.ok_event.set()
        if status == 'warning' and self.warning_event:
            self.warning_event.set()

class TestBarcodeScanner(NIOBlockTestCase):

    barcodes = {
        'LS01': (
            b'\x02\x00\x00\x00\x00\x00\x00\x00'
            b'\x02\x00\x0f\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x02\x00\x00\x00\x00\x00\x00\x00'
            b'\x02\x00\x16\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x27\x00\x00\x00\x00\x00'
            b'\x00\x00\x1e\x00\x00\x00\x00\x00'
            b'\x00\x00\x28'
        ),
    }

    @patch('builtins.open')
    def test_read(self, mock_open):
        """When a barcode is scanned a signal is notified."""
        expected_code = 'LS01'
        notify_event = Event()
        blk = ScannerEvents(notify_event=notify_event)
        mock_file = Mock()
        mock_open.return_value = mock_file
        mock_file.read.side_effect = ReadSizeBytes(
            self.barcodes[expected_code])
        self.configure_block(blk, {})
        blk.start()
        self.assertTrue(notify_event.wait(1))
        blk.stop()
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'barcode': expected_code})

    @patch('builtins.open')
    def test_device_property(self, mock_open):
        """HID device node is configurable."""
        blk = BarcodeScanner()
        self.configure_block(blk, {
            'device': 'foo',
        })
        blk.start()
        blk.stop()
        mock_open.assert_called_once_with('foo', 'rb')

    @patch(BarcodeScanner.__module__ + '.sleep')
    @patch('builtins.open')
    def test_warning_status_connect(self, mock_open, mock_sleep):
        """The block is in warning status while the hardware is unavailable."""
        expected_code = 'LS01'
        mock_open.side_effect = [OSError, Mock()]
        notify_event = Event()
        ok_event = Event()
        warning_event = Event()
        blk = ScannerEvents(ok_event=ok_event, warning_event=warning_event)
        self.configure_block(blk, {})
        blk.start()

        # The first attempt to open the hardware fails, block is in warning
        self.assertTrue(warning_event.wait(1))
        # Second attempt is successful, block is ok
        self.assertTrue(ok_event.wait(1))

    @patch(BarcodeScanner.__module__ + '.sleep')
    @patch('builtins.open')
    def test_warning_status_read(self, mock_open, mock_sleep):
        """The block is in warning status while the hardware is unavailable."""
        expected_code = 'LS01'
        mock_file = Mock()
        mock_file.read.side_effect = ReadSizeBytes(
            self.barcodes[expected_code])
        mock_open.return_value = mock_file
        notify_event = Event()
        ok_event = Event()
        warning_event = Event()
        blk = ScannerEvents(
            notify_event=notify_event,
            ok_event=ok_event,
            warning_event=warning_event)
        self.configure_block(blk, {})
        blk.start()

        # first attempt to read works and a signal notified
        self.assertTrue(notify_event.wait(1))
        self.assert_num_signals_notified(1)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'barcode': expected_code})
        notify_event.clear()  # we're going to use this one again

        # something goes wrong in read(), the block is back in warning
        mock_file.read.side_effect = Exception
        self.assertTrue(warning_event.wait(1))

        # block reconnects on its own, and returns to ok
        mock_file.read.side_effect = ReadSizeBytes(
            self.barcodes[expected_code])
        self.assertTrue(ok_event.wait(1))
        # read operations resume and we get another signal
        self.assertTrue(notify_event.wait(1))
        self.assert_num_signals_notified(2)
        blk.stop()

    @patch('builtins.open')
    def test_unknown_characters(self, mock_open):
        """Scanning unknown characters is handled."""
        expected_code = 'LS01'
        scanned_code = b'\xf8\x28'  # unmapped byted followed by delimiter
        scanned_code += self.barcodes[expected_code]  # successful scan
        notify_event = Event()
        blk = ScannerEvents(notify_event=notify_event)
        mock_file = Mock()
        mock_open.return_value = mock_file
        mock_file.read.side_effect = ReadSizeBytes(scanned_code)
        self.configure_block(blk, {})
        blk.start()
        # wait for successful read and notify
        self.assertTrue(notify_event.wait(1))
        self.assertTrue(blk._thread.is_alive())
        self.assert_num_signals_notified(2)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'barcode': None})
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][1].to_dict(),
            {'barcode': expected_code})
        blk.stop()