BarcodeScanner
===
For every successful scan of a barcode, notify a signal with the barcode value in plain text.

**NOTE**: Because this block uses threading to handle the scanner, a child thread will be left running while the block tries to stop. This will log a WARNING that the containing service did not stop in time, which is safe to ignore.

Properties
---
- **Device**: (advanced) The HID Device node, exact location and naming depends on operating system.

Example
---
```
{
  'barcode': 'ABC123!@#'
}
```

Commands
---
None
