# LAN Remote Control (Same Network)

> View **and control** a consenting device's screen on the same LAN.  
> Password-protected. Runs without internet (LAN-only).

## ⚠️ Consent & Legality

Only use on devices you own or where you have explicit permission. Unauthorized access is illegal.

## Requirements

- Python 3.9+ on the **target** machine
- On macOS: grant Terminal (or your Python app) **Screen Recording** and **Accessibility** in _System Settings → Privacy & Security_.
- On Windows: usually no extra permissions; run normally.

## Install (on the target machine)

```bash
pip install -r requirements.txt
# set a strong password
export LRC_PASSWORD="YourStrongPassword"   # macOS/Linux
# Windows (PowerShell): [System.Environment]::SetEnvironmentVariable("LRC_PASSWORD","YourStrongPassword","User")
python server.py
```
