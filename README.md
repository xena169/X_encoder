# X_encoder

## 4_enc.py

`4_enc.py` は、`.bin` / `.qltlm` のバイナリログからエンコーダ値（`encX`, `encY`, `encZ`）を抽出し、CSVとグラフを出力するスクリプトです。

## 要件

- Python 3.10+
- matplotlib

インストール例:

```powershell
pip install matplotlib
```

## デフォルトのディレクトリ運用

- 入力ディレクトリ: `input/`
- 出力ディレクトリ: `output/`
- CSV既定: `output/encoder_values.csv`
- グラフ既定: `output/plots/encX.png`, `encY.png`, `encZ.png`

オプションなしで実行した場合は、`input/` 内の `.bin` / `.qltlm` を自動検索します。

- 1ファイルだけある場合: そのファイルを処理
- 0ファイル: エラー
- 2ファイル以上: エラー（入力ファイルを明示）

## 実行方法

```powershell
python 4_enc.py [input_file] [options]
```

例:

```powershell
# input/ 内の単一 .bin/.qltlm を自動使用
python 4_enc.py

# ファイルを明示
python 4_enc.py input/sample.bin

# 横軸を分で表示
python 4_enc.py --x-unit min

# 出力先を変更
python 4_enc.py input/sample.bin -o output/my_encoder.csv --plot-dir output/my_plots
```

### オプション

- `--input-dir` : `input_file` 省略時に検索するディレクトリ（既定: `input`）
- `-o, --output-csv` : 出力CSVパス（既定: `output/encoder_values.csv`）
- `--plot-dir` : グラフ出力ディレクトリ（既定: `output/plots`）
- `--x-unit {sec,min}` : 横軸単位（未指定時は実行時に入力）

## 入力/処理仕様（要点）

1. マーカー `FA F3 20` でレコード分割
2. 1レコードを138列固定行に変換（不足は欠損）
3. 14列目（N列）を Frame ID、24列目（X列）を Value Byte として使用
4. Frame ID が連続する8行を1時間枠として抽出
5. `frame_id % 32` でキー化して X/Y/Z の上下位バイトを判定
6. 上位行の直後が下位行かつ Frame ID `+1` のときのみ結合
7. 2バイト値を signed int16 として解釈し `/512` で物理値化

## 出力

### CSV

- カラム: `time, encX, encY, encZ`
- `encX/encY/encZ` が全て欠損の枠は出力しない
- 欠損値は空欄で出力

### グラフ

- `encX.png`, `encY.png`, `encZ.png` を `--plot-dir` に保存
- 縦軸: 物理値
- 横軸: `time`（`sec`）または `time/60`（`min`）
