# 3.5" LCD Shows a Blank White Screen

## Symptom

The 3.5" ILI9486 panel lights up a uniform white after boot and never draws
anything.

The backlight on these boards is wired straight to the header's 3.3V/5V, so it
comes on whether or not anything is driving the panel. **A white glow means the
backlight is on but the ILI9486 controller never received its init sequence** --
no driver ever bound to it. The only question is why nothing bound.

---

## Which script to run

There are two installers in `lcd-driver/`, one per board. Both do the same thing
by the same method; each is gated to the board it was tested on.

| Board | Script |
|---|---|
| Raspberry Pi 5 | `sudo ./LCD35-show` |
| Raspberry Pi 4 Model B | `sudo ./LCD35-show-pi4b` |

Check which you have with `cat /proc/device-tree/model`.

**Run them with `./`, not with `sh`.** See "Running it with sh" below -- this is
the single most common way to get a wall of errors that hides the real problem.

---

## Step 1: Confirm the panel was never set up

```bash
grep -iE 'spi|dtoverlay' /boot/firmware/config.txt
dmesg | grep -iE 'ili9486|piscreen|fbtft'
ls /sys/class/drm/
```

A Pi where nothing was installed looks like this:

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

## Step 2: Install it

```bash
cd lcd-driver
sudo ./LCD35-show --speed 32000000      # or ./LCD35-show-pi4b on a Pi 4
sudo reboot
```

Before it changes anything, the script checks that
`/boot/firmware/overlays/piscreen.dtbo` exists and stops if it does not. That
overlay ships with Raspberry Pi OS. If you are on plain Debian rather than
Raspberry Pi OS, overlays come from the `raspi-firmware` package and may be
missing or stale.

After the reboot the panel is working if:

```bash
ls /sys/class/drm/          # now has a SPI-1 connector
dmesg | grep -i ili9486     # no longer empty
```

To undo everything: `sudo ./LCD35-show --uninstall`

---

## Running it with `sh`

```
LCD35-show: 22: source: not found
LCD35-show: 41: [[: not found
LCD35-show: 37: cannot open 12.1: No such file
-e
```

This is what `sudo sh LCD35-show` produces. Invoking `sh` explicitly **overrides
the `#!/bin/bash` shebang**, and on Debian `/bin/sh` is dash, which has no `[[`,
no `source`, no `local`, and no `echo -e`.

Two of those messages are worth recognising, because they do not look like what
they are:

- `cannot open 12.1` -- with `[[` gone, dash parsed the `<` in
  `[[ "$ver" < "12.1" ]]` as **input redirection** from a file named `12.1`.
- A stray file named `13.1` appearing in the directory -- same thing with `>`,
  which dash took as **output redirection** and so created the file.

Both scripts now refuse to run under dash and say so in one line instead:

```
run this with bash, not sh: sudo ./LCD35-show
```

Run them as `sudo ./LCD35-show` or `sudo ./LCD35-show-pi4b`.

---

## If you ran the old upstream `LCD35-show`

`lcd-driver/LCD35-show` used to hold the upstream goodtft script, from
<https://github.com/goodtft/LCD-show/blob/master/LCD35-show>, which is still what
most guides for these panels point you at. It is in this repo's git history too.

It was written for Buster/Bullseye and cannot work on Trixie, for five
independent reasons -- worth knowing, because the same reasoning applies to
every other LCD-show fork you will find online.

**It writes the wrong `config.txt`.** It does
`cp -rf ./boot/config.txt.bak /boot/config.txt`. Since Bookworm the firmware
reads `/boot/firmware/config.txt`. Everything it configured -- `dtparam=spi=on`,
`dtoverlay=tft35a:rotate=90` -- landed in a file nothing reads. Same for
`/boot/overlays/`, which should be `/boot/firmware/overlays/`.

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
`99-fbturbo.conf`, `xserver-xorg-input-evdev` and `/etc/inittab` are all
X11-and-sysvinit era. Trixie's desktop is Wayland (labwc) on systemd, so
calibration has to go through libinput instead.

