import streamlit as st
import pandas as pd
import altair as alt

# --- 1. タイトル ---
st.title('産業別・年齢構成グラフ 📊')

# --- 2. データの読み込み ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel('22年労働力調査_DB形式.xlsx', sheet_name='データベース')
    except Exception as e:
        return None, f"Excelファイルの読み込みに失敗しました: {e}"

    # 文字列の掃除（空白削除）
    for col in ['性別', '年齢', '産業']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # 数字のお掃除
    def clean_number(x):
        s = str(x)
        s = s.replace(',', '') 
        s = s.replace('-', '0') 
        s = s.strip()
        try:
            return float(s)
        except ValueError:
            return 0

    if '人数_万人' in df.columns:
        df['人数_万人'] = df['人数_万人'].apply(clean_number)
    
    return df, None

df, error_msg = load_data()

if error_msg:
    st.error(error_msg)
    st.stop()

# --- 3. サイドバー ---
st.sidebar.header('表示設定')
industry_list = df['産業'].unique()
selected_industry = st.sidebar.selectbox('産業を選んでください', industry_list)

# --- 4. データの加工 ---
df_filtered = df[df['産業'] == selected_industry]

# 数値計算
try:
    row_all = df_filtered[(df_filtered['年齢'] == '全年齢') & (df_filtered['性別'].str.contains('計|合計|総数'))]
    row_working = df_filtered[(df_filtered['年齢'] == '15～64歳') & (df_filtered['性別'].str.contains('計|合計|総数'))]
    
    val_all = row_all['人数_万人'].sum() if not row_all.empty else 0
    val_working = row_working['人数_万人'].sum() if not row_working.empty else 0
except:
    val_all = 0
    val_working = 0

# グラフ用データ
exclude_ages = ['全年齢', '15～64歳']
df_chart_source = df_filtered[~df_filtered['年齢'].isin(exclude_ages)].copy()

df_gender = df_chart_source[df_chart_source['性別'].isin(['男性', '女性'])].copy()
df_total = df_chart_source[df_chart_source['性別'].str.contains('計|合計|総数')].copy()

# --- 5. 表示エリア ---

# (1) 数値表示
col1, col2 = st.columns(2)
with col1:
    st.metric(label="全年齢（実数）", value=f"{int(val_all):,} 万人")
with col2:
    st.metric(label="15～64歳（実数）", value=f"{int(val_working):,} 万人")

st.markdown("---")

# (2) グラフ1：年齢別・男女計人数構成（紫色） ★先に移動しました
st.subheader('■ 年齢別・男女計人数構成')

try:
    if df_total.empty:
        st.warning('⚠️ 男女計データが見つかりません。')
    else:
        base_total = alt.Chart(df_total).encode(
            x=alt.X('年齢', sort=None, title='年齢階級'),
            y=alt.Y('人数_万人', title='人数（万人）')
        )
        bars_total = base_total.mark_bar(color='#800080').encode(
            tooltip=['年齢', '人数_万人']
        )
        text_total = base_total.mark_text(dy=-10, color='black', fontWeight='bold').encode(
            text=alt.Text('人数_万人', format=',.0f')
        )
        st.altair_chart((bars_total + text_total).properties(height=400), use_container_width=True)

except Exception as e:
    st.error(f"グラフ1描画エラー: {e}")


# (3) グラフ2：年齢別・男女別構成（青・ピンク） ★後に移動・クリック機能追加
st.subheader('■ 年齢別・男女別構成')
st.caption("※グラフ右側の「男性」「女性」という凡例をクリックすると、表示を切り替えられます（Shiftキーを押しながらクリックで複数選択）。グラフの何もないところをダブルクリックすると元に戻ります。")

try:
    if df_gender.empty:
        st.warning('⚠️ 男女別データが見つかりません。')
    else:
        # ★インタラクション設定：凡例(legend)をクリックして選択できるようにする
        selection = alt.selection_point(fields=['性別'], bind='legend')

        base = alt.Chart(df_gender).encode(
            x=alt.X('年齢', sort=None, title='年齢階級'),
            y=alt.Y('人数_万人', title='人数（万人）'),
            order=alt.Order('性別', sort='descending'),
            # ★選択されていないものは透明度を下げる（opacity 0.1）＝ほぼ消える
            opacity=alt.condition(selection, alt.value(1), alt.value(0.1))
        ).add_params(
            selection # チャートにインタラクションを追加
        )

        # 棒グラフ
        bars = base.mark_bar().encode(
            color=alt.Color('性別', scale=alt.Scale(domain=['男性', '女性'], range=['#0000FF', '#FF69B4'])),
            tooltip=['年齢', '性別', '人数_万人']
        )

        # 数字ラベル
        text = base.mark_text(dy=0, fontWeight='bold').encode(
            text=alt.Text('人数_万人', format=',.0f'),
            color=alt.condition(
                alt.datum.性別 == '男性',
                alt.value('white'),
                alt.value('black')
            )
        )

        st.altair_chart((bars + text).properties(height=400), use_container_width=True)

except Exception as e:
    st.error(f"グラフ2描画エラー: {e}")


# (4) データテーブル
st.markdown("---")
st.subheader('■ データソース')
try:
    if not df_chart_source.empty:
        pivot_df = df_chart_source.pivot_table(
            index='年齢', columns='性別', values='人数_万人', aggfunc='sum'
        )
        cols_order = ['男女計', '男女合計', '男性', '女性']
        existing_cols = [c for c in cols_order if c in pivot_df.columns]
        other_cols = [c for c in pivot_df.columns if c not in cols_order]
        st.dataframe(pivot_df[existing_cols + other_cols])
    else:
        st.write("データがありません")
except Exception as e:
    st.error(f"テーブル表示エラー: {e}")