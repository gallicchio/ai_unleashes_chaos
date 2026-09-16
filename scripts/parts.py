"""Single source of truth for every part: value, footprint, LCSC code, notes.

The BOM, the CPL and the cost estimate are all generated from this table, so
there is exactly one place to change a part.
"""

REV = "A"
BOARD_DATE = "2026-09-15"

# lcsc            : JLCPCB / LCSC order code
# jlc_type        : "basic" | "preferred" | "extended"  (assembly setup fee)
# process         : "SMT" | "THT"
# stock           : stock seen at JLCPCB when the design was frozen
# alt             : drop-in alternates, checked to share the same footprint
PARTS = {
    # ---- the circuit proper -------------------------------------------
    "LF412": dict(
        value="LF412", mpn="LF412CDR", lcsc="C15322", jlc_type="extended",
        process="SMT", stock=1037, price=0.906,
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        desc="Dual JFET-input op-amp (Paul's original part)",
        alt=["TL072CDT / C6961 (JLCPCB Basic, $0.16) - same pinout, "
             "slightly higher bias current"]),
    "MPY634": dict(
        value="MPY634", mpn="MPY634KU/1K", lcsc="C1523457", jlc_type="extended",
        process="SMT", stock=874, price=30.586,
        footprint="Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
        desc="Four-quadrant analog multiplier, W=(X1-X2)(Y1-Y2)/10 (Paul's part)",
        alt=["AD633ARZ / C431243 - identical transfer function but SOIC-8, "
             "needs a different footprint; zero stock at JLCPCB 2026-09-15"]),
    "R_0805": dict(footprint="Resistor_SMD:R_0805_2012Metric", process="SMT"),
    "C_0805": dict(footprint="Capacitor_SMD:C_0805_2012Metric", process="SMT"),
    "C_1206": dict(footprint="Capacitor_SMD:C_1206_3216Metric", process="SMT"),
    "SW_DIP6": dict(
        value="SW_DIP_x06", mpn="DSIC06LSGET", lcsc="C54952", jlc_type="extended",
        process="SMT", stock=2140, price=0.571,
        footprint="lorenz:SW_DIP_SPSTx06_KingTek_DSIC06_P2.54mm",
        desc="6-way SMD DIP switch, 2.54 mm pitch - integrator speed select"),
    "BNC": dict(
        value="BNC", mpn="BNC-KYWE-295-W4-N", lcsc="C41416668", jlc_type="extended",
        process="THT", stock=410, price=1.549,
        footprint="lorenz:BNC_KYWE_RightAngle",
        desc="50 ohm BNC jack, right angle, 4 ground posts on 8x8 mm",
        alt=["HL2-BNC-KYWE / C48606310 (180 in stock)",
             "MLD-BNC-KYWE-L29.5 / C52766468 (67 in stock)"]),
    # ---- power ---------------------------------------------------------
    "USBC": dict(
        value="USB-C", mpn="TYPE-C-31-M-12", lcsc="C165948", jlc_type="extended",
        process="SMT", stock=230097, price=0.186,
        footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        desc="USB-C receptacle, power only (16 pin)"),
    "DCDC": dict(
        value="A0515S-2WR2", mpn="A0515S-2WR2", lcsc="C19272710", jlc_type="extended",
        process="THT", stock=255, price=1.595,
        footprint="lorenz:DCDC_SIP_A05xxS_1W_2W",
        desc="Isolated 5V -> +/-15V 2W DC/DC module",
        alt=["A0515S-2WR2L / C20622616 (233 in stock)",
             "A0515S-1WR3 / C5369388 (920 in stock, 1W) - same footprint and "
             "pinout; 1W is enough for this board's ~20 mA/rail but leaves "
             "less margin"]),
    "REG_POS": dict(
        value="78L12", mpn="CJ78L12", lcsc="C8615", jlc_type="extended",
        process="SMT", stock=52154, price=0.099,
        footprint="Package_TO_SOT_SMD:SOT-89-3",
        desc="+12 V linear regulator (SOT-89: 1=OUT 2=GND 3=IN)"),
    "REG_NEG": dict(
        value="79L12", mpn="CJ79L12", lcsc="C8626", jlc_type="extended",
        process="SMT", stock=11413, price=0.118,
        footprint="Package_TO_SOT_SMD:SOT-89-3",
        desc="-12 V linear regulator (SOT-89: 1=GND 2=IN 3=OUT)"),
    # Three rail lamps, three colours, all three JLCPCB Basic parts so they
    # cost nothing extra to place.  Not red/green: red reads as "fault" when
    # here it means the rail is up, and the RGB output lamp has already spoken
    # for red, green and blue.
    "LED_G": dict(
        value="green", mpn="KT-0805G", lcsc="C2297", jlc_type="basic",
        process="SMT", stock=1542073, price=0.016,
        footprint="LED_SMD:LED_0805_2012Metric",
        desc="+12 V rail lamp"),
    "LED_Y": dict(
        value="yellow", mpn="KT-0805Y", lcsc="C2296", jlc_type="basic",
        process="SMT", stock=526613, price=0.0152,
        footprint="LED_SMD:LED_0805_2012Metric",
        desc="+5 V (USB) rail lamp"),
    "LED_W": dict(
        value="white", mpn="KT-0805W", lcsc="C34499", jlc_type="basic",
        process="SMT", stock=570707, price=0.0198,
        footprint="LED_SMD:LED_0805_2012Metric",
        desc="-12 V rail lamp"),
    "LED_RGB": dict(
        value="RGB", mpn="MHPC3528CRGBCT", lcsc="C2962096", jlc_type="extended",
        process="SMT", stock=3789, price=0.0547,
        footprint="lorenz:LED_RGB_PLCC4_3.5x2.8mm",
        desc="Common-cathode RGB lamp, PLCC-4: red = x, green = -y, blue = z",
        alt=["XL-A3528RGBC-BM / C3647023 (6451 in stock) and "
             "TJ-S3528UG2W9TLCCSRGB-A5 / C20613304 are the same 3528 PLCC-4 "
             "outline; check the pin order before substituting",
             "MHSC110RGBCT / C482558 (10921 in stock) is the same idea in a "
             "3.0 x 1.5 mm package -- smaller than this project wants to "
             "hand-solder"]),
    "TESTPOINT": dict(
        value="", process="THT", in_bom=False,
        footprint="TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm",
        desc="Probe pad: a 0.7 mm plated hole, nothing to buy or place"),
    "SCOPE_GND": dict(
        value="", process="THT", in_bom=False,
        footprint="lorenz:TestPoint_ScopeGnd_Loop_2x1.1mm",
        desc="Two 1.1 mm holes 5.08 mm apart: solder a wire loop through "
             "them and a scope ground clip has something to grab"),
    "JUMPER": dict(
        value="", process="THT", in_bom=False,
        footprint="Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
        desc="Solder jumper, left open: bridge it to tie the two grounds "
             "together and give up the isolation"),
    "FUSE": dict(
        value="500mA", mpn="MF-MSMF050-2", lcsc="C17313", jlc_type="extended",
        process="SMT", stock=142624, price=0.068,
        footprint="lorenz:PTC_1812_4532Metric",
        desc="Resettable PTC on the USB input"),
}

