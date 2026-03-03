def convert_hex_to_uppercase(input_path, output_path):
    with open(input_path, "r") as hex_file:
        hex_data = hex_file.read()

    # 小文字を大文字に変換
    upper_hex_data = hex_data.upper()

    with open(output_path, "w") as output_file:
        output_file.write(upper_hex_data)

    print(f"Converted hex file saved to {output_path}")

# 例: "input.hex" を整形して "output.hex" に保存
convert_hex_to_uppercase(r"temp\SATQL_TLM_230612_144722_ned.hex", r"temp\SATQL_TLM_230612_144722_cap.hex")
convert_hex_to_uppercase(r"temp\SATQL_TLM_230614_122149_ned.hex", r"temp\SATQL_TLM_230614_122149_cap.hex")