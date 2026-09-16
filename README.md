# AI UNLEASHES CHAOS

Lorenz Attractor Circuit by Paul Horowitz in KiCAD

In graduate school I worked with Paul Horowitz, of [Art of Electronics](https://artofelectronics.net/) fame. I even contributed a few bits and pieces to the 3rd edition. (I am thanked in the footnotes, one of which simply says, "Jason, again.) I want you to build a nice little present for Paul, which could also live on as an open source project and a kit that people could build.

![The board](docs/images/lorenz-render-iso.png)

## What it is

A 100 x 100 mm, two-layer, USB-C-powered analog computer that solves

    dx/dt = s (y - x)          s = 10
    dy/dt = r x - y - x z      r = 21.3 .. 37.0, on a knob
    dz/dt = x y - b z          b = 8/3

in real time, continuously, with three op-amp integrators and two **MPY634**
analog multipliers — Paul's exact parts, in hand-solderable packages, so the
circuit stays literally his. Hang a scope on `x` and `z` in X-Y and the
attractor's owl's face appears within a second of power-up.

**The interesting bits:**

* **Four speeds on a DIP switch** — `fast!` (τ = 2.2 ms) through `slower!`
  (572 ms), the six sliders reading left to right as a two-digit binary
  number. At `slower!` you can follow the dot around a wing by eye.
* **An r knob.** 21.3 to 37.0 on a single-turn trimmer, which takes you from
  "the trace spirals into one wing and stops" through the bistable window at
  r ≈ 24.1–24.7 and Lorenz's own 28, to a tight fast orbit at 37. Its wiper is
  tied to one end of the track on purpose: grit under a wiper then means
  *maximum resistance*, never an open circuit.
* **A chaos lamp.** One RGB LED whose colour is the state vector, with the
  reference, the die mapping and all three resistors chosen by modelling the
  LEDs against the CIE 1931 observer and rendering [660 wirings of
  it](docs/lamp/). Mostly deep blue, with a swirl through the colour wheel
  every time the trajectory changes wings.
* **A real isolated ground split.** The DC/DC converter's isolation is
  actually used: analog ground and USB ground are separate pours with a 1 mm
  gap, bridged only by 1 M, 2.2 nF and a solder jumper, so no mains-referenced
  loop runs through a signal whose full scale is 2 V.
* **`SYNC IN X`.** A fourth BNC and a weight knob: feed it another board's `x`
  output and the two boards synchronise — Pecora–Carroll on the bench. Pull
  the cable and they diverge again from states that agreed to a few
  millivolts. The knob is linear in coupling strength from 0 to 10, with the
  locking threshold at about 70 % of rotation.
* **Everything is generated.** There is no hand-edited schematic or board.
  `./make.py` writes the symbols, footprints, 3D models, schematic, placement,
  routing, silkscreen, gerbers, BOM and CPL from Python, then checks them:
  141 circuit assertions read the exported netlist back and re-derive the
  equations, the QR codes on the back are decoded out of the gerbers, and a
  clean clone rebuilds byte-identically.

![Front](docs/images/lorenz-render-top.png)
![Back](docs/images/lorenz-render-bottom.png)

The back carries the equations, the owl's face drawn from a real integration
of them, and QR codes to Paul's page and to this repository.

## Building it

Needs KiCad 10, and Python 3 with `numpy` and `Pillow`; `pdftoppm`
(poppler-utils) for the preview images.

```bash
# point at an extracted KiCad 10 AppImage (skip if kicad-cli is on your PATH)
export KICAD_APPRUN=$HOME/.local/kicad10/AppDir/AppRun

./make.py                # build and check everything  (~40 s)
./make.py --clean        # delete everything it generates
```

Upload `out/lorenz/lorenz-gerbers.zip`, `-bom.csv` and `-cpl.csv` to a fab.
Read **[docs/MANUFACTURING.md](docs/MANUFACTURING.md)** first — it lists the
part rotations to check in the fab's preview before you pay.

## More

* **[docs/DESIGN_NOTES.md](docs/DESIGN_NOTES.md)** — the circuit, every
  changed value and why, and how the lamp was chosen.
* **[docs/DESIGN_REVIEW.md](docs/DESIGN_REVIEW.md)** — the design reviews,
  including the bugs the checks caught.
* **[CLAUDE_CODE_CHAT.md](CLAUDE_CODE_CHAT.md)** — the entire conversation
  that produced this board, prompt by prompt.

Circuit by Paul Horowitz. Board by Jason Gallicchio and Claude Opus 5 Max.
