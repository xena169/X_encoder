import re
import openpyxl

def bin_to_hex(input_path):
    # バイナリ → 連続HEX（大文字・スペースなし）
    with open(input_path, "rb") as f:
        return f.read().hex().upper()

def format_hex_file(hex_data):
    # "FAF320" の直前で改行を入れる（複数箇所対応）
    return re.sub(r"FAF320", r"\nFAF320", hex_data)

def hex_to_excel(hex_data, output_path):
    lines = hex_data.splitlines()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hex Data"
    max_cols = 16384

    for r, line in enumerate(lines, start=1):
        # 念のため全ての空白を除去
        cleaned = re.sub(r"\s+", "", line)
        # 偶数桁に揃える（万が一奇数桁なら末尾1文字を捨てる）
        if len(cleaned) % 2 == 1:
            cleaned = cleaned[:-1]

        # 2桁ずつセルへ（各セルは必ず2文字のみ）
        byte_count = min(len(cleaned)//2, max_cols)
        for c in range(byte_count):
            ws.cell(row=r, column=c+1, value=cleaned[2*c:2*c+2])

    wb.save(output_path)
    print(f"Saved: {output_path}")

def process_bin_to_excel(input_path, excel_output_path):
    hex_data = bin_to_hex(input_path)
    formatted = format_hex_file(hex_data)   # 行区切りを付与
    hex_to_excel(formatted, excel_output_path)

# 使用例
process_bin_to_excel(r"STARS-X-log-2025-08-21T03-18-55.bin", r"temp\STARS-X-log-2025-08-21T03-18-55.xlsx")