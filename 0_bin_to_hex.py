def binary_to_hex(file_path, output_path):
    with open(file_path, "rb") as bin_file:
        binary_data = bin_file.read()
    
    hex_data = binary_data.hex()
    
    with open(output_path, "w") as hex_file:
        hex_file.write(hex_data)
    
    print(f"Converted binary file to hex and saved to {output_path}")

# 例: "input.bin" を "output.hex" に変換
binary_to_hex(r"1_input_bin\SATQL_TLM_230612_144722.qltlm", r"temp\SATQL_TLM_230612_144722.hex")
binary_to_hex(r"1_input_bin\SATQL_TLM_230614_122149.qltlm", r"temp\SATQL_TLM_230614_122149.hex")