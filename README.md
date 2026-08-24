# bgc-cyberdeck

Python lessons for the **Black Girls Code** cyberdeck workshop.

A cyberdeck is a handmade, portable computer — in this workshop it's a Raspberry Pi
wired up to lights and a screen. These lessons walk from "what is a variable?" all the
way to blinking a real LED and pulling a live weather forecast off the internet.

Each file is a standalone lesson. Open it, read the comments, run it, then change
something and run it again.

## The lessons

| # | File | What you'll learn |
|---|------|-------------------|
| 1 | `1-variables-and-data-types.py` | Variables, comments, and the basic data types: booleans, integers, floats, strings, lists, and dictionaries |
| 2 | `2-conditional-statements.py` | `if` / `elif` / `else`, plus writing your own function. Builds a "what should I wear?" closet app that picks a coat or jacket based on the temperature and shows the picture |
| 3 | `3-loops.py` | `while` loops, `for` loops, and f-strings for printing formatted text |
| 4 | `4-simple-led-blink.py` | Your first hardware program — turn on an LED wired to GPIO pin 16 |
| 5 | `5-simple-led-loop.py` | Combine loops with hardware to make the LED blink five times |
| 6 | `6-weather-api.py` | Call a real API (weather.gov), read the JSON that comes back, and pull out the current temperature |

Lessons 1–3 and 6 run on any computer. Lessons 4 and 5 need a Raspberry Pi with an
LED connected.

## Setup

You'll need Python 3.12 or newer.

```bash
# create a virtual environment
python -m venv .venv

# activate it — Windows
.venv\Scripts\activate
# activate it — macOS / Linux / Raspberry Pi
source .venv/bin/activate

# install the libraries the lessons use
pip install matplotlib requests gpiozero
```

What each library is for:

- **matplotlib** — displays the clothing image in lesson 2
- **requests** — makes the web request in lesson 6
- **gpiozero** — controls the LED pins in lessons 4 and 5 (Raspberry Pi only)

## Running a lesson

```bash
python 3-loops.py
```

## Wiring the LED (lessons 4 and 5)

The code uses **GPIO 16**. Connect the long leg of the LED (the positive side) through
a resistor to GPIO 16, and the short leg to a ground pin. If you wire your LED to a
different pin, change the number in `LED(16)` to match.

## Notes for lesson 6

The weather.gov API asks every program to identify itself. Before you run
`6-weather-api.py`, replace the placeholder contact info in the `User-Agent` header
with your own:

```python
'User-Agent': '(some-website.com,some-email@email.com)'
```

The coordinates in the file point at San Diego, California. Swap in your own latitude and
longitude to get your local forecast.

## The 3.5" LCD screen

The cyberdeck's little screen is an ILI9486 panel that plugs onto the GPIO header and
talks to the Pi over SPI. On Raspberry Pi OS Trixie it's driven by the `piscreen`
overlay, which ships with the OS — you don't need to download a driver for it.

### Careful: the LCD isn't always `/dev/fb0`

Linux calls each screen a **framebuffer** and numbers them `/dev/fb0`, `/dev/fb1`, and so
on. The number the LCD gets **depends on whether an HDMI monitor is plugged in**:

| HDMI monitor | LCD shows up as |
|---|---|
| Not attached | `/dev/fb0` — with nothing on HDMI, the Pi never makes a framebuffer for it, so the LCD takes the first slot |
| Attached | `/dev/fb1` — HDMI claims `/dev/fb0` and the LCD shifts up |

So don't hard-code the number in a script or a lesson. Look it up first — the LCD is the
one named `fb_ili9486`:

```bash
for f in /sys/class/graphics/fb*; do echo "$f -> $(cat $f/name)"; done
```

This matters because writing to the wrong framebuffer scribbles all over your HDMI
desktop. Once you know the right number, you can prove the panel is alive by filling it
with colored static:

```bash
sudo bash -c 'cat /dev/urandom > /dev/fb0'   # use the number you just looked up
```

Press Ctrl+C to stop.

### Making the screen less sluggish

