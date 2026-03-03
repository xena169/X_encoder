import openpyxl

def hex_to_excel(input_path, output_path):
    # HEXファイルを読み込む
    with open(input_path, "r") as hex_file:
        hex_lines = hex_file.readlines()

    # Excelワークブックとシートを作成
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hex Data"

    # HEXデータを2文字ずつ区切ってExcelに配置
    for row_idx, line in enumerate(hex_lines, start=1):
        hex_pairs = [line[i:i+2] for i in range(0, len(line.strip()), 2)]  # 2文字ずつ分割
        for col_idx, hex_value in enumerate(hex_pairs, start=1):
            ws.cell(row=row_idx, column=col_idx, value=hex_value)

    # Excelファイルを保存
    wb.save(output_path)
    print(f"Converted HEX file to Excel and saved as {output_path}")

# 例: "input.hex" を "output.xlsx" に変換
hex_to_excel(r"temp\SATQL_TLM_230612_144722_cap.hex", r"2_output_xlsx\SATQL_TLM_230612_144722_cap.xlsx")
hex_to_excel(r"temp\SATQL_TLM_230614_122149_cap.hex", r"2_output_xlsx\SATQL_TLM_230614_122149_cap.xlsx")