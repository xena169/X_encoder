import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MARKER = bytes.fromhex("FAF320")
ROW_LEN = 138
FRAME_COL_INDEX = 13  # 14th column (N)
VALUE_COL_INDEX = 23  # 24th column (X)
DEFAULT_INPUT_DIR = Path("input")

PAIR_DEFINITIONS = {
    "X1": (0x00, 0x01),
    "X2": (0x10, 0x11),
    "Y1": (0x02, 0x03),
    "Y2": (0x12, 0x13),
    "Z1": (0x04, 0x05),
    "Z2": (0x14, 0x15),
}


def split_records(binary: bytes) -> list[bytes]:
    marker_positions = []
    start = 0
    while True:
        idx = binary.find(MARKER, start)
        if idx == -1:
            break
        marker_positions.append(idx)
        start = idx + 1

    records = []
    for i, marker_pos in enumerate(marker_positions):
        rec_start = marker_pos + len(MARKER)
        rec_end = marker_positions[i + 1] if i + 1 < len(marker_positions) else len(binary)
        records.append(binary[rec_start:rec_end])
    return records


def records_to_rows(records: list[bytes]) -> list[list[int | None]]:
    rows = []
    for rec in records:
        row = [None] * ROW_LEN
        for i, b in enumerate(rec[:ROW_LEN]):
            row[i] = b
        rows.append(row)
    return rows


def get_frame_id(row: list[int | None]) -> int | None:
    return row[FRAME_COL_INDEX]


def get_value_byte(row: list[int | None]) -> int | None:
    return row[VALUE_COL_INDEX]


def frame_key(frame_id: int) -> int:
    return frame_id % 32


def extract_time_windows(rows: list[list[int | None]]) -> list[list[list[int | None]]]:
    windows = []
    i = 0
    while i <= len(rows) - 8:
        candidate = rows[i : i + 8]
        frame_ids = [get_frame_id(r) for r in candidate]
        if any(fid is None for fid in frame_ids):
            i += 1
            continue

        ok = True
        for j in range(7):
            if frame_ids[j + 1] != ((frame_ids[j] + 1) & 0xFF):
                ok = False
                break

        if ok:
            windows.append(candidate)
            i += 8
        else:
            i += 1

    return windows


def combine_big_endian_signed16(upper: int, lower: int) -> float:
    raw = (upper << 8) | lower
    if raw >= 0x8000:
        raw -= 0x10000
    return raw / 512.0


def find_pair_value(window: list[list[int | None]], pair_name: str) -> float:
    high_key, low_key = PAIR_DEFINITIONS[pair_name]
    candidates = []

    for i in range(len(window) - 1):
        r_hi = window[i]
        r_lo = window[i + 1]

        fid_hi = get_frame_id(r_hi)
        fid_lo = get_frame_id(r_lo)
        if fid_hi is None or fid_lo is None:
            continue

        if frame_key(fid_hi) != high_key or frame_key(fid_lo) != low_key:
            continue

        if fid_lo != ((fid_hi + 1) & 0xFF):
            continue

        val_hi = get_value_byte(r_hi)
        val_lo = get_value_byte(r_lo)
        if val_hi is None or val_lo is None:
            continue

        candidates.append(combine_big_endian_signed16(val_hi, val_lo))

    if len(candidates) == 1:
        return candidates[0]
    return math.nan


def choose_axis_value(v1: float, v2: float) -> float:
    valid = [v for v in (v1, v2) if not math.isnan(v)]
    if len(valid) == 1:
        return valid[0]
    return math.nan


def build_output_rows(windows: list[list[list[int | None]]]) -> list[dict[str, float | int]]:
    output_rows = []
    for t, window in enumerate(windows, start=1):
        x1 = find_pair_value(window, "X1")
        x2 = find_pair_value(window, "X2")
        y1 = find_pair_value(window, "Y1")
        y2 = find_pair_value(window, "Y2")
        z1 = find_pair_value(window, "Z1")
        z2 = find_pair_value(window, "Z2")

        enc_x = choose_axis_value(x1, x2)
        enc_y = choose_axis_value(y1, y2)
        enc_z = choose_axis_value(z1, z2)

        if all(math.isnan(v) for v in (enc_x, enc_y, enc_z)):
            continue

        output_rows.append({"time": t, "encX": enc_x, "encY": enc_y, "encZ": enc_z})

    return output_rows


