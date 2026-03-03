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

オプションなしで実行した場合は、`input/` 内の `.bin` / `.qltlm` を全件検索して、各ファイルを順番に処理します。

- 0ファイル: エラー
- 1ファイル以上: すべて処理

## 実行方法

```powershell
python 4_enc.py [input_files ...] [options]
```

例:

```powershell
# input/ 内の .bin/.qltlm を全件処理
python 4_enc.py

# 複数ファイルを明示
python 4_enc.py input/a.bin input/b.qltlm

# 横軸を分で表示
python 4_enc.py --x-unit min
```

### オプション

- `--input-dir` : `input_files` 省略時に検索するディレクトリ（既定: `input`）
- `-o, --output-csv` : 出力CSVパス（既定: `output/encoder_values.csv`）
- `--plot-dir` : グラフ出力ディレクトリ（既定: `output/plots`）
- `--x-unit {sec,min}` : 横軸単位（未指定時は実行時に入力）

## 複数入力時の出力ルール

同名での上書きを防ぐため、入力ファイルごとに出力先を分けます。

- `-o/--output-csv` 未指定時:
  - `output/<入力ファイル名(拡張子除く)>.csv`
- `-o/--output-csv` 指定時:
  - 値が `.csv` なら `指定名_<入力ファイル名>.csv`
  - 値がディレクトリなら `そのディレクトリ/<入力ファイル名>.csv`
- `--plot-dir` 未指定時:
  - `output/plots/<入力ファイル名>/encX.png` など
- `--plot-dir` 指定時:
  - `指定ディレクトリ/<入力ファイル名>/encX.png` など

単一入力時は従来どおり、`-o` と `--plot-dir` の値をそのまま使います。

## 入力/処理仕様（要点）

1. マーカー `FA F3 20` でレコード分割
2. 1レコードを138列固定行に変換（不足は欠損）
3. 現在のログ形式では、マーカー直後の1列目を Frame ID、24列目を Value Byte として使用
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

- 各入力ごとに `encX.png`, `encY.png`, `encZ.png` を保存
- 縦軸: 物理値
- 横軸: `time`（`sec`）または `time/60`（`min`）

