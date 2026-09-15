#!/usr/bin/env python3
"""Write the KiCad project file and the two library tables.

Design rules are deliberately tighter than the cheapest tier at JLCPCB,
NextPCB and CircuitHub, so a board that passes DRC here passes everywhere:

                        JLCPCB    NextPCB   CircuitHub   used here
  min track / space     0.127     0.127     0.152        0.200
  min via pad / drill   0.45/0.3  0.45/0.3  0.60/0.30    0.60/0.30
  min annular ring      0.13      0.13      0.15         0.25
  min hole to hole      0.50      0.50      0.50         0.50
  copper to board edge  0.20      0.20      0.25         0.30
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(HERE, "..", "hardware")

TRACK_MIN = 0.2
CLEARANCE = 0.2
VIA_DIA, VIA_DRILL = 0.6, 0.3

NET_CLASSES = [
    {"name": "Default", "clearance": CLEARANCE, "track_width": 0.25,
     "via_diameter": VIA_DIA, "via_drill": VIA_DRILL,
     "microvia_diameter": 0.3, "microvia_drill": 0.1,
     "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
     "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
     "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6, "bus_width": 12,
     "priority": 2147483647},
    {"name": "Power", "clearance": CLEARANCE, "track_width": 0.6,
     "via_diameter": 0.8, "via_drill": 0.4,
     "microvia_diameter": 0.3, "microvia_drill": 0.1,
     "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
     "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
     "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6, "bus_width": 12,
     "priority": 1},
]

POWER_NETS = ["GND", "+5V", "+12V", "-12V", "+15V", "-15V", "VBUS"]


def design_rules():
    return {
        "max_error": 0.005,
        "min_clearance": CLEARANCE,
        "min_connection": TRACK_MIN,
        "min_copper_edge_clearance": 0.3,
        "min_groove_width": 0.0,
        "min_hole_clearance": 0.3,
        "min_hole_to_hole": 0.5,
        "min_microvia_diameter": 0.2,
        "min_microvia_drill": 0.1,
        "min_resolved_spokes": 2,
        "min_silk_clearance": 0.15,
        "min_text_height": 0.8,
        "min_text_thickness": 0.15,
        "min_through_hole_diameter": 0.3,
        "min_track_width": TRACK_MIN,
        "min_via_annular_width": 0.25,
        "min_via_diameter": VIA_DIA,
        "solder_mask_clearance": 0.0,
        "solder_mask_min_width": 0.0,
        "solder_mask_to_copper_clearance": 0.0,
        "use_height_for_length_calcs": True,
    }


def severities():
    """Everything that could reach the fab as a defect is an error."""
    err = ["copper_edge_clearance", "copper_sliver", "courtyards_overlap",
           "drill_out_of_range", "duplicate_footprints", "footprint",
           "footprint_symbol_mismatch", "hole_clearance", "hole_near_hole",
           "invalid_outline", "isolated_copper", "item_on_disabled_layer",
           "lib_footprint_issues", "lib_footprint_mismatch", "malformed_courtyard",
           "microvia_drill_out_of_range", "missing_courtyard", "missing_footprint",
           "npth_inside_courtyard", "padstack", "pth_inside_courtyard",
           "shorting_items", "silk_over_copper", "silk_overlap",
           "solder_mask_bridge", "starved_thermal", "text_height",
           "text_thickness", "through_hole_pad_without_hole", "too_many_vias",
           "track_dangling", "track_width", "unconnected_items", "via_dangling",
           "zones_intersect"]
    warn = ["assertion_failure", "diff_pair_gap_out_of_range",
            "diff_pair_uncoupled_length_too_long", "footprint_filters_mismatch",
            "footprint_type_mismatch", "length_out_of_range",
            "mirrored_text_on_front_layer", "nonmirrored_text_on_back_layer",
            "skew_out_of_range", "track_angle", "track_segment_length",
            "connection_width"]
    out = {k: "error" for k in err}
    out.update({k: "warning" for k in warn})
    out["silk_over_copper"] = "warning"   # pads under silk are usual on connectors
    return out


def project(board_stem):
    return {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5, "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "courtyard_line_width": 0.05,
                    "dimension_precision": 4, "dimension_units": 3,
                    "fab_line_width": 0.1,
                    "fab_text_size_h": 1.0, "fab_text_size_v": 1.0,
                    "fab_text_thickness": 0.15,
                    "other_line_width": 0.15,
                    "other_text_size_h": 1.0, "other_text_size_v": 1.0,
                    "other_text_thickness": 0.15,
                    "silk_line_width": 0.15,
                    "silk_text_size_h": 1.0, "silk_text_size_v": 1.0,
                    "silk_text_thickness": 0.15,
                    "zones": {"min_clearance": 0.25},
                },
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rule_severities": severities(),
                "rules": design_rules(),
                "track_widths": [0.0, 0.25, 0.4, 0.6, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": VIA_DIA, "drill": VIA_DRILL},
                                   {"diameter": 0.8, "drill": 0.4}],
                "zones_allow_external_fillets": False,
            },
            "layer_presets": [], "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {
            "erc_exclusions": [],
            "meta": {"version": 0},
            "pin_map": [],
            "rule_severities": {
                "bus_definition_conflict": "error",
                "bus_entry_needed": "error",
                "bus_to_bus_conflict": "error",
                "bus_to_net_conflict": "error",
                "conflicting_netclasses": "error",
                "different_unit_footprint": "error",
                "different_unit_net": "error",
                "duplicate_reference": "error",
                "duplicate_sheet_names": "error",
                "endpoint_off_grid": "error",
                "extra_units": "error",
                "footprint_link_issues": "error",
                "global_label_dangling": "warning",
                "hier_label_mismatch": "error",
                "label_dangling": "error",
                "lib_symbol_issues": "error",
                "missing_bidi_pin": "warning",
                "missing_input_pin": "warning",
                "missing_power_pin": "error",
                "missing_unit": "warning",
                "multiple_net_names": "warning",
                "net_not_bus_member": "warning",
                "no_connect_connected": "error",
                "no_connect_dangling": "warning",
                "pin_not_connected": "error",
                "pin_not_driven": "error",
                "pin_to_pin": "error",
                "power_pin_not_driven": "error",
                "similar_label_and_power": "warning",
                "similar_labels": "warning",
                "simulation_model_issue": "ignore",
                "single_global_label": "ignore",
                "unannotated": "error",
                "unconnected_wire_endpoint": "error",
                "unresolved_variable": "error",
                "wire_dangling": "error",
            },
        },
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": board_stem + ".kicad_pro", "version": 3},
        "net_settings": {
            "classes": NET_CLASSES,
            "meta": {"version": 4},
            "net_colors": None,
            "netclass_assignments": {n: ["Power"] for n in POWER_NETS},
            "netclass_patterns": [],
        },
        "pcbnew": {
            "last_paths": {"gencad": "", "idf": "", "netlist": "",
                           "plot": "", "pos_files": "", "specctra_dsn": "",
                           "step": "", "svg": "", "vrml": ""},
            "page_layout_descr_file": "",
        },
        "schematic": {
            "annotate_start_num": 0,
            "bom_fmt_presets": [], "bom_fmt_settings": {},
            "bom_presets": [], "bom_settings": {},
            "connection_grid_size": 50.0,
            "drawing": {
                "dashed_lines_dash_length_ratio": 12.0,
                "dashed_lines_gap_length_ratio": 3.0,
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "field_names": [],
                "intersheets_ref_own_page": False,
                "intersheets_ref_prefix": "",
                "intersheets_ref_short": False,
                "intersheets_ref_show": False,
                "intersheets_ref_suffix": "",
                "junction_size_choice": 3,
                "label_size_ratio": 0.375,
                "operating_point_overlay_i_precision": 3,
                "operating_point_overlay_i_range": "~A",
                "operating_point_overlay_v_precision": 3,
                "operating_point_overlay_v_range": "~V",
                "overbar_offset_ratio": 1.23,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15,
            },
            "legacy_lib_dir": "", "legacy_lib_list": [],
            "meta": {"version": 1},
            "net_format_name": "",
            "page_layout_descr_file": "",
            "plot_directory": "../out/",
            "space_save_all_events": True,
            "spice_current_sheet_as_root": False,
            "spice_external_command": 'spice "%I"',
            "spice_model_current_sheet_as_root": True,
            "spice_save_all_currents": False,
            "spice_save_all_dissipations": False,
            "spice_save_all_voltages": False,
            "subpart_first_id": 65,
            "subpart_id_separator": 0,
        },
        "sheets": [], "text_variables": {},
    }


SYM_LIB_TABLE = """(sym_lib_table
  (version 7)
  (lib (name "lorenz")(type "KiCad")(uri "${KIPRJMOD}/lib/lorenz.kicad_sym")(options "")(descr "Symbols drawn for this project"))
)
"""

FP_LIB_TABLE = """(fp_lib_table
  (version 7)
  (lib (name "lorenz")(type "KiCad")(uri "${KIPRJMOD}/lib/lorenz.pretty")(options "")(descr "Footprints drawn for this project"))
)
"""


def main():
    os.makedirs(HW, exist_ok=True)
    for stem in ("lorenz", "lorenz-4layer"):
        path = os.path.join(HW, stem + ".kicad_pro")
        with open(path, "w") as fh:
            json.dump(project(stem), fh, indent=2)
            fh.write("\n")
        print(f"  wrote {os.path.relpath(path)}")
    for name, body in (("sym-lib-table", SYM_LIB_TABLE),
                       ("fp-lib-table", FP_LIB_TABLE)):
        path = os.path.join(HW, name)
        with open(path, "w") as fh:
            fh.write(body)
        print(f"  wrote {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
