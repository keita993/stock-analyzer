import pandas as pd
import os

def fix_encoding(input_file, output_file, input_encoding='shift_jis', output_encoding='utf-8', sep=','):
    # CSVファイルを指定されたエンコーディングで読み込む
    try:
        # ヘッダー行をスキップして、実際のデータ部分から読み込む
        df = pd.read_csv(input_file, encoding=input_encoding, sep=sep, skiprows=8)
    except UnicodeDecodeError:
        print(f"エンコーディング {input_encoding} で読み込めませんでした。別のエンコーディングを試してください。")
        return
    except Exception as e:
        print(f"ファイル読み込み中にエラーが発生しました: {str(e)}")
        print("区切り文字やエンコーディングを確認してください。")
        return

    # データを新しいエンコーディングで保存
    try:
        df.to_csv(output_file, index=False, encoding=output_encoding)
        print(f"ファイルが正常に保存されました: {output_file}")
    except Exception as e:
        print(f"ファイル保存中にエラーが発生しました: {str(e)}")

# 使用例
input_file = '/Users/a0000/Downloads/SaveFile_000001_001921.csv'
output_file = '/Users/a0000/Downloads/Fixed_SaveFile.csv'

# ファイルの存在確認
if not os.path.exists(input_file):
    print(f"入力ファイルが見つかりません: {input_file}")
else:
    # skiprows=8を追加して最初の8行をスキップ
    fix_encoding(input_file, output_file, input_encoding='shift_jis', sep=',')
    # 上記が失敗した場合は以下を試してみてください
    # fix_encoding(input_file, output_file, input_encoding='utf-8')
    # fix_encoding(input_file, output_file, input_encoding='cp932')
    # fix_encoding(input_file, output_file, input_encoding='euc_jp')
    # fix_encoding(input_file, output_file, sep='\t')  # タブ区切りの場合