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