### Cleaning up after it

It also expected companion files -- `./usr/`, `./boot/`, `system_backup.sh`,
`system_config.sh` -- that were never vendored into this repo, so most of it
failed outright. In particular `cp -rf ./boot/config.txt.bak /boot/config.txt`
failed, meaning it never created a stray `/boot/config.txt`. Only three things
got through, all inert under Wayland but worth undoing:

```bash
cd lcd-driver
rm -f 13.1 error_output.txt .have_installed      # junk left in the git repo
sudo rm -f /usr/share/X11/xorg.conf.d/45-evdev.conf
sudo rmdir /etc/X11/xorg.conf.d 2>/dev/null      # empty dir it created
```

Optionally `sudo apt-get purge -y xserver-xorg-input-evdev` -- it gets installed
but nothing uses it on a Wayland desktop.

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

Both scripts guard against this: their block opens with `[all]` and includes its
own `dtparam=spi=on`, which overrides a commented-out one earlier in the file. If
you add overlay lines by hand, write `[all]` above them.

Each script also strips **both** scripts' blocks -- from `config.txt` and from
`rc.xml` -- before writing its own. Moving an SD card between a Pi 4 and a Pi 5
and re-running therefore cannot leave two `dtoverlay=piscreen` lines or two
`<touch>` elements fighting each other.

---

## The picture works but touch does not

Two different causes that look alike. Check the first one first: it presents as
a completely dead touchscreen, which reads as a hardware fault and sends you
looking in the wrong place.

### Touch does nothing, and a monitor is plugged in

With more than one output, wlroots spreads the touchscreen's coordinate space
across the **whole desktop** unless it is told which output the panel is. With
HDMI connected that puts every tap somewhere out on the monitor -- the panel
looks perfect and responds to nothing.

Confirm it by unplugging HDMI and rebooting. If touch works with the monitor
gone, this is it.

The fix is a `<touch>` element in labwc's `rc.xml` binding the device to the
panel's output:

```xml
<touch deviceName="ADS7846 Touchscreen" mapToOutput="SPI-1" mouseEmulation="no"/>
```

Both scripts write this for you. It is read when the compositor starts, so log
out and back in after installing -- it does not apply live.

Three things make that edit less simple than it looks, and all fail silently:

- **The root element may be either `<labwc_config>` or `<openbox_config
  xmlns="http://openbox.org/3.4/rc">`.** labwc accepts both -- the second is
  inherited from openbox's schema. Whichever your `rc.xml` uses, the `<touch>`
  element goes inside it.

- **labwc reads only ONE `rc.xml`** -- yours if it exists, otherwise
  `/etc/xdg/labwc/rc.xml`. It does **not** merge them. That is the opposite of
  `autostart`, where both files run. So a hand-written user `rc.xml` containing
  just the `<touch>` line discards the ~170 lines Raspberry Pi OS ships in the
  system file, trading a dead touchscreen for a subtly broken desktop. Copy the
  system file first, then add the element to the copy.
- **An XML comment may not contain `--` anywhere.** Marking your edit with
  something like `<!-- --- mine --- -->` makes libxml2 reject the entire file,
  and labwc falls back to built-in defaults -- losing every setting in it, not
  just yours.

### Taps land in the wrong place

That is the calibration matrix, not the driver. The matrix baked into both
scripts was fit on the workshop unit at `--transform 180`. It is a property of
the panel rather than the board, so it carries between Pis with the same screen,
but changing the rotation or swapping the panel means re-measuring. See
"Recalibrating the touchscreen" in the README for the corner-press procedure.

---

## Speckled noise, torn rows or flicker

Speckled noise, torn rows, flicker or a dark panel are a different problem
is the SPI clock running too fast for that board and ribbon. Re-run with a lower
`--speed` (64 -> 48 -> 32 -> 24 MHz). There is no damage risk in trying a speed
that is too high.
