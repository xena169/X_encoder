import argparse
import csv
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MARKER = bytes.fromhex("FAF320")
ROW_LEN = 138
FRAME_COL_INDEX = 3  # c004 in marker-aligned test rows
VALUE_COL_INDEX = 10  # c011 in marker-aligned test rows
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


def split_records_with_marker(binary: bytes) -> list[bytes]:
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
        rec_start = marker_pos
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


def write_test_rows_csv(rows: list[list[int | None]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["row"] + [f"c{i:03d}" for i in range(1, ROW_LEN + 1)]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(rows, start=1):
            out = {"row": idx}
            for col_i, v in enumerate(row, start=1):
                out[f"c{col_i:03d}"] = "" if v is None else f"{v:02X}"
            writer.writerow(out)


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
        "input_files",
        nargs="*",
        type=Path,
        default=[],
        help="Input .bin/.qltlm file(s). If omitted, auto-detect from --input-dir.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory scanned when input_files are omitted (default: input)",
    )
    parser.add_argument("-o", "--output-csv", type=Path, default=Path("output/encoder_values.csv"))
    parser.add_argument("--plot-dir", type=Path, default=Path("output/plots"))
    parser.add_argument(
        "--test-csv",
        type=Path,
        default=Path("output/test_rows.csv"),
        help="Test CSV path for marker-aligned rows (default: output/test_rows.csv)",
    )
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


def resolve_input_files(input_files: list[Path], input_dir: Path) -> list[Path]:
    if input_files:
        return input_files

    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    candidates = sorted(list(input_dir.glob("*.bin")) + list(input_dir.glob("*.qltlm")))
    if not candidates:
        raise FileNotFoundError(f"No .bin/.qltlm found in {input_dir}")
    return candidates


def csv_path_for_file(
    base_output_csv: Path, input_file: Path, multiple_inputs: bool, output_csv_specified: bool
) -> Path:
    if not multiple_inputs:
        return base_output_csv
    if output_csv_specified and base_output_csv.suffix.lower() != ".csv":
        return base_output_csv / f"{input_file.stem}.csv"
    if output_csv_specified and base_output_csv.suffix.lower() == ".csv":
        return base_output_csv.parent / f"{base_output_csv.stem}_{input_file.stem}.csv"
    return Path("output") / f"{input_file.stem}.csv"


def plot_dir_for_file(
    base_plot_dir: Path, input_file: Path, multiple_inputs: bool, plot_dir_specified: bool
) -> Path:
    if not multiple_inputs:
        return base_plot_dir
    if plot_dir_specified:
        return base_plot_dir / input_file.stem
    return Path("output/plots") / input_file.stem


def test_csv_path_for_file(base_test_csv: Path, input_file: Path, multiple_inputs: bool) -> Path:
    if not multiple_inputs:
        return base_test_csv
    if base_test_csv.suffix.lower() == ".csv":
        return base_test_csv.parent / f"{base_test_csv.stem}_{input_file.stem}.csv"
    return base_test_csv / f"{input_file.stem}.csv"


def process_one_file(
    input_file: Path, x_unit: str, output_csv: Path, plot_dir: Path, test_csv: Path
) -> tuple[int, int, int]:
    binary = input_file.read_bytes()

    # Test dump: split right before marker so each row starts with FA F3 20.
    test_records = split_records_with_marker(binary)
    test_rows = records_to_rows(test_records)
    write_test_rows_csv(test_rows, test_csv)

    records = split_records_with_marker(binary)
    rows = records_to_rows(records)
    windows = extract_time_windows(rows)
    output_rows = build_output_rows(windows)

    write_csv(output_rows, output_csv)
    plot_axis(output_rows, x_unit=x_unit, plot_dir=plot_dir)
    return len(records), len(windows), len(output_rows)


def main() -> None:
    args = parse_args()
    output_csv_specified = any(a in {"-o", "--output-csv"} for a in sys.argv[1:])
    plot_dir_specified = any(a == "--plot-dir" for a in sys.argv[1:])
    input_files = resolve_input_files(args.input_files, args.input_dir)
    multiple_inputs = len(input_files) > 1

    x_unit = args.x_unit if args.x_unit else ask_x_unit()

    for input_file in input_files:
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        if input_file.suffix.lower() not in {".bin", ".qltlm"}:
            print(f"Warning: extension is not .bin/.qltlm, but processing continues: {input_file}")

        output_csv = csv_path_for_file(args.output_csv, input_file, multiple_inputs, output_csv_specified)
        plot_dir = plot_dir_for_file(args.plot_dir, input_file, multiple_inputs, plot_dir_specified)
        test_csv = test_csv_path_for_file(args.test_csv, input_file, multiple_inputs)
        rec_n, win_n, row_n = process_one_file(input_file, x_unit, output_csv, plot_dir, test_csv)

        print(f"Input: {input_file}")
        print(f"records: {rec_n}")
        print(f"time windows: {win_n}")
        print(f"csv rows: {row_n}")
        print(f"CSV: {output_csv}")
        print(f"Plots: {plot_dir}")
        print(f"Test CSV: {test_csv}")


if __name__ == "__main__":
    main()