The panel talks to the Pi over SPI, one pixel at a time down a single wire, and the SPI
clock speed sets how fast a full screen can be redrawn. At the default 16 MHz, one
320x480 frame is about 2.5 million bits, so the screen tops out around **6-7 frames per
second**. Taps feel laggy not because the touchscreen is slow, but because the picture
takes a moment to catch up.

You can push the clock. Edit the `piscreen` line in `/boot/firmware/config.txt`:

```
dtoverlay=piscreen,drm=1,speed=32000000
```

Then `sudo reboot`. Doubling the clock roughly doubles the frame rate. Most of these
3.5" boards are happy at 32 MHz, and some will run at 48 or 64 MHz.

**If you push it too far, back it off.** The signs that the clock is too fast for your
particular board and ribbon cable:

- speckles or confetti-like noise across the image
- rows of the picture torn or shifted sideways
- flickering
- the panel going dark or never drawing at all

Step down one notch at a time — 64 to 48, 48 to 32, 32 to 24 — until it's clean. There's
no damage risk in trying a speed that's too high; the display just garbles, and the next
reboot at a lower speed fixes it.

Changing this does **not** affect the touchscreen. The touch controller is a separate
chip on its own chip-select line with its own much slower clock, so your calibration
stays put.

One honest expectation: even at the highest speed the panel accepts, this will not feel
like a phone or a monitor. Pushing a whole desktop through SPI is inherently slow. That's
the trade for a screen that runs off the GPIO header instead of needing HDMI.

### Recalibrating the touchscreen

The touch panel reports raw numbers that have no idea which way up the screen is, so
whenever you change the rotation, the calibration has to be measured again. The symptom
is unmistakable once you know it: the picture looks perfect and your taps land somewhere
else entirely.

Measure the four corners. Keep the screen in the orientation you actually want, and use a
stylus or a fingernail — a fingertip is several millimetres wide and its centre sits well
inside the corner you're aiming at:

```bash
for corner in TOP-LEFT TOP-RIGHT BOTTOM-RIGHT BOTTOM-LEFT; do
  echo ""; echo ">>> get ready: $corner"; sleep 2
  echo ">>> PRESS AND HOLD $corner NOW"
  sudo timeout 5 evtest /dev/input/event4 2>/dev/null | awk -v c="$corner" '
    /ABS_X/ {sx+=$NF; nx++}
    /ABS_Y/ {sy+=$NF; ny++}
    END {if (nx>0) printf "%-12s ABS_X=%.0f  ABS_Y=%.0f  (n=%d)\n", c, sx/nx, sy/ny, nx;
         else printf "%-12s NO SAMPLES\n", c}'
done
```

(`evtest` comes from `sudo apt install evtest`. Check your event number first with
`grep -A4 -i ads7846 /proc/bus/input/devices | grep Handlers`.)

Divide each reading by 4095 to get a number between 0 and 1. Look at which raw axis
changes as you move **across** the screen:

- If `ABS_X` changes going left-to-right, the matrix is `a 0 c 0 e f` where
  `a = 1 / (x_right - x_left)`, `c = -a * x_left`, `e = 1 / (y_bottom - y_top)`, and
  `f = -e * y_top`
- If `ABS_Y` changes going left-to-right instead, the axes are swapped and the matrix is
  `0 b c d 0 f`, with the same arithmetic applied to the swapped pairs

Put the six numbers in `/etc/udev/rules.d/99-touchscreen-calibration.rules`, or pass them
to the driver script with `--matrix "a b c d e f"`, and reboot.

Two things worth knowing. **`evtest` always shows raw numbers** — the calibration is
applied by libinput further up the stack, so the readings never change no matter what you
put in the matrix. Test by using the desktop, not by re-reading evtest. And **the matrix
is affine**: it can rotate, stretch, and shift, but it can't bend. Resistive panels sag a
little toward the middle, so expect the centre to sit a few pixels off even when all four
corners are perfect.

## Image icon credit

- https://freeicon.com/free-icons/winter-coat/two-color
- https://freeicon.com/free-icons/winter-jacket/two-color
