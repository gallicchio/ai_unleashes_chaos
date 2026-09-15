# ai_unleashes_chaos

Lorenz Attractor Circuit by Paul Horowitz in KiCAD

## Prompt 1

In graduate school I worked with Paul Horowitz, of [Art of Electronics](https://artofelectronics.net/) fame. I even contributed a few bits and pieces to the 3rd edition. (I am thanked in the footnotes, one of which simply says, "Jason, again.) I want you to build a nice little present for Paul, which could also live on as an open source project and a kit that people could build.

Make a KiCAD 10 project, schematic, and PCB to implement [Paul's Lorenz Attractor Circuit](https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm).
* It should take power in through a simple USB-C connector. This means that you'll either need to make a negative voltage or change the circuit to power the op amps from only +5V. 
* You may need to make other changes to the circuit. Do it in a way that maintains is simple elegance and educational value.
* Its outputs ()"x", "-y", and "z") should each come out on a BNC connector.
* It would be good to be able to switch the capacitor "C" to the three different values shown: "slow!", "nice!", and "fast!". However, if this explodes the complexity, just pick "nice!".
* Feel free to use modern components if necessary, but try to keep packages as large as is reasonable. SMT is ok, but I want people to be able to hand solder and rework as much as possible (0805 R's and C's, for example).  I want you to take it all the way to gerbers, a BOM, and a CPL file that I can simply upload to a place like JLCPCB, NextPCB Rev 0, or CircuitHub.
* Select components that these places have plenty of in stock, such that that I can order in only one step. I do not want to consign any parts. I do not want to wait for out of stock items.
* Make 2-layer and also a 4-layer version. Do all of the placement and routing yourself.
* You should have a shell script or python file that just "makes" everything on the command line: the schematic, PCB, manufacturing files, and a document with a cost estimate and other manufacturing instructions for me. Your scripts should run as many checks as necessary to ensure that I can just upload the files, "click go", and have working boards show up at Paul's house.
* Make the design rule checks at least as strict as the cheap option's design rules at JLCPCB, NextPCB Rev 0, and CircuitHub.
* Lay out the schematic and the PCB as Paul does in his hand-drawn schematic. The schematic should be a single page. The PCB should fit within the fab and assembly house's discounted small size, but otherwise should be legible and logically arranged.
* The schematic should be in the beautiful "Art of Electronics style" --- the circuit is drawn, and things are labeled in such a way as to immediately answer typical questions that might arise in a reader's mind:
 - I don't want to see labels that disappear and magically reappear elsewhere (except maybe power and ground).
 - If a note belongs with a node or IC, write it right next to the node, not somewhere off to the side.
 - No labels should overlap components or other labels. You can spread things out a bit on the page to allow this to happen, but keep everything within the borders of the page. Really check that this is the case.
* The PCB's silkscreen should make it clear what the inputs and outputs are. 
 - Nothing on the silkscreen should overlap other silkscreen or components. Really check this. Make it beautiful.
 - The silkscreen should have the following on it: "AI Unleashes Chaos", "Circuit by Paul Horowitz", "PCB by Jason Gallicchio and Claude", today's date, and "rev A" in case we need to re-spin.
 - Component values and IC names should also be on the silkscreen (in addition to the reference designators) for educational purposes.
 - Write the equations and "suggested parameters" on the silkscreen. Check that the circuit actually implements them.
 - Include a little drawing of the "owl's face" on the PCB like Paul does in his schematic.
* Do a self-critical design review of the circuit, the way the schematic is drawn, the way the PCB is laid out, and the component and manufacturing selections. Make any changes. Iterate until satisfied.
* I will open the schematic and PCB in KiCAD and give you feedback after you've worked on it for many hours.

Record your response below in this document. Do this regularly, and check things into git as you go.

## Response 1

Built. `./make.py` regenerates everything from scratch in about 40 seconds and
refuses to finish unless every check passes. Current state:

| check | result |
|---|---|
| ERC | 0 violations |
| DRC + schematic parity, 2-layer | 0 violations |
| DRC + schematic parity, 4-layer | 0 violations |
| circuit checker (reads the netlist, not the drawing) | 75 checks pass |
| schematic layout (205 text items) | no overlaps, nothing outside the frame |
| fab package | all checks pass |

Open `hardware/lorenz.kicad_pro`. The 4-layer variant is `lorenz-4layer.kicad_pro`
and shares the schematic.

### What it is

Your circuit, unchanged: three lossy integrators built from **LF412s** and two
**MPY634s**, with the resistor values exactly as you drew them — 100k, 100k,
35.7k, 10k, 1M, 10k, 374k. The sign inversions still come free from swapping the
multipliers' differential inputs. `scripts/check_circuit.py` walks the exported
netlist, works out what each integrator actually computes from the resistors
really attached to it, and recovers **s = 10, r = 28.01, b = 2.6738** — 8/3 plus
0.27%, which is the 374k. It also checks the virtual earths, the multiplier
hookup, the matched capacitors, the outputs and every supply pin.

Both of your parts are still stocked at JLCPCB: LF412CDR (1037) and MPY634KU
(874). Being able to keep them is why the schematic looks like yours.

### The three things that had to change

**USB-C power.** 5 V in → `A0515S-2WR2` isolated module → ±15 V → 78L12/79L12 →
**±12 V**. The module alone is unregulated and climbs toward ±17 V at this
board's light load, which is too close to the MPY634's ±18 V absolute maximum
to trust across vendors; the regulators pin the rails and strip the converter's
100 kHz ripple. MPY634 is specified from ±8 V, and the largest signal on the
board is z at 4.8 V, so ±12 V is not tight.

**Speed switching.** No supplier stocks a 3-pole 3-position switch, and the three
integrators have to change together. So 2.2 nF C0G is always fitted and a 6-way
DIP switch adds 100 nF (poles 1–3) or 470 nF (poles 4–6) to all three at once:
2.2 nF fast, 102 nF nice, 472 nF slow. The table is on the silkscreen next to
the switch. This is the part of the design I like least — see the review.

**100 Ω in series with each BNC.** A JFET-input op-amp driving a metre of RG-58
will ring. They sit outside the summing network, so the equations are untouched,
and the error into a 1 MΩ scope input is 0.01%.

### What to look at when you open it

- **Schematic** (A2, one page): three integrator rows the way you stack them,
  multipliers on the left, your `C = 0.47 µF (slow!)…` note in the top-left
  corner, and the owl's face top-right — that trace is the real solution,
  integrated by `scripts/lorenz_curve.py`, not clip art. Supply pins and
  bypassing are grouped in their own dashed box, which is the job your "IC
  Pinouts (DIP)" box was doing.
- **PCB**: 100 × 100 mm, inside the discounted size everywhere. Front silkscreen
  is legends, port labels and the speed table; **turn it over** — the back
  carries the equations, your suggested parameters and a large owl.
- **`docs/DESIGN_REVIEW.md`** — what I think is wrong with it, including four
  router bugs the checks caught that each produce a board that *looks* right.
- **`docs/MANUFACTURING.md`** — what to upload, what to select, what it costs.

### Cost

Parts are **$71.69/board**, of which $61.17 is the pair of MPY634s. Two boards
fully assembled, two layers, including through-hole assembly and DHL: about
**$231**, so roughly $115 each. Five is about $74 each. Four layers adds $23 to
the order. `docs/MANUFACTURING.md` breaks it down and is regenerated from the
same parts table the BOM comes from, so it cannot drift.

### Biggest risk

The BNC footprint is drawn from SAMZO's drawing, not from a connector in my
hand. `out/lorenz/lorenz-assembly-top.pdf` prints 1:1 — please check it against
a real BNC-KYWE before ordering. Everything else on the board is a stock KiCad
footprint or dimensioned from a datasheet I read.

### Pictures

`./make.py` now writes these into `docs/images/` every build, so they cannot
drift from the design.

![The board, front](docs/images/lorenz-render-iso.png)

The back carries the equations, your suggested parameters and the attractor
itself — the trace is the real solution, integrated by `scripts/lorenz_curve.py`:

![The board, back](docs/images/lorenz-render-bottom.png)

[The schematic](docs/images/schematic.png) ·
[front silkscreen](docs/images/lorenz-silk-top.png) ·
[back silkscreen](docs/images/lorenz-silk-bottom.png) ·
[front copper](docs/images/lorenz-top.png) ·
[back copper](docs/images/lorenz-bottom.png) ·
4-layer [ground plane](docs/images/lorenz-4layer-in1-ground.png) and
[+12 V plane](docs/images/lorenz-4layer-in2-power.png)

Every one of these is byte-reproducible except `lorenz-render-iso.png`: KiCad's
renderer jitters a rotated camera, so that one image differs slightly from build
to build even though the board has not changed. Everything a fab reads —
gerbers, drill files, BOM, CPL — is reproducible, with timestamps pinned to the
board date.

Each board also gets a `.step` model (not tracked; it churns) and a
`-stats.txt` in its `out/` folder,
and PDFs of the schematic and both assembly drawings — the top one prints 1:1
for checking footprints against real parts.

### Answering `next_prompt.md`

**Do the schematics differ between 2-layer and 4-layer? Why are there two?**

They do not differ — `lorenz-4layer.kicad_sch` is a byte-for-byte copy that
`make.py` writes from `lorenz.kicad_sch` on every build, so the two cannot
drift apart. It is purely a KiCad requirement: a project is one `.kicad_pro`,
one `.kicad_sch` and one `.kicad_pcb` sharing a basename, and
`kicad-cli pcb drc --schematic-parity` finds the schematic by that basename. No
basename, no parity check — and the parity check is what guarantees the board
you send to the fab really is the circuit that was verified. I kept the copy
tracked rather than generated-only so that either project opens straight from a
clone without running anything first.

The only real differences between the two boards are the stackup and what is
poured on it: two layers puts ground on both sides, four puts signals outside,
a solid ground plane on In1 and a +12 V plane on In2. Same placement, same
schematic, same BOM, same pick-and-place.


## Prompt 2

Build process:

* On a different computer (my laptop), when I run make.py after setting `KICAD_APPRUN`, I get the following, which may indicate that not everything in this git repo is self contained. This should be reproducible by someone who just clones it off of github and types `./make.py`.
```
$ ./make.py 
KiCad 10.0.6

=== self-tests ======================================================
Cannot locate KiCad shared data (symbols/footprints).

BUILD FAILED: selftest_rotation.py failed
```
* Add a `make.py --clean` to remove everything that is generated by make.py. In addition to being good practice, this is useful so that people can know what is generated and what needs to live in git.


Schematics:

* I made a datasheets directory and download some datasheets there. You should make sure they are all downloaded: all parts and connectors and anything else that would be useful. I can get you any that you need. Do not check this into git for copyright reasons.
* Do the schematics differ at all between 2-layer and 4? If not, why are there two different schematics? Is this just a KiCAD requirement? When I have both the schematic and PCB open, I can't seem to click on one to highlight that spot in the other. Do they need to get linked in some way for that to work?
* Two web pages URLs along with QR codes for them should go on the back of the PCB:
 - <https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm>
 - <https://github.com/gallicchio/ai_unleashes_chaos>
* The little table that explains the switch settings could be more clear
* You might have misinterpreted my request which came up in your "One label per signal net" section of your DESIGN_REVIEW.md document. I meant one human-readable comment-type label. The internal KiCAD labels can be whatever they need to be for the best error checking.
* There should be places to attach the ground clips of oscilloscope leads and marked (labeled) test points (places to probe) for all of the DC voltages and the other interesting places to probe in the circuit that you marked in the schematic, like "dx/dt = 10 (y - x)", "-xz/100", and "dy/dt = 28 x - y - x z".
* There should be at least 3 "rails OK" LEDs, one for USB and one for each of the regulated rails. They can be different colors so that one can know at a glance which one is not working. Or they could be all dim white LEDs if you do the following:
* Does it make sense to put LEDs on the x, -y, and z outputs? Or an RGB LED, where each color is driven by one of the outputs to make a chaotic color in "slow" mode? The advantage is that there would be something to look at even if you didn't plug in the BNCs to a scope. A resistor and LED would have a non-linear response, but I'm not sure if anything would be gained by making a proper proportional current drive, and I'm not sure how I'd deal with negative-going signals.
* I'm not familiar with the A0515S-2WR2. If it's truly isolated, as the schematic symbol suggests, would it be a good idea or a bad idea to keep the USB ground separate from what eventually becomes the oscilloscope ground to avoid ground loops? Or would that introduce more problems than it solves? You do acknowledge that "the isolation is not used," whose text you should keep on the schematic if you decide to continue not isolating it.

PCB:

* Does the 4-layer  board buy you anything useful here? Maybe with my pedagogical silkscreen requests, the board size is already going to be large and identical in size to the 2 layer. Is the 4-layer worth it? If it's not worth it, just drop it from the project.
* Should "rails OK" be right next to the LED? Does it really only light if both rails are, in fact, ok?
* The 3D model is missing some parts, especially the DIP switch and the A0515S device that makes +-15 V.
* The PCB should also include the text "Circuit by Paul Horowitz" and the web page, just like the schematic does, not only "PCB by Jason Gallicchio and Claude". Please, that's what he'll see first!
* The table that explains the switch settings could be more clear. At a minimum, the text should be rotated so that the words "off" and "ON" in each column should actually be under the 3 switches that they refer to. Make a silkscreen bar that is drawn coming perpendicular to the DIP switches, in between the columns. Doing this carefully should also solve my second problem with this, table, which is that the label "1-3" is above both columns of the off's and ON's, whereas "4-6" is above the capacitor values... and "fast", "nice", "slow" should be associated with rows of the table.
* The text "MountingHole" and its reference designator does not need to be on the silkscreen.
* The PCB layers in docs/images/ are mostly whitespace. Why aren't these images only as big as the PCB outline?


Misc:

* As part of the build process, generate PDFs and PNGs and 3D renders of the schematic and PCBs and include them here, as you've started to do.
* Continue calling this "rev A" until I actually pay to fabricate a board.
* As you are working, I might be updating next_prompt.md, but don't look at it until I put its content here and tell you to look at it.