# Resistor and capacitor order codes, keyed by value.
PASSIVES = {
    "100k":  dict(lcsc="C149504", mpn="0805W8F1003T5E", jlc_type="basic",
                  price=0.006, stock=4893299),
    "35.7k": dict(lcsc="C843989", mpn="CRCW080535K7FKEA", jlc_type="extended",
                  price=0.015, stock=2783),
    "10k":   dict(lcsc="C17414", mpn="0805W8F1002T5E", jlc_type="basic",
                  price=0.004, stock=53835303),
    "1M":    dict(lcsc="C17514", mpn="0805W8F1004T5E", jlc_type="basic",
                  price=0.005, stock=2688974),
    "374k":  dict(lcsc="C2933427", mpn="FRC0805F3743TS", jlc_type="extended",
                  price=0.004, stock=18582),
    "100R":  dict(lcsc="C17408", mpn="0805W8F1000T5E", jlc_type="basic",
                  price=0.004, stock=10085527),
    "5.1k":  dict(lcsc="C27834", mpn="0805W8F5101T5E", jlc_type="basic",
                  price=0.006, stock=3917491),
    "4.7k":  dict(lcsc="C17673", mpn="0805W8F4701T5E", jlc_type="basic",
                  price=0.005, stock=5973538),
    "2.2k":  dict(lcsc="C17520", mpn="0805W8F2201T5E", jlc_type="basic",
                  price=0.0027, stock=3751757),
    "1.5k":  dict(lcsc="C4310", mpn="0805W8F1501T5E", jlc_type="basic",
                  price=0.0015, stock=585325),
    "33k":   dict(lcsc="C17633", mpn="0805W8F3302T5E", jlc_type="basic",
                  price=0.0028, stock=570100),
    "6.8k":  dict(lcsc="C17772", mpn="0805W8F6801T5E", jlc_type="basic",
                  price=0.0042, stock=382071),
    "2.2nF": dict(lcsc="C28260", mpn="CL21C222JBFNNNE", jlc_type="basic",
                  price=0.028, stock=179637, note="C0G/NP0 50V"),
    "100nF_C0G": dict(lcsc="C170182", mpn="1206N104J500CT", jlc_type="extended",
                      price=0.187, stock=193311, note="C0G/NP0 50V, 1206"),
    "470nF": dict(lcsc="C277483", mpn="CC1206KKX7R9BB474", jlc_type="extended",
                  price=0.032, stock=190079, note="X7R 50V, 1206"),
    "100nF": dict(lcsc="C49678", mpn="CC0805KRX7R9BB104", jlc_type="basic",
                  price=0.019, stock=18183154, note="X7R 50V, 0805 - bypass"),
    "10uF":  dict(lcsc="C15850", mpn="CL21A106KAYNNNE", jlc_type="basic",
                  price=0.084, stock=6702077, note="X5R 25V, 0805 - bulk"),
}
