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
**$220**, so roughly $110 each. Five is about $73 each. Four layers adds $23 to
the order.

### Biggest risk

The BNC footprint is drawn from SAMZO's drawing, not from a connector in my
hand. `out/lorenz/lorenz-assembly-top.pdf` prints 1:1 — please check it against
a real BNC-KYWE before ordering. Everything else on the board is a stock KiCad
footprint or dimensioned from a datasheet I read.
