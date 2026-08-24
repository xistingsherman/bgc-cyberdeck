# Raspberry Pi Bluetooth Troubleshooting
 
## Symptom
```
[bluetoothctl]> power on
Failed to set power on: org.bluez.Error.Failed
[bluetoothctl]>
```
 
This error means bluez is running and can talk to the daemon, but the underlying HCI adapter isn't coming up. Common causes: rfkill blocking it, firmware/driver not loaded, or the adapter not bound to its UART/USB interface.
 
---
 
## Step 1: Check rfkill
```bash
rfkill list
```
If Bluetooth shows `Soft blocked: yes` or `Hard blocked: yes`:
```bash
sudo rfkill unblock bluetooth
```
Then retry `bluetoothctl power on`.
 
---
 
## Step 2: Check if the controller is detected
```bash
hciconfig -a
```
- No `hci0` listed at all → kernel isn't recognizing the adapter.
- `hci0` present but `DOWN` → try:
```bash
  sudo hciconfig hci0 up
```
  Any error here is usually more specific and points closer to the root cause.
 
---
 
## Step 3: Check dmesg for the actual failure
```bash
sudo dmesg | grep -i -E "blue|hci|bcm"
```
On Pi boards, the Bluetooth chip is typically a Broadcom part on UART, requiring firmware load via `hciattach`/`btuart` (handled by `hciuart.service`). Look for firmware load failures or `command tx timeout`.
 
---
 
## Step 4: Check the hciuart service (Pi-specific)
```bash
sudo systemctl status hciuart
```
If this failed or isn't running, the UART attach never happened — no live HCI device exists for bluez to power on. Try:
```bash
sudo systemctl restart hciuart
sudo systemctl restart bluetooth
```
 
---
 
## Step 5: Confirm Bluetooth isn't disabled in firmware config
```bash
grep -i bluetooth /boot/firmware/config.txt
```
If you see:
```
dtoverlay=disable-bt
```
remove that line and reboot — this disables the onboard chip entirely.
 
---
 
## Quick reference: other bluetoothctl errors
 
| Error | Likely cause |
|---|---|
| `No default controller available` | No adapter detected at all — check `hciconfig -a`, `dmesg`, or firmware config |
| `org.bluez.Error.Blocked` | rfkill soft/hard block — see Step 1 |
| `org.bluez.Error.Failed` | Driver/firmware not loaded, or UART not attached — see Steps 2–4 |
| No response / hangs | `bluetooth` service not running — `sudo systemctl restart bluetooth` |
 
---
 
## Notes
- Pi model / OS:
- Fresh setup or previously working:
- Findings from `rfkill list`:
- Findings from `hciconfig -a`:
 