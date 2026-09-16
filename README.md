# AI UNLEASHES CHAOS

[Lorenz Attractor Circuit](https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm) by Paul Horowitz in KiCAD

In graduate school I worked with Paul Horowitz, of [Art of Electronics](https://artofelectronics.net/) fame. I even contributed a few bits and pieces to the 3rd edition. (I am thanked in the footnotes, one of which simply says, "Jason, again.") I want you to build a nice little present for Paul, which could also live on as an open source project and a kit that people could build.

**Only Prompts:**
As an experiment, the entire PCB, along with additions to Paul's original circuit were designed in a few
hours of [prompts to Claude Opus 5 Max](CLAUDE_CODE_CHAT.md). I only typed prompts. 
I only used KiCAD to look at the output of Claude's [python scripts](scripts/), which generated everything else.

![The board](docs/images/lorenz-render-iso.png)

## What it is

A 100 x 100 mm, two-layer, USB-C-powered analog computer that solves

    dx/dt = s (y - x)          s = 10
    dy/dt = r x - y - x z      r = 21.3 .. 37.0, on a knob
    dz/dt = x y - b z          b = 8/3

in real time, continuously, with three op-amp integrators and two **MPY634**
analog multipliers — Paul's exact parts, in hand-solderable packages, so the
circuit stays literally his. Hang a scope on `x` and `z` in X-Y and the
attractor's "owl's face" appears within a second of power-up.

**Fun additions to Paul's original circuit:**

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
  LEDs against the CIE 1931 observer, rendering 660 wirings of it and
  [publishing the hundred most different](docs/lamp/) to flip through.
  Mostly deep blue, with a swirl through the colour wheel every time the
  trajectory changes wings.
* **A real isolated ground split.** The DC/DC converter's isolation is
  actually used: analog ground and USB ground are separate pours with a 1 mm
  gap, bridged only by 1 M, 2.2 nF and a solder jumper, so no mains-referenced
  loop runs through a signal whose full scale is 2 V.
* **`SYNC IN X`.** A fourth BNC and a weight knob: feed it another board's `x`
  output and the two boards synchronise — chaotic synchronisation on the
  bench. Pull
  the cable and they diverge again from states that agreed to a few
  millivolts. The knob is linear in coupling strength from 0 to 10, with the
  locking threshold at about 70 % of rotation.
**Everything here is generated.** There is no hand-edited schematic or board:
`./make.py` writes the symbols, footprints, 3D models, schematic, placement,
routing, silkscreen, gerbers, BOM and CPL from Python, and then checks them.
141 circuit assertions read the exported netlist back and re-derive the
equations from the resistors that are really attached; the QR codes on the
back are decoded out of the gerbers they were plotted into; and a clean clone
rebuilds every deliverable byte-identically.

![Front](docs/images/lorenz-render-top.png)
![Back](docs/images/lorenz-render-bottom.png)

The back carries the equations, the owl's face drawn from a real integration
of them, and QR codes to Paul's page and to this repository.

## Building it

Needs KiCad 10, and Python 3 with `numpy` and `Pillow`; `pdftoppm`
(poppler-utils) for the preview images.

```bash
git clone https://github.com/gallicchio/ai_unleashes_chaos.git

cd ai_unleashes_chaos

# Nothing to configure if kicad-cli is on your PATH, or if a KiCad 10
# AppImage is in ~/.local/bin, ~/Downloads, ~/Applications, ~/bin or /opt:
# the build finds it and mounts it for as long as it runs.  Otherwise:
export KICAD_APPIMAGE=$HOME/.local/bin/kicad-10.0.6-x86_64.AppImage
# ...or, for an AppImage you have already extracted:
# export KICAD_APPRUN=$HOME/.local/kicad10/AppDir/AppRun

./make.py                # build and check everything  (~40 s)
./make.py --clean        # delete everything it generates
```

Upload `out/lorenz/lorenz-gerbers.zip` and `-bom.csv` to a fab, with
`-cpl_jlc_corrected.csv` for the placements if that fab is JLCPCB and
`-cpl.csv` if it is anyone else — JLCPCB turns six of the parts differently
from KiCad, and the corrected file is the same placements with those angles
applied. Read **[docs/MANUFACTURING.md](docs/MANUFACTURING.md)** first: it
lists what to check in the fab's preview before you pay.

## More

* **[docs/DESIGN_NOTES.md](docs/DESIGN_NOTES.md)** — the circuit, every
  changed value and why, and how the lamp was chosen.
* **[docs/DESIGN_REVIEW.md](docs/DESIGN_REVIEW.md)** — the design reviews,
  including the bugs the checks caught.
* **[CLAUDE_CODE_CHAT.md](CLAUDE_CODE_CHAT.md)** — the entire conversation
  that produced this board, prompt by prompt.

Circuit by Paul Horowitz. Board by Jason Gallicchio and Claude Opus 5 Max.
