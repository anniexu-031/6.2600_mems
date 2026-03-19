"""
mems_wafer_layout.py
--------------------
Tiles the MEMS parameter-sweep chip across a 150 mm wafer.

Two chip variants are placed in a checkerboard pattern:
  - Variant A: 10 µm electrode height  (original)
  - Variant B:  5 µm electrode height  (new)

Chips are spaced 2 mm apart (centre-to-centre = chip_size + 2 mm) to
allow cleaving.  Only chips whose four corners all fall within the
wafer circle are placed.

Layers used
-----------
  1  structural geometry (from base layout)
  2  contact geometry    (from base layout)
  3  text labels         (from base layout)
  11 cell outlines       (from base layout)
  20 wafer outline
"""

from phidl import Device
import phidl.geometry as pg
import numpy as np

import mems_parameter_sweep_layout as base   # renamed module (was mems_parameter_sweep_layout)


# ── Constants ──────────────────────────────────────────────────────────────────
WAFER_DIAMETER_UM  = 150_000   # 150 mm
CHIP_GAP_UM        = 2_000     # 2 mm cleaving margin
WAFER_LAYER        = 20
MASK_LAYER         = 1
ELECTRODE_HEIGHTS  = (10, 5)   # variant A, variant B
# ───────────────────────────────────────────────────────────────────────────────


def build_chip(electrode_height: int) -> Device:
    """
    Build the full parameter-sweep chip (cantilever + clamped-clamped
    sections + line-gradient characterization structures) with the
    specified electrode height for both resonator families.
    """
    mc = base.build_parameter_object()
    mc.cant_electrode_height = electrode_height
    mc.cc_electrode_height   = electrode_height

    chip = Device(f"mems_chip_elec{electrode_height}um")

    row_count     = len(mc.widths) * len(mc.gaps)
    section_width = mc.grid_origin_x + len(mc.lengths) * mc.cell_pitch_x
    section_height = mc.grid_origin_y + row_count * mc.cell_pitch_y

    cant_origin = (mc.master_margin, mc.master_margin + 200)
    cc_origin   = (cant_origin[0] + section_width + mc.family_gap_x, cant_origin[1])

    base.add_section_label(chip, "Cantilever Sweep",
                           (cant_origin[0], mc.master_margin), mc.section_label_size)
    base.add_section_label(chip, "Clamped-Clamped Sweep",
                           (cc_origin[0],   mc.master_margin), mc.section_label_size)

    base.place_parameter_grid(chip, cant_origin, mc.lengths, mc.widths, mc.gaps,
                              base.cantilever_cell, "cantilever_section", mc)
    base.place_parameter_grid(chip, cc_origin,   mc.lengths, mc.widths, mc.gaps,
                              base.clamped_clamped_cell, "clamped_clamped_section", mc)

    # Grating characterisation structures — placed below the MEMS sections
    grating_origin = (
        cant_origin[0],
        cant_origin[1] + section_height + mc.master_margin,
    )
    base.place_grating_section(chip, grating_origin, mc)

    return chip


def fits_in_wafer(cx: float, cy: float,
                  half_w: float, half_h: float,
                  wafer_radius: float) -> bool:
    """Return True if all four chip corners lie within the wafer circle."""
    corners = [
        (cx - half_w, cy - half_h),
        (cx + half_w, cy - half_h),
        (cx + half_w, cy + half_h),
        (cx - half_w, cy + half_h),
    ]
    return all(x ** 2 + y ** 2 <= wafer_radius ** 2 for x, y in corners)


def invert_chip(source: Device, border: int = 200, output_layer: int = MASK_LAYER) -> Device:
    """
    Invert a single chip: subtract its geometry from a background rectangle,
    exactly as in the original invert_layout() approach.
    """
    mask_source = pg.extract(source, layers=[1, 2, 3])
    xmin, ymin = mask_source.xmin, mask_source.ymin
    xmax, ymax = mask_source.xmax, mask_source.ymax

    background = Device("mask_background")
    background << pg.rectangle(
        size=(xmax - xmin + 2 * border, ymax - ymin + 2 * border),
        layer=output_layer,
    ).move((xmin - border, ymin - border))

    inverted = pg.boolean(
        A=background,
        B=mask_source,
        operation="A-B",
        precision=1e-6,
        layer=output_layer,
    )

    chip_inv = Device(source.name + "_inverted")
    chip_inv << inverted
    return chip_inv


def tile_wafer() -> Device:
    """
    Place inverted chip variants on a 150 mm wafer in a checkerboard
    arrangement and return the assembled Device.
    """
    wafer_radius = WAFER_DIAMETER_UM / 2

    # Build and invert both chip variants once; tiled instances share these cells
    raw_variants = [build_chip(h) for h in ELECTRODE_HEIGHTS]
    variants = [invert_chip(v) for v in raw_variants]

    # Use the first variant's bounding box (both are identical in size)
    chip_w = variants[0].xsize
    chip_h = variants[0].ysize
    half_w, half_h = chip_w / 2, chip_h / 2

    pitch_x = chip_w + CHIP_GAP_UM
    pitch_y = chip_h + CHIP_GAP_UM

    # Grid extent needed to cover the wafer
    n_cols = int(np.ceil(wafer_radius / pitch_x)) + 1
    n_rows = int(np.ceil(wafer_radius / pitch_y)) + 1

    wafer = Device("wafer_150mm_mems_layout")

    # Wafer outline (layer 20)
    wafer << pg.circle(radius=wafer_radius, layer=WAFER_LAYER)

    counts = {h: 0 for h in ELECTRODE_HEIGHTS}

    for row in range(-n_rows, n_rows + 1):
        for col in range(-n_cols, n_cols + 1):
            cx = col * pitch_x
            cy = row * pitch_y

            if not fits_in_wafer(cx, cy, half_w, half_h, wafer_radius):
                continue

            # Checkerboard: even (row+col) → variant A, odd → variant B
            variant_idx = (row + col) % 2
            chip = variants[variant_idx]
            elec_h = ELECTRODE_HEIGHTS[variant_idx]

            ref = wafer << chip
            # Place so chip centre lands at (cx, cy)
            ref.move((cx - half_w, cy - half_h))
            counts[elec_h] += 1

    total = sum(counts.values())
    print(f"Wafer tiling complete:")
    print(f"  Chip size      : {chip_w/1000:.2f} mm × {chip_h/1000:.2f} mm")
    print(f"  Chip pitch     : {pitch_x/1000:.2f} mm × {pitch_y/1000:.2f} mm")
    for h, n in counts.items():
        print(f"  {h:2d} µm electrodes : {n} chips")
    print(f"  Total          : {total} chips")

    return wafer


def main():
    wafer = tile_wafer()
    output_gds = "mems_wafer_150mm_inverted.gds"
    wafer.write_gds(output_gds)
    print(f"\nWrote {output_gds}")


if __name__ == "__main__":
    main()