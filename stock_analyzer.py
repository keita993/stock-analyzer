import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import yfinance as yf

# ページ設定
st.set_page_config(
    page_title="株式取引分析アプリ", 
    layout="wide",
    initial_sidebar_state="collapsed"  # モバイル用にサイドバーを初期で折りたたむ
)

# スタイルシートを追加してモバイル表示を最適化
st.markdown("""
<style>
    /* モバイル向け全体調整 */
    @media (max-width: 640px) {
        .main .block-container {
            padding-top: 1rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        /* フォントサイズ調整 */
        h1 {
            font-size: 1.5rem !important;
        }
        h2 {
            font-size: 1.3rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        p, li, div {
            font-size: 0.9rem !important;
        }
        
        /* テーブル幅調整 */
        .stTable {
            width: 100%;
            font-size: 0.8rem !important;
        }
        
        /* 進捗バー調整 */
        .stProgress > div > div {
            height: 1.5rem !important;
        }
    }
    
    /* タッチデバイス向けボタン調整 */
    button {
        min-height: 2.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("株式の売買傾向分析アプリ（SBI証券用）")

# CSVファイルをアップロードまたは既存ファイルを使用
st.sidebar.header("データ入力")
upload_option = st.sidebar.radio(
    "データソースを選択",
    ("ファイルをアップロード", "サンプルデータを使用")
)

# エンコーディング変換機能をapp.pyから統合
def fix_encoding(input_file, output_file=None, input_encoding='shift_jis', output_encoding='utf-8', sep=',', skiprows=8):
    """CSVファイルのエンコーディングを修正し、データフレームとして返す"""
    try:
        # ヘッダー行をスキップして、実際のデータ部分から読み込む
        df = pd.read_csv(input_file, encoding=input_encoding, sep=sep, skiprows=skiprows)
        
        # 出力ファイルが指定されている場合は保存
        if output_file:
            df.to_csv(output_file, index=False, encoding=output_encoding)
            st.success(f"ファイルを変換しました: {output_file}")
        
        return df
    except UnicodeDecodeError:
        st.error(f"エンコーディング {input_encoding} で読み込めませんでした。別のエンコーディングを試してください。")
        return None
    except Exception as e:
        st.error(f"ファイル読み込み中にエラーが発生しました: {str(e)}")
        st.warning("区切り文字やエンコーディングを確認してください。")
        return None

def load_data(file_path=None, uploaded_file=None, encoding='utf-8', sep=',', skiprows=0):
    try:
        if uploaded_file is not None:
            # アップロードされたファイルを読み込む
            df = pd.read_csv(uploaded_file, encoding=encoding, sep=sep, skiprows=skiprows)
        elif file_path is not None:
            # 既存のファイルパスから読み込む
            df = pd.read_csv(file_path, encoding=encoding, sep=sep, skiprows=skiprows)
        else:
            st.error("ファイルが指定されていません")
            return None
            
        # 日付列を日付型に変換
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], format='%Y/%m/%d', errors='coerce')
        
        # 金額列を数値型に変換
        numeric_cols = [7, 8, 9, 10, 12]  # 数量、単価、手数料、税額、受渡金額の列インデックス
        for col in numeric_cols:
            if col < df.shape[1]:
                df.iloc[:, col] = pd.to_numeric(df.iloc[:, col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 列名を設定
        df.columns = ['日付', '銘柄', 'コード', '市場', '取引種別', '期間', '口座', '課税区分', 
                      '数量', '単価', '手数料', '税額', '受渡日', '受渡金額']
        
        return df
    
    except Exception as e:
        st.error(f"データ読み込み中にエラーが発生しました: {str(e)}")
        return None

# グローバル変数としてモバイル判定を追加
is_mobile = False

# モバイル向けにレイアウトを調整する関数
def responsive_columns(spec):
    """
    スクリーン幅に基づいて列数を調整
    スマホ画面なら1列、デスクトップなら指定列数
    """
    global is_mobile
    try:
        # JavaScriptを使ってスクリーン幅を取得
        screen_width = st.session_state.get('screen_width', 1000)
        is_mobile = screen_width < 640
    except:
        pass
    
    if is_mobile:
        return st.columns([1])  # モバイルでは1列
    else:
        return st.columns(spec)  # デスクトップでは指定された列数

if upload_option == "ファイルをアップロード":
    uploaded_file = st.sidebar.file_uploader("CSVファイルをアップロード", type=["csv"])
    
    if uploaded_file is not None:
        # エンコーディングオプションを表示
        st.sidebar.header("ファイル読み込みオプション")
        encoding_option = st.sidebar.selectbox(
            "エンコーディング",
            options=["utf-8", "shift_jis", "cp932", "euc_jp", "latin1"],
            index=1  # shift_jisをデフォルトに設定
        )
        
        separator = st.sidebar.selectbox(
            "区切り文字",
            options=[",", "\t", ";"],
            index=0  # カンマをデフォルトに設定
        )
        
        skip_rows = st.sidebar.number_input(
            "スキップする行数",
            min_value=0,
            max_value=10,
            value=8,  # デフォルト値
            help="ヘッダーなど、スキップする行数を指定"
        )
        
        # データ読み込み
        data = load_data(uploaded_file=uploaded_file, encoding=encoding_option, sep=separator, skiprows=skip_rows)
        
        # 読み込みに失敗した場合、他のエンコーディングを自動試行するオプション
        if data is None:
            if st.sidebar.button("エンコーディングを自動検出"):
                encodings = ["utf-8", "shift_jis", "cp932", "euc_jp", "latin1"]
                for enc in encodings:
                    if enc != encoding_option:  # 既に試したエンコーディングはスキップ
                        st.info(f"{enc}でファイルを読み込み中...")
                        try:
                            data = load_data(uploaded_file=uploaded_file, encoding=enc, sep=separator, skiprows=skip_rows)
                            if data is not None:
                                st.success(f"エンコーディング {enc} で正常に読み込みました！")
                                break
                        except:
                            pass
    else:
        st.info("CSVファイルをアップロードしてください")
        data = None
else:
    sample_path = '/Users/a0000/Downloads/Fixed_SaveFile.csv'
    if os.path.exists(sample_path):
        data = load_data(file_path=sample_path)
    else:
        st.error("サンプルファイルが見つかりません")
        data = None

# メイン分析セクション
if data is not None:
    st.success("データを正常に読み込みました！")
    
    # 日付列を確実に日付型に変換
    data['日付'] = pd.to_datetime(data['日付'], errors='coerce')
    
    # 日経平均と売買代金の比較チャート
    st.header("日経平均株価と売買代金の比較")
    
    # 日付範囲を取得
    min_date = data['日付'].min()
    max_date = data['日付'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        # 日経平均株価データを取得
        try:
            st.info(f"データ期間: {min_date.strftime('%Y年%m月%d日')} から {max_date.strftime('%Y年%m月%d日')}")
            
            with st.spinner("日経平均データを取得中..."):
                nikkei = yf.download('^N225', start=min_date, end=max_date)
            
            # 日次売買代金を集計
            daily_trade = data.copy()
            daily_trade['受渡金額'] = pd.to_numeric(daily_trade['受渡金額'], errors='coerce')
            
            # 取引種別ごとに日次データを集計
            buy_daily = daily_trade[daily_trade['取引種別'] == '株式現物買'].groupby(daily_trade['日付'].dt.date)['受渡金額'].sum()
            sell_daily = daily_trade[daily_trade['取引種別'] == '株式現物売'].groupby(daily_trade['日付'].dt.date)['受渡金額'].sum()
            
            # 日付をインデックスからカラムに変換
            buy_df = buy_daily.reset_index()
            buy_df.columns = ['日付', '買い金額']
            
            sell_df = sell_daily.reset_index()
            sell_df.columns = ['日付', '売り金額']
            
            # 日経平均を準備
            nikkei_df = nikkei.reset_index()
            nikkei_df = nikkei_df[['Date', 'Close']]
            nikkei_df.columns = ['日付', '日経平均']
            
            # 日付型を統一（両方をdatetime型に変換）
            buy_df['日付'] = pd.to_datetime(buy_df['日付'])
            sell_df['日付'] = pd.to_datetime(sell_df['日付'])
            nikkei_df['日付'] = pd.to_datetime(nikkei_df['日付'])
            
            # データを結合
            merged_df = pd.merge(nikkei_df, buy_df, left_on='日付', right_on='日付', how='outer')
            merged_df = pd.merge(merged_df, sell_df, left_on='日付', right_on='日付', how='outer')
            
            # 欠損値を0に設定
            merged_df['買い金額'] = merged_df['買い金額'].fillna(0)
            merged_df['売り金額'] = merged_df['売り金額'].fillna(0)
            
            # サブプロットを作成（2つのY軸）
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 日経平均チャート
            fig.add_trace(
                go.Scatter(x=merged_df['日付'], y=merged_df['日経平均'], name="日経平均", line=dict(color='blue')),
                secondary_y=False,
            )
            
            # 買い金額チャート
            fig.add_trace(
                go.Bar(x=merged_df['日付'], y=merged_df['買い金額'], name="買い金額", marker_color='green', opacity=0.7),
                secondary_y=True,
            )
            
            # 売り金額チャート
            fig.add_trace(
                go.Bar(x=merged_df['日付'], y=merged_df['売り金額'], name="売り金額", marker_color='red', opacity=0.7),
                secondary_y=True,
            )
            
            # チャートをスマホ対応に調整
            fig.update_layout(
                title_text="日経平均株価と売買代金の推移",
                hovermode="x unified",
                height=500,  # 高さを固定
                margin=dict(l=10, r=10, t=50, b=30),  # マージンを小さく
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)  # 凡例を上部中央に
            )
            
            # X軸とY軸のタイトルを更新
            fig.update_xaxes(title_text="日付")
            fig.update_yaxes(title_text="日経平均株価", secondary_y=False)
            fig.update_yaxes(title_text="売買代金（円）", secondary_y=True)
            
            # チャートを表示
            st.plotly_chart(fig, use_container_width=True, height=500)
            
            # 統合された分析セクション
            st.subheader("取引タイミング分析")
            
            # 日経平均のトレンド分析を修正
            st.subheader("日経平均トレンド分析と売買判定")
            
            # 移動平均線パラメータの修正
            nikkei_ma_short = 5   # 短期移動平均線（5日）
            nikkei_ma_medium = 20 # 中期移動平均線（20日）- より一般的な値に変更
            nikkei_ma_long = 50   # 長期移動平均線（50日）- より一般的な値に変更
            
            # 日付順にソート
            nikkei_sorted = nikkei.sort_index()
            
            # 移動平均線を計算
            nikkei_sorted['MA_short'] = nikkei_sorted['Close'].rolling(window=nikkei_ma_short).mean()
            nikkei_sorted['MA_medium'] = nikkei_sorted['Close'].rolling(window=nikkei_ma_medium).mean()
            nikkei_sorted['MA_long'] = nikkei_sorted['Close'].rolling(window=nikkei_ma_long).mean()
            
            # ゴールデンクロス・デッドクロスによるシグナル判定
            nikkei_sorted['ゴールデンクロス'] = (nikkei_sorted['MA_short'] > nikkei_sorted['MA_medium']) & (nikkei_sorted['MA_short'].shift(1) <= nikkei_sorted['MA_medium'].shift(1))
            nikkei_sorted['デッドクロス'] = (nikkei_sorted['MA_short'] < nikkei_sorted['MA_medium']) & (nikkei_sorted['MA_short'].shift(1) >= nikkei_sorted['MA_medium'].shift(1))
            
            # 買いシグナル・売りシグナルとして設定
            nikkei_sorted['買いシグナル'] = nikkei_sorted['ゴールデンクロス']
            nikkei_sorted['売りシグナル'] = nikkei_sorted['デッドクロス']
            
            # トレンド判定（より洗練された方法）
            nikkei_sorted['上昇トレンド'] = nikkei_sorted['MA_short'] > nikkei_sorted['MA_medium']
            nikkei_sorted['下落トレンド'] = nikkei_sorted['MA_short'] < nikkei_sorted['MA_medium']
            
            # トレンドグラフを作成
            fig_trend = go.Figure()
            
            # 日経平均終値
            fig_trend.add_trace(go.Scatter(
                x=nikkei_sorted.index, 
                y=nikkei_sorted['Close'],
                mode='lines',
                name='日経平均',
                line=dict(color='blue', width=1)
            ))
            
            # 短期移動平均線
            fig_trend.add_trace(go.Scatter(
                x=nikkei_sorted.index, 
                y=nikkei_sorted['MA_short'],
                mode='lines',
                name=f'{nikkei_ma_short}日移動平均',
                line=dict(color='green', width=1)
            ))
            
            # 中期移動平均線
            fig_trend.add_trace(go.Scatter(
                x=nikkei_sorted.index, 
                y=nikkei_sorted['MA_medium'],
                mode='lines',
                name=f'{nikkei_ma_medium}日移動平均',
                line=dict(color='orange', width=1)
            ))
            
            # 長期移動平均線
            fig_trend.add_trace(go.Scatter(
                x=nikkei_sorted.index, 
                y=nikkei_sorted['MA_long'],
                mode='lines',
                name=f'{nikkei_ma_long}日移動平均',
                line=dict(color='red', width=1, dash='dot')
            ))
            
            # 買いシグナル（ゴールデンクロス）
            buy_signals = nikkei_sorted[nikkei_sorted['買いシグナル']]
            if not buy_signals.empty:
                fig_trend.add_trace(go.Scatter(
                    x=buy_signals.index, 
                    y=buy_signals['Close'],
                    mode='markers',
                    name='買いシグナル',
                    marker=dict(symbol='triangle-up', size=12, color='green')
                ))
            
            # 売りシグナル（デッドクロス）
            sell_signals = nikkei_sorted[nikkei_sorted['売りシグナル']]
            if not sell_signals.empty:
                fig_trend.add_trace(go.Scatter(
                    x=sell_signals.index, 
                    y=sell_signals['Close'],
                    mode='markers',
                    name='売りシグナル',
                    marker=dict(symbol='triangle-down', size=12, color='red')
                ))
            
            # レイアウト設定
            fig_trend.update_layout(
                title='日経平均トレンド分析と売買シグナル',
                xaxis_title='日付',
                yaxis_title='価格',
                height=500,
                margin=dict(l=10, r=10, t=50, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            # グラフ表示
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # 一致度分析を改善 - 日付の前後数日も含めて一致とみなす
            st.subheader("売買シグナルと実際の取引一致度分析")
            
            # シグナル日前後の日数（前後7日をシグナル有効期間とする）
            signal_window = 7
            
            # 分析のためのデータ準備
            signal_df = nikkei_sorted[['買いシグナル', '売りシグナル']].reset_index()
            signal_df.columns = ['日付', '買いシグナル', '売りシグナル']
            
            # 各シグナル発生日の前後n日も有効期間とみなす
            buy_signal_dates = signal_df[signal_df['買いシグナル']]['日付'].tolist()
            sell_signal_dates = signal_df[signal_df['売りシグナル']]['日付'].tolist()
            
            # 有効期間のデータフレーム生成
            valid_buy_dates = []
            valid_sell_dates = []
            
            for date in buy_signal_dates:
                # 前後n日を追加
                for i in range(-signal_window, signal_window+1):
                    valid_date = date + pd.Timedelta(days=i)
                    valid_buy_dates.append(valid_date)
            
            for date in sell_signal_dates:
                # 前後n日を追加
                for i in range(-signal_window, signal_window+1):
                    valid_date = date + pd.Timedelta(days=i)
                    valid_sell_dates.append(valid_date)
            
            # 日付型を統一
            merged_df['日付'] = pd.to_datetime(merged_df['日付'])
            
            # 拡張シグナル期間内の取引を集計
            matched_buys = merged_df[merged_df['日付'].isin(valid_buy_dates)]['買い金額'].sum()
            mismatched_buys = merged_df[~merged_df['日付'].isin(valid_buy_dates)]['買い金額'].sum()
            
            matched_sells = merged_df[merged_df['日付'].isin(valid_sell_dates)]['売り金額'].sum()
            mismatched_sells = merged_df[~merged_df['日付'].isin(valid_sell_dates)]['売り金額'].sum()
            
            # 結果表示
            col_signal1, col_signal2 = responsive_columns([1, 1])
            
            with col_signal1:
                st.markdown("### シグナル一致率")
                
                # メトリクス表示
                total_buys = matched_buys + mismatched_buys
                total_sells = matched_sells + mismatched_sells
                
                buy_match_rate = (matched_buys / total_buys * 100) if total_buys > 0 else 0
                sell_match_rate = (matched_sells / total_sells * 100) if total_sells > 0 else 0
                overall_match_rate = ((matched_buys + matched_sells) / (total_buys + total_sells) * 100) if (total_buys + total_sells) > 0 else 0
                
                st.metric("買いシグナル一致率", f"{buy_match_rate:.1f}%", 
                         delta=f"{buy_match_rate - 50:.1f}%" if buy_match_rate != 50 else "中立")
                
                st.metric("売りシグナル一致率", f"{sell_match_rate:.1f}%", 
                         delta=f"{sell_match_rate - 50:.1f}%" if sell_match_rate != 50 else "中立")
                
                st.metric("総合シグナル一致率", f"{overall_match_rate:.1f}%", 
                         delta=f"{overall_match_rate - 50:.1f}%" if overall_match_rate != 50 else "中立")
                
                # データ表示
                signal_summary = pd.DataFrame({
                    "項目": ["買いシグナルに一致", "買いシグナルに不一致", "売りシグナルに一致", "売りシグナルに不一致"],
                    "金額": [
                        f"{matched_buys:,.0f}円", 
                        f"{mismatched_buys:,.0f}円", 
                        f"{matched_sells:,.0f}円", 
                        f"{mismatched_sells:,.0f}円"
                    ]
                })
                
                st.dataframe(signal_summary, use_container_width=True)
            
            with col_signal2:
                st.markdown("### シグナル分析評価")
                
                # 買いシグナル評価
                if buy_match_rate > 70:
                    st.success("✅ **買いタイミング**: 優れています。トレンド転換点での買い判断が的確です。")
                elif buy_match_rate > 50:
                    st.info("ℹ️ **買いタイミング**: 良好です。トレンド判断に基づいた買い注文が多いですが、改善の余地があります。")
                elif buy_match_rate > 30:
                    st.warning("⚠️ **買いタイミング**: 要改善。トレンド転換を十分に捉えられていません。")
                else:
                    st.error("❌ **買いタイミング**: 不適切です。理想的な買いシグナルとは逆のタイミングで買っている可能性が高いです。")
                
                # 売りシグナル評価
                if sell_match_rate > 70:
                    st.success("✅ **売りタイミング**: 優れています。トレンド転換点での売り判断が的確です。")
                elif sell_match_rate > 50:
                    st.info("ℹ️ **売りタイミング**: 良好です。トレンド判断に基づいた売り注文が多いですが、改善の余地があります。")
                elif sell_match_rate > 30:
                    st.warning("⚠️ **売りタイミング**: 要改善。トレンド転換を十分に捉えられていません。")
                else:
                    st.error("❌ **売りタイミング**: 不適切です。理想的な売りシグナルとは逆のタイミングで売っている可能性が高いです。")
                
                # 総合評価
                st.markdown("### 改善提案")
                
                if overall_match_rate < 50:
                    st.markdown("""
                    **トレンド分析に基づく改善点**:
                    
                    1. 短期・中期・長期の移動平均線の位置関係を確認し、トレンドの方向性を把握しましょう
                    2. 上昇トレンド初期（短期線が中期線を上抜ける）で買い、下落トレンド初期（短期線が中期線を下抜ける）で売るルールを検討してください
                    3. チャートパターンの学習: トレンド転換のサインを学んで、早めに判断する力を養いましょう
                    4. 感情的な売買を避け、事前に決めたルールに従うディシプリンを強化しましょう
                    """)
                else:
                    st.markdown("""
                    **さらなる改善のためのヒント**:
                    
                    1. シグナル発生後のエントリータイミングを見直し、より有利な価格での取引を目指しましょう
                    2. ポジションサイジング: トレンドの強さに応じて投資金額を調整することで、リターンを最適化できます
                    3. 複数の時間軸でのトレンド確認: 日足だけでなく週足や月足のトレンドも確認し、より大きな流れに逆らわないようにしましょう
                    """)

            # メトリクスと分析を並べて表示
            try:
                col1, col2 = responsive_columns([1, 1])
            except:
                # フォールバック - レスポンシブ機能が動作しない場合
                cols = st.columns([1, 1])
                col1, col2 = cols[0], cols[1]
            
            with col1:
                st.markdown("### 市場状況別の取引額")
                
                # データを表形式で整理
                market_data = {
                    "市場状況": ["上昇相場", "下落相場", "合計"],
                    "買い金額": [f"{buy_on_up:,.0f}円", f"{buy_on_down:,.0f}円", f"{buy_on_up + buy_on_down:,.0f}円"],
                    "売り金額": [f"{sell_on_up:,.0f}円", f"{sell_on_down:,.0f}円", f"{sell_on_up + sell_on_down:,.0f}円"]
                }
                
                # データフレームを作成して表示
                market_df = pd.DataFrame(market_data)
                
                # モバイル向けにテーブル表示を簡略化
                if is_mobile:
                    # 表示する列を限定
                    simple_df = market_df[["市場状況", "買い金額"]]
                    st.dataframe(simple_df, height=200, use_container_width=True)
                    
                    simple_df = market_df[["市場状況", "売り金額"]]
                    st.dataframe(simple_df, height=200, use_container_width=True)
                else:
                    # デスクトップ向けに全ての列を表示
                    st.table(market_df)
                
                # 比率を計算
                if buy_on_up + sell_on_up > 0:
                    up_buy_ratio = buy_on_up / (buy_on_up + sell_on_up) * 100
                    st.markdown(f"**上昇相場での買い/売り比率**: {up_buy_ratio:.1f}% / {100-up_buy_ratio:.1f}%")
                    st.progress(int(up_buy_ratio))
                
                if buy_on_down + sell_on_down > 0:
                    down_buy_ratio = buy_on_down / (buy_on_down + sell_on_down) * 100
                    st.markdown(f"**下落相場での買い/売り比率**: {down_buy_ratio:.1f}% / {100-down_buy_ratio:.1f}%")
                    st.progress(int(down_buy_ratio))
            
            with col2:
                st.markdown("### 取引パターン分析")
                
                # 上昇相場の分析（より辛口に）
                if buy_on_up + sell_on_up > 0:
                    up_buy_ratio = buy_on_up / (buy_on_up + sell_on_up) * 100
                    
                    if up_buy_ratio > 60:
                        st.error(f"📈 **上昇相場** - 買い{up_buy_ratio:.1f}%、売り{100-up_buy_ratio:.1f}%\n\n"
                                "**問題点**: 相場上昇時に買い集中しており、典型的な「高値掴み」リスクが高い状態です。他の投資家が利益を確定する局面で買いを入れ、後の下落に巻き込まれやすい危険なパターンです。")
                    elif up_buy_ratio < 40:
                        st.success(f"📈 **上昇相場** - 買い{up_buy_ratio:.1f}%、売り{100-up_buy_ratio:.1f}%\n\n"
                                "上昇相場での売り優位は理想的です。他の投資家が熱狂して買いに走る中で冷静に利益確定できています。")
                    else:
                        st.warning(f"📈 **上昇相場** - 買い{up_buy_ratio:.1f}%、売り{100-up_buy_ratio:.1f}%\n\n"
                                "上昇相場ではもっと利益確定（売り）に傾けるべきです。上昇局面での買いは、後に下落した際の含み損リスクが高まります。")
                
                # 下落相場の分析（より辛口に）
                if buy_on_down + sell_on_down > 0:
                    down_buy_ratio = buy_on_down / (buy_on_down + sell_on_down) * 100
                    
                    if down_buy_ratio > 60:
                        st.success(f"📉 **下落相場** - 買い{down_buy_ratio:.1f}%、売り{100-down_buy_ratio:.1f}%\n\n"
                                "下落相場での買い姿勢は理想的です。他の投資家がパニック売りする中で、割安になった銘柄を拾える強い精神力があります。")
                    elif down_buy_ratio < 40:
                        st.error(f"📉 **下落相場** - 買い{down_buy_ratio:.1f}%、売り{100-down_buy_ratio:.1f}%\n\n"
                                "**重大な問題**: 下落相場で売りに偏っており、典型的な「底値売り」の悪い習慣があります。安値で損切りし、その後の反発で利益機会を逃す最悪のパターンです。相場の格言「弱気相場は強気に、強気相場は弱気に」の逆をやっています。")
                    else:
                        st.warning(f"📉 **下落相場** - 買い{down_buy_ratio:.1f}%、売り{100-down_buy_ratio:.1f}%\n\n"
                                "下落相場では買いの比率をもっと高めるべきです。下落時こそ割安銘柄を集める好機なのに、その機会を十分に活かせていません。")
                
                # 総合評価（より辛口に）
                st.markdown("### 総合評価")
                
                if buy_on_up + sell_on_up > 0 and buy_on_down + sell_on_down > 0:
                    up_buy_ratio = buy_on_up / (buy_on_up + sell_on_up) * 100
                    down_buy_ratio = buy_on_down / (buy_on_down + sell_on_down) * 100
                    
                    if up_buy_ratio > 60 and down_buy_ratio < 40:
                        st.error("**最悪の投資パターン検出**: 典型的な「高値で買い、安値で売る」という最も損失を生みやすい投資行動です。マーケット心理に流されて大衆と同じ行動をとり、ほぼ確実に長期的な損失を生み出します。プロの投資家は、あなたのような投資家から富を移転しています。")
                        
                        # 改善提案
                        st.markdown("""
                        ### 緊急改善提案
                        
                        1. **投資行動を完全に見直してください**: 現在のパターンの真逆の行動をとることを検討すべきです
                        2. **相場心理に流されないための訓練**: 下落時に冷静に買い増せるよう、感情コントロールのトレーニングが必要です
                        3. **機械的なルールの導入**: 感情で判断せず、事前に決めたルールに従って売買を行いましょう
                        4. **積立投資の比率を増やす**: 自分の判断を減らし、機械的な定期買付の比率を上げることを検討してください
                        """)
                    elif up_buy_ratio < 40 and down_buy_ratio > 60:
                        st.success("**プロフェッショナルな投資パターン**: 「安く買って高く売る」という投資の基本原則を実践できています。逆張り戦略を実行できる精神力と市場センスがあります。")
                    elif up_buy_ratio > 60 and down_buy_ratio > 60:
                        st.warning("**強気一辺倒の買い姿勢**: どんな相場環境でも買い続ける傾向があります。長期投資家的視点は良いですが、高値圏での過剰な買い増しは危険です。特に上昇相場での投資比率を見直してください。")
                    elif up_buy_ratio < 40 and down_buy_ratio < 40:
                        st.warning("**過度に慎重な売り姿勢**: どんな相場環境でも売り優位になっています。リスク回避志向が強すぎるため、長期的な資産形成の機会を逃している可能性があります。")
                    else:
                        st.info("**中立的な投資姿勢**: 相場環境によって買いと売りのバランスを取っていますが、上昇時の売りと下落時の買いの比率をさらに高めることで、より良い結果が期待できます。")
            
            # 投資効率の計算（可能であれば）
            total_buy = buy_on_up + buy_on_down
            total_sell = sell_on_up + sell_on_down
            
            if total_buy > 0 and total_sell > 0:
                # 理想的な投資パターン（下落時買い・上昇時売り）の割合
                optimal_ratio = (buy_on_down / total_buy) * (sell_on_up / total_sell)
                # 実際のパターン（上昇時買い・下落時売り）の割合
                actual_ratio = (buy_on_up / total_buy) * (sell_on_down / total_sell)
                
                efficiency = 1 - (actual_ratio / (optimal_ratio + actual_ratio))
                
                st.metric("投資タイミング効率", f"{efficiency * 100:.1f}%", 
                         delta=f"理想との差: {(efficiency-0.5)*200:.1f}%" if efficiency != 0.5 else "中立")
                
                st.markdown(f"**注**: 投資タイミング効率は、理想的な「安く買って高く売る」パターンにどれだけ近いかを示します。" +
                           f"50%が中立、100%に近いほど理想的なタイミング、0%に近いほど逆のパターン（高く買って安く売る）を示します。")
            
        except Exception as e:
            st.error(f"分析中にエラーが発生しました: {str(e)}")
            st.warning("yfinanceライブラリをインストールするには: pip install yfinance")
    else:
        st.warning("取引データの日付範囲が不明なため、日経平均との比較チャートを表示できません。")

# RSIとMACDを計算するための関数
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    # 移動平均の計算
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    
    # MACDとシグナルラインの計算
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    # ヒストグラムの計算
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

# 技術指標の計算と分析を追加（移動平均分析の下に追加）
# 既存の移動平均分析コードの後に以下を追加

# RSIの計算
nikkei_sorted['RSI'] = calculate_rsi(nikkei_sorted['Close'])

# MACDの計算
nikkei_sorted['MACD'], nikkei_sorted['Signal'], nikkei_sorted['Histogram'] = calculate_macd(nikkei_sorted['Close'])

# 複合シグナルの生成
# RSIによるシグナル（RSI<30で買い、RSI>70で売り）
nikkei_sorted['RSI_買いシグナル'] = (nikkei_sorted['RSI'] < 30) & (nikkei_sorted['RSI'].shift(1) >= 30)
nikkei_sorted['RSI_売りシグナル'] = (nikkei_sorted['RSI'] > 70) & (nikkei_sorted['RSI'].shift(1) <= 70)

# MACDによるシグナル（MACDがシグナルラインを上抜けで買い、下抜けで売り）
nikkei_sorted['MACD_買いシグナル'] = (nikkei_sorted['MACD'] > nikkei_sorted['Signal']) & (nikkei_sorted['MACD'].shift(1) <= nikkei_sorted['Signal'].shift(1))
nikkei_sorted['MACD_売りシグナル'] = (nikkei_sorted['MACD'] < nikkei_sorted['Signal']) & (nikkei_sorted['MACD'].shift(1) >= nikkei_sorted['Signal'].shift(1))

# 複合シグナル（少なくとも2つの指標が同時に買い/売りシグナルを出した場合）
nikkei_sorted['強い買いシグナル'] = (
    (nikkei_sorted['買いシグナル'] & nikkei_sorted['RSI_買いシグナル']) |
    (nikkei_sorted['買いシグナル'] & nikkei_sorted['MACD_買いシグナル']) |
    (nikkei_sorted['RSI_買いシグナル'] & nikkei_sorted['MACD_買いシグナル'])
)

nikkei_sorted['強い売りシグナル'] = (
    (nikkei_sorted['売りシグナル'] & nikkei_sorted['RSI_売りシグナル']) |
    (nikkei_sorted['売りシグナル'] & nikkei_sorted['MACD_売りシグナル']) |
    (nikkei_sorted['RSI_売りシグナル'] & nikkei_sorted['MACD_売りシグナル'])
)

# RSIとMACDのチャートを表示
st.subheader("RSIとMACD指標分析")

# RSIチャート
fig_rsi = go.Figure()

# 日経平均（参照用）を2番目のY軸に表示
fig_rsi.add_trace(go.Scatter(
    x=nikkei_sorted.index, 
    y=nikkei_sorted['Close'],
    mode='lines',
    name='日経平均',
    line=dict(color='blue', width=1),
    yaxis="y2"
))

# RSI
fig_rsi.add_trace(go.Scatter(
    x=nikkei_sorted.index, 
    y=nikkei_sorted['RSI'],
    mode='lines',
    name='RSI (14)',
    line=dict(color='purple', width=1.5)
))

# 買われすぎ・売られすぎのラインを追加
fig_rsi.add_shape(
    type="line", line=dict(color="red", width=1, dash="dash"),
    y0=70, y1=70, x0=nikkei_sorted.index[0], x1=nikkei_sorted.index[-1]
)

fig_rsi.add_shape(
    type="line", line=dict(color="green", width=1, dash="dash"),
    y0=30, y1=30, x0=nikkei_sorted.index[0], x1=nikkei_sorted.index[-1]
)

# RSIによる買いシグナル
rsi_buy_signals = nikkei_sorted[nikkei_sorted['RSI_買いシグナル']]
if not rsi_buy_signals.empty:
    fig_rsi.add_trace(go.Scatter(
        x=rsi_buy_signals.index, 
        y=rsi_buy_signals['RSI'],
        mode='markers',
        name='RSI買いシグナル',
        marker=dict(symbol='triangle-up', size=10, color='green')
    ))

# RSIによる売りシグナル
rsi_sell_signals = nikkei_sorted[nikkei_sorted['RSI_売りシグナル']]
if not rsi_sell_signals.empty:
    fig_rsi.add_trace(go.Scatter(
        x=rsi_sell_signals.index, 
        y=rsi_sell_signals['RSI'],
        mode='markers',
        name='RSI売りシグナル',
        marker=dict(symbol='triangle-down', size=10, color='red')
    ))

# レイアウト設定
fig_rsi.update_layout(
    title='RSI分析（相対力指数）',
    xaxis_title='日付',
    yaxis_title='RSI',
    height=400,
    margin=dict(l=10, r=10, t=50, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    yaxis=dict(
        range=[0, 100],
        tickvals=[0, 30, 50, 70, 100],
    ),
    yaxis2=dict(
        title="日経平均株価",
        overlaying="y",
        side="right",
        showgrid=False
    )
)

# グラフ表示
st.plotly_chart(fig_rsi, use_container_width=True)

# MACDチャート
fig_macd = go.Figure()

# MACDライン
fig_macd.add_trace(go.Scatter(
    x=nikkei_sorted.index, 
    y=nikkei_sorted['MACD'],
    mode='lines',
    name='MACD (12, 26)',
    line=dict(color='blue', width=1.5)
))

# シグナルライン
fig_macd.add_trace(go.Scatter(
    x=nikkei_sorted.index, 
    y=nikkei_sorted['Signal'],
    mode='lines',
    name='Signal (9)',
    line=dict(color='red', width=1)
))

# ヒストグラム
colors = ['green' if h >= 0 else 'red' for h in nikkei_sorted['Histogram']]
fig_macd.add_trace(go.Bar(
    x=nikkei_sorted.index,
    y=nikkei_sorted['Histogram'],
    name='Histogram',
    marker_color=colors
))

# MACDによる買いシグナル
macd_buy_signals = nikkei_sorted[nikkei_sorted['MACD_買いシグナル']]
if not macd_buy_signals.empty:
    fig_macd.add_trace(go.Scatter(
        x=macd_buy_signals.index, 
        y=macd_buy_signals['MACD'],
        mode='markers',
        name='MACD買いシグナル',
        marker=dict(symbol='triangle-up', size=10, color='green')
    ))

# MACDによる売りシグナル
macd_sell_signals = nikkei_sorted[nikkei_sorted['MACD_売りシグナル']]
if not macd_sell_signals.empty:
    fig_macd.add_trace(go.Scatter(
        x=macd_sell_signals.index, 
        y=macd_sell_signals['MACD'],
        mode='markers',
        name='MACD売りシグナル',
        marker=dict(symbol='triangle-down', size=10, color='red')
    ))

# レイアウト設定
fig_macd.update_layout(
    title='MACD分析（移動平均収束拡散法）',
    xaxis_title='日付',
    yaxis_title='MACD',
    height=400,
    margin=dict(l=10, r=10, t=50, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
)

# グラフ表示
st.plotly_chart(fig_macd, use_container_width=True)

# 複合シグナル分析
st.subheader("複合テクニカル指標による売買シグナル")

# 複合シグナルを含む日経平均チャート
fig_composite = go.Figure()

# 日経平均終値
fig_composite.add_trace(go.Scatter(
    x=nikkei_sorted.index, 
    y=nikkei_sorted['Close'],
    mode='lines',
    name='日経平均',
    line=dict(color='blue', width=1)
))

# 強い買いシグナル
strong_buy_signals = nikkei_sorted[nikkei_sorted['強い買いシグナル']]
if not strong_buy_signals.empty:
    fig_composite.add_trace(go.Scatter(
        x=strong_buy_signals.index, 
        y=strong_buy_signals['Close'],
        mode='markers',
        name='強い買いシグナル',
        marker=dict(symbol='triangle-up', size=14, color='green', line=dict(width=2, color='white'))
    ))

# 強い売りシグナル
strong_sell_signals = nikkei_sorted[nikkei_sorted['強い売りシグナル']]
if not strong_sell_signals.empty:
    fig_composite.add_trace(go.Scatter(
        x=strong_sell_signals.index, 
        y=strong_sell_signals['Close'],
        mode='markers',
        name='強い売りシグナル',
        marker=dict(symbol='triangle-down', size=14, color='red', line=dict(width=2, color='white'))
    ))

# レイアウト設定
fig_composite.update_layout(
    title='複合テクニカル指標による売買シグナル',
    xaxis_title='日付',
    yaxis_title='価格',
    height=500,
    margin=dict(l=10, r=10, t=50, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
)

# グラフ表示
st.plotly_chart(fig_composite, use_container_width=True)

# 複合シグナルと実際の取引の一致度分析
st.subheader("複合シグナルと実際の取引一致度")

# 複合シグナル分析用のデータ準備
composite_df = nikkei_sorted[['強い買いシグナル', '強い売りシグナル']].reset_index()
composite_df.columns = ['日付', '強い買いシグナル', '強い売りシグナル']

# 各シグナル発生日の前後n日も有効期間とみなす
strong_buy_dates = composite_df[composite_df['強い買いシグナル']]['日付'].tolist()
strong_sell_dates = composite_df[composite_df['強い売りシグナル']]['日付'].tolist()

# 有効期間のデータフレーム生成
valid_strong_buy_dates = []
valid_strong_sell_dates = []

for date in strong_buy_dates:
    for i in range(-signal_window, signal_window+1):
        valid_date = date + pd.Timedelta(days=i)
        valid_strong_buy_dates.append(valid_date)

for date in strong_sell_dates:
    for i in range(-signal_window, signal_window+1):
        valid_date = date + pd.Timedelta(days=i)
        valid_strong_sell_dates.append(valid_date)

# 拡張シグナル期間内の取引を集計
strong_matched_buys = merged_df[merged_df['日付'].isin(valid_strong_buy_dates)]['買い金額'].sum()
strong_mismatched_buys = merged_df[~merged_df['日付'].isin(valid_strong_buy_dates)]['買い金額'].sum()

strong_matched_sells = merged_df[merged_df['日付'].isin(valid_strong_sell_dates)]['売り金額'].sum()
strong_mismatched_sells = merged_df[~merged_df['日付'].isin(valid_strong_sell_dates)]['売り金額'].sum()

# 結果表示
col_strong1, col_strong2 = responsive_columns([1, 1])

with col_strong1:
    st.markdown("### 複合シグナル一致率")
    
    # メトリクス表示
    total_buys = strong_matched_buys + strong_mismatched_buys
    total_sells = strong_matched_sells + strong_mismatched_sells
    
    strong_buy_match_rate = (strong_matched_buys / total_buys * 100) if total_buys > 0 else 0
    strong_sell_match_rate = (strong_matched_sells / total_sells * 100) if total_sells > 0 else 0
    strong_overall_match_rate = ((strong_matched_buys + strong_matched_sells) / (total_buys + total_sells) * 100) if (total_buys + total_sells) > 0 else 0
    
    st.metric("複合買いシグナル一致率", f"{strong_buy_match_rate:.1f}%", 
             delta=f"{strong_buy_match_rate - 50:.1f}%" if strong_buy_match_rate != 50 else "中立")
    
    st.metric("複合売りシグナル一致率", f"{strong_sell_match_rate:.1f}%", 
             delta=f"{strong_sell_match_rate - 50:.1f}%" if strong_sell_match_rate != 50 else "中立")
    
    st.metric("複合総合シグナル一致率", f"{strong_overall_match_rate:.1f}%", 
             delta=f"{strong_overall_match_rate - 50:.1f}%" if strong_overall_match_rate != 50 else "中立")

with col_strong2:
    st.markdown("### 複合シグナル評価")
    
    # 買いシグナル評価
    if strong_buy_match_rate > 70:
        st.success("✅ **複合買いシグナル**: 非常に優れたタイミング！複数の指標が示す好機を上手く活用できています。")
    elif strong_buy_match_rate > 50:
        st.info("ℹ️ **複合買いシグナル**: 良好です。複数指標のシグナルに基づいた買い行動が見られます。")
    elif strong_buy_match_rate > 30:
        st.warning("⚠️ **複合買いシグナル**: 改善の余地があります。複数の指標が示す買い時を十分に活かせていません。")
    else:
        st.error("❌ **複合買いシグナル**: 要改善。複数指標が示す買い時とは逆のタイミングで行動している可能性があります。")
    
    # 売りシグナル評価
    if strong_sell_match_rate > 70:
        st.success("✅ **複合売りシグナル**: 非常に優れたタイミング！複数の指標が示す好機を上手く活用できています。")
    elif strong_sell_match_rate > 50:
        st.info("ℹ️ **複合売りシグナル**: 良好です。複数指標のシグナルに基づいた売り行動が見られます。")
    elif strong_sell_match_rate > 30:
        st.warning("⚠️ **複合売りシグナル**: 改善の余地があります。複数の指標が示す売り時を十分に活かせていません。")
    else:
        st.error("❌ **複合売りシグナル**: 要改善。複数指標が示す売り時とは逆のタイミングで行動している可能性があります。")

# アプリ起動方法を表示
st.sidebar.markdown("""
---
### アプリの起動方法

ターミナルで以下のコマンドを実行: 
```
pip install streamlit pandas numpy plotly yfinance
streamlit run stock_analyzer.py
```
""")

# スクリーン幅を取得するためのJavaScript
st.markdown("""
<script>
    // スクリーン幅をセッションステートに保存
    const screenWidth = window.innerWidth;
    const setWidth = () => {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: screenWidth
        }, '*');
    }
    window.addEventListener('load', setWidth);
</script>
""", unsafe_allow_html=True)