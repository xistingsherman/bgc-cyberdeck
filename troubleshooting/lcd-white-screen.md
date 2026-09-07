# 3.5" LCD Shows a Blank White Screen

## Symptom

The 3.5" ILI9486 panel lights up a uniform white after boot and never draws
anything. Usually seen right after running the original `goodtft` `LCD35-show`
script from `lcd-driver/LCD35-show`.

The backlight on these boards is wired straight to the header's 3.3V/5V, so it
comes on whether or not anything is driving the panel. **A white glow means the
backlight is on but the ILI9486 controller never received its init sequence** --
no driver ever bound to it. The only question is why nothing bound.

---

## Step 1: Confirm the panel was never set up

```bash
grep -iE 'spi|dtoverlay' /boot/firmware/config.txt
dmesg | grep -iE 'ili9486|piscreen|fbtft'
ls /sys/class/drm/
```

A broken setup looks like this:

```
#dtparam=spi=on
dtoverlay=vc4-kms-v3d
dtoverlay=dwc2,dr_mode=host
...
card0  card1  card1-HDMI-A-1  card1-HDMI-A-2  card1-Writeback-1 ...
```

Three tells:

- `dtparam=spi=on` is **commented out** -- SPI0 is off, so nothing can reach
  the panel at all.
- There is no `piscreen` line.
- `/sys/class/drm/` has only vc4's HDMI outputs and v3d's render node. A working
  panel adds a `SPI-1` connector.

(Watch out for a false positive on the `dmesg` grep: a hostname containing
"spi" -- like `spiderverse` -- matches the `spi` pattern. Grep for `ili9486`
rather than `spi` to avoid it.)

---

## Step 2: Understand why `LCD35-show` cannot work here

`lcd-driver/LCD35-show` is the upstream goodtft script, written for
Buster/Bullseye. It fails on Trixie for five independent reasons, and on a Pi 5
all five apply at once.

**It writes the wrong `config.txt`.** The script does
`cp -rf ./boot/config.txt.bak /boot/config.txt`. Since Bookworm the firmware
reads `/boot/firmware/config.txt`. Everything it configured -- `dtparam=spi=on`,
`dtoverlay=tft35a:rotate=90` -- landed in a file nothing reads. Same for
`/boot/overlays/`, which should be `/boot/firmware/overlays/`. This alone is
fatal, and it is why Step 1 shows a config the script apparently never touched.
The upside: there is nothing to undo.

**Its overlay is compiled for the wrong SoC.** `tft35a-overlay.dtb` was built
against the BCM2835/2711 device tree. The Pi 5 is BCM2712 with the RP1
southbridge, where SPI, GPIO and the interrupt controller live in different
nodes. Even with the path fixed, the firmware fails to resolve the fragments and
skips the overlay -- silently, with no error.

**Its whole display model is gone.** `tft35a` binds the fbtft staging driver to
make a dumb framebuffer, and the script then builds **fbcp** to copy the HDMI
framebuffer onto it. fbcp uses dispmanx (`bcm_host`, VideoCore), which Raspberry
Pi removed in Bookworm; the Pi 5 has no legacy firmware graphics path at all and
`libraspberrypi-dev` does not exist for it. Even a correctly loaded panel would
never receive a pixel.

**The HDMI keys are inert.** `hdmi_force_hotplug`, `hdmi_group`, `hdmi_mode`,
`hdmi_cvt` and `hdmi_drive` are legacy firmware options ignored under KMS, and
the Pi 5 is KMS-only.

**The touch half targets a stack Trixie does not run.** `99-calibration.conf`,
`99-fbturbo.conf`, `xserver-xorg-input-evdev` and `/etc/inittab` are all X11-and-
sysvinit era. Trixie's desktop is Wayland (labwc) on systemd, so calibration has
to go through libinput instead.

---

## Step 3: Install the panel properly

Use `lcd-driver/LCD35-show-pi4b` instead. It drives the panel as a real DRM/KMS
display through the in-tree `piscreen` overlay, leaves `vc4-kms-v3d` alone so
HDMI keeps working, and needs no downloaded companion files.

First check the overlay is present -- the script stops if it is not:

```bash
ls /boot/firmware/overlays/ | grep -i piscreen
```

It ships with Raspberry Pi OS. If you are on plain Debian rather than Raspberry
Pi OS, overlays come from the `raspi-firmware` package and may be missing or
stale.

Then:

```bash
sudo ./lcd-driver/LCD35-show-pi4b --speed 32000000
sudo reboot
```

After the reboot the panel is working if:

```bash
ls /sys/class/drm/          # now has a SPI-1 connector
dmesg | grep -i ili9486     # no longer empty
```

To undo everything: `sudo ./lcd-driver/LCD35-show-pi4b --uninstall`

---

## A trap worth knowing: conditional sections in `config.txt`

`config.txt` supports conditional filters -- `[pi4]`, `[pi5]`, `[cm4]`, `[cm5]`,
`[all]` -- and every line after a filter applies **only** to matching boards. A
config containing both `dtoverlay=dwc2,dr_mode=host` and
`dtoverlay=dwc2,dr_mode=peripheral` is a sign that filters are in use, since
those two lines can only coexist under different sections.

This matters because appending an overlay to the end of the file puts it inside
whatever section the file happens to end in. Append `dtoverlay=piscreen` after a
`[cm4]` header and it is filtered out on a Pi 5 -- producing exactly the same
white screen, from a config that looks correct.

`LCD35-show-pi4b` guards against this: its block opens with `[all]` and includes
its own `dtparam=spi=on`, which overrides a commented-out one earlier in the
file. If you add overlay lines by hand, write `[all]` above them.

---

## Once the picture works but the taps do not

The panel drawing correctly while touches land somewhere else is a separate
problem -- the calibration matrix, not the driver. The matrix baked into
`LCD35-show-pi4b` was fit on the workshop unit at `--transform 180`; it is
per-panel and per-rotation, so changing either means re-measuring. See
"Recalibrating the touchscreen" in the README for the corner-press procedure.

Speckled noise, torn rows, flicker or a dark panel are a different problem
again: the SPI clock is too fast for that board and ribbon. Re-run with a lower
`--speed` (64 -> 48 -> 32 -> 24 MHz). There is no damage risk in trying a speed
that is too high.
