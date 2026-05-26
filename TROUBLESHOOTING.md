# Troubleshooting

Real-world problems encountered during hardware bring-up and integration, with diagnoses and fixes. Each entry documents the symptom, what the underlying issue actually was, and how to resolve it.

When a new problem is solved, add an entry here. When an existing problem recurs, check here first.

---

## SSH connection closes immediately after typing password

**Symptom:** SSH into the Pi from a laptop works up to the password prompt, but after typing the password and pressing Enter, the connection drops with a message like:

```
Connection closed by 172.16.x.x port 22
```

**Diagnosis:** Not a credential problem. The Pi's SSH server timed out before receiving the password. The `Timeout before authentication` line appears in the Pi's SSH log, confirming this.

**Cause:** SSH password prompts hide all input — no characters, no asterisks, no cursor feedback. It's easy to pause and second-guess what you've typed. If the pause exceeds the SSH `LoginGraceTime` (default 120 seconds), the server closes the connection.

**Fix:** Type the password promptly when prompted. Even if you're unsure mid-password, don't pause for minutes to think — either commit and hit Enter, or hit Enter on whatever's in the buffer and let it fail cleanly, then retry. The lack of visual feedback is normal SSH behaviour; the password keystrokes are being received.

**How to verify the diagnosis on the Pi side:**

```bash
sudo journalctl -u ssh -n 30 --no-pager
```

Look for a line like:

```
Timeout before authentication for connection from <laptop_ip> to <pi_ip>
```

If you see that, this is the issue. If you see "Failed password" instead, it's a real credential problem and you need to fix the password (not the timing).

---

## Wi-Fi disabled on Pi after first boot despite Imager configuration

**Symptom:** SSH from laptop fails to find the Pi. `myindoornav.local` does not resolve. `arp -a` does not show the Pi. On directly inspecting the Pi via monitor, the Wi-Fi icon in the top-right of the desktop shows a red X (not connected).

**Diagnosis:** The Pi never joined the Wi-Fi network. The credentials configured in the Raspberry Pi Imager were saved correctly, but the wireless LAN radio itself was turned off.

**Cause:** Unclear. Imager settings should enable Wi-Fi by default when credentials are provided. Possible explanations:
- The "Configure wireless LAN" toggle in the Imager was not ticked even though credentials were filled in (the credentials fields can exist independently of the toggle)
- A first-boot service left the radio disabled
- A driver or firmware quirk specific to this Pi 5 / OS combination

**Fix:** From the Pi desktop, click the Wi-Fi icon in the top-right corner. In the dropdown, toggle "Turn on wireless LAN". The saved credentials will reconnect automatically — no need to re-enter SSID or password.

**Prevention for future flashes:** When configuring the Imager, double-check that "Configure wireless LAN" is actively ticked (not just filled in) before saving settings and writing the card.

**Verification after fix:**

```bash
# On the Pi desktop terminal:
ping -c 3 google.com         # confirms internet works
hostname -I                  # shows the Pi's IP address
```

If both work, Wi-Fi is fully restored.

---

## Diagnostic principle: check the device's own state before suspecting the network

When SSH or similar remote-access tools fail, the temptation is to suspect network-level problems first (firewalls, client isolation, router config). These are often the wrong place to start.

The faster diagnostic path is **from the device outward**:

1. Is the device powered on and booted correctly? (Check LEDs, look at the screen if attached)
2. Has the device joined the network at all? (Check the Wi-Fi indicator on the device itself, or run `hostname -I` locally)
3. Does the device have working internet? (Run `ping -c 3 google.com` locally)
4. *Only then* worry about laptop-to-device communication, firewall rules, client isolation, etc.

Most "the network is broken" symptoms turn out to be device-side issues that look like network problems from the outside. Checking the device first eliminates the most likely causes quickly.

This requires temporary direct access to the device (monitor + keyboard, or a console cable). Worth doing for first-time bring-up even if the long-term plan is fully headless.

## Package `libatlas-base-dev` not found on Pi OS Bookworm

**Symptom:** `sudo apt install libatlas-base-dev` fails with:

**Diagnosis:** `libatlas-base-dev` has been superseded on newer Pi OS Bookworm releases. The package was removed from the standard repositories in favour of OpenBLAS.

**Fix:** Use `libopenblas-dev` instead, which provides the same kind of optimised linear algebra routines that numpy and opencv depend on:

```bash
sudo apt install -y libopenblas-dev
```

NumPy and OpenCV detect whichever BLAS library is present at install time, so the swap is transparent to user code.

**Related:** `libtiff5` is also unavailable on newer Bookworm and follows the same pattern. Use `libtiff6` instead — confirmed working as a drop-in replacement.