def write_csv(output_rows: list[dict[str, float | int]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "encX", "encY", "encZ"])
        writer.writeheader()
        for row in output_rows:
            writer.writerow(
                {
                    "time": row["time"],
                    "encX": "" if math.isnan(row["encX"]) else row["encX"],
                    "encY": "" if math.isnan(row["encY"]) else row["encY"],
                    "encZ": "" if math.isnan(row["encZ"]) else row["encZ"],
                }
            )


def plot_axis(output_rows: list[dict[str, float | int]], x_unit: str, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)

    x_vals = [r["time"] for r in output_rows]
    if x_unit == "min":
        x_vals = [t / 60.0 for t in x_vals]
        x_label = "time [min]"
    else:
        x_label = "time [s]"

    for axis in ("encX", "encY", "encZ"):
        y_vals = [r[axis] for r in output_rows]
        y_plot = [math.nan if math.isnan(v) else v for v in y_vals]

        plt.figure(figsize=(10, 4))
        plt.plot(x_vals, y_plot, marker="o", linestyle="-")
        plt.title(f"{axis} vs time")
        plt.xlabel(x_label)
        plt.ylabel("physical value")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(plot_dir / f"{axis}.png", dpi=150)
        plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract encX/encY/encZ from binary log and output CSV/plots."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        default=None,
        help="Input .bin/.qltlm file. If omitted, auto-detect from --input-dir.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory scanned when input_file is omitted (default: input)",
    )
    parser.add_argument("-o", "--output-csv", type=Path, default=Path("output/encoder_values.csv"))
    parser.add_argument("--plot-dir", type=Path, default=Path("output/plots"))
    parser.add_argument(
        "--x-unit",
        choices=["sec", "min"],
        help="X axis unit. If omitted, asks interactively (sec/min).",
    )
    return parser.parse_args()


def ask_x_unit() -> str:
    while True:
        ans = input("Select x-axis unit [sec/min]: ").strip().lower()
        if ans in {"sec", "min"}:
            return ans
        print("Please input 'sec' or 'min'.")


def resolve_input_file(input_file: Path | None, input_dir: Path) -> Path:
    if input_file is not None:
        return input_file

    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    candidates = sorted(list(input_dir.glob("*.bin")) + list(input_dir.glob("*.qltlm")))
    if not candidates:
        raise FileNotFoundError(f"No .bin/.qltlm found in {input_dir}")
    if len(candidates) > 1:
        raise RuntimeError(
            "Multiple input files found. Specify one explicitly, e.g. "
            "python 4_enc.py input/sample.bin"
        )
    return candidates[0]


def main() -> None:
    args = parse_args()
    input_file = resolve_input_file(args.input_file, args.input_dir)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if input_file.suffix.lower() not in {".bin", ".qltlm"}:
        print("Warning: extension is not .bin/.qltlm, but processing continues.")

    x_unit = args.x_unit if args.x_unit else ask_x_unit()

    binary = input_file.read_bytes()
    records = split_records(binary)
    rows = records_to_rows(records)
    windows = extract_time_windows(rows)
    output_rows = build_output_rows(windows)

    write_csv(output_rows, args.output_csv)
    plot_axis(output_rows, x_unit=x_unit, plot_dir=args.plot_dir)

    print(f"Input: {input_file}")
    print(f"records: {len(records)}")
    print(f"time windows: {len(windows)}")
    print(f"csv rows: {len(output_rows)}")
    print(f"CSV: {args.output_csv}")
    print(f"Plots: {args.plot_dir}")


if __name__ == "__main__":
    main()
