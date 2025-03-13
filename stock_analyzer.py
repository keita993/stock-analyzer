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
            
            # 上昇日と下落日の買い売り
            up_days = merged_df[merged_df['日経平均'].diff() > 0]
            down_days = merged_df[merged_df['日経平均'].diff() < 0]
            
            buy_on_up = up_days['買い金額'].sum()
            sell_on_up = up_days['売り金額'].sum()
            buy_on_down = down_days['買い金額'].sum()
            sell_on_down = down_days['売り金額'].sum()
            
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