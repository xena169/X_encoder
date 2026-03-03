def format_hex_file(input_path, output_path):
    with open(input_path, "r") as hex_file:
        hex_data = hex_file.read()

    # "320" の直後に改行を追加
    formatted_data = hex_data.replace("faf320", "\nfaf320")

    with open(output_path, "w") as output_file:
        output_file.write(formatted_data)

    print(f"Formatted hex file saved to {output_path}")

# 例: "input.hex" を整形して "output.hex" に保存
format_hex_file(r"temp\SATQL_TLM_230612_144722.hex", r"temp\SATQL_TLM_230612_144722_ned.hex")
format_hex_file(r"temp\SATQL_TLM_230614_122149.hex", r"temp\SATQL_TLM_230614_122149_ned.hex")