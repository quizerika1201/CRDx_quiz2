import streamlit as st
import pandas as pd
import random

# ページ設定
st.set_page_config(page_title="検査学 資格試験対策クイズ", page_icon="🔬", layout="centered")

# --- CSS設定（UI調整） ---
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
#stDecoration {display:none;}
footer {visibility: hidden;}
header {visibility: hidden;}
header[data-testid="stHeader"] {visibility: visible; background-color: transparent;}
header > div > button {visibility: visible;}
button[aria-label="Open menu"] {visibility: visible;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("CRDx アセスメント対策クイズ")
st.write("カテゴリー別出題＆弱点克服モード（MAX10問）")

# --- Googleスプレッドシートからのデータ読み込み設定 ---
@st.cache_data(ttl=60)
def load_questions_from_sheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("CRDx_quiz_db")
        sheet = spreadsheet.worksheet("Questions")
        
        rows = sheet.get_all_values()
        
        if len(rows) < 2:
            return pd.DataFrame()
        
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        return df
        
    except Exception as e:
        st.error(f"スプレッドシートの読み込みに失敗しました。設定を確認してください。\nエラー: {e}")
        return pd.DataFrame()

df_questions = load_questions_from_sheet()

if df_questions.empty:
    st.warning("問題データが読み込まれていません。スプレッドシートの設定を確認してください。")
    st.stop()

# --- セッション状態の初期化 ---
if "mode" not in st.session_state:
    st.session_state.mode = "normal"
if "quiz_list" not in st.session_state:
    st.session_state.quiz_list = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "wrong_questions" not in st.session_state:
    st.session_state.wrong_questions = []
if "answered_current" not in st.session_state:
    st.session_state.answered_current = False
if "user_choice" not in st.session_state:
    st.session_state.user_choice = None
if "balloons_shown" not in st.session_state:
    st.session_state.balloons_shown = False

def init_quiz(selected_category="すべて"):
    for key in list(st.session_state.keys()):
        if key.startswith("shuffled_options_"):
            del st.session_state[key]
            
    if selected_category == "復習":
        st.session_state.mode = "retry"
        wrong_ids = list(set([str(x) for x in st.session_state.wrong_questions]))
        source_df = df_questions[df_questions['id'].astype(str).isin(wrong_ids)]
        questions = source_df.to_dict(orient="records")
        random.shuffle(questions)
    else:
        if selected_category == "すべて":
            st.session_state.mode = "normal"
            source_df = df_questions
            st.session_state.wrong_questions = []
        else:
            st.session_state.mode = f"category_{selected_category}"
            source_df = df_questions[df_questions['category'] == selected_category]
        
        questions = source_df.to_dict(orient="records")
        random.shuffle(questions)
        
        if len(questions) > 10:
            questions = questions[:10]
        
    st.session_state.quiz_list = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answered_current = False
    st.session_state.user_choice = None
    st.session_state.balloons_shown = False

# --- サイドバー（メニュー） ---
st.sidebar.header("📌 メニュー")

if st.sidebar.button("🏠 ホームに戻る"):
    st.session_state.quiz_list = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answered_current = False
    st.session_state.user_choice = None
    st.session_state.balloons_shown = False
    st.rerun()

wrong_count = len(set(st.session_state.wrong_questions))
if st.sidebar.button(f"⚠️ 間違えた問題だけ復習 ({wrong_count}問)", disabled=(wrong_count == 0)):
    init_quiz(selected_category="復習")
    st.rerun()

# --- クイズ画面の本体 ---
if not st.session_state.quiz_list:
    st.markdown("### 🌸 クイズメニューへようこそ！")
    st.write("出題範囲を選んでスタートしてください。（最大10問/回）")
    
    categories = ["すべて"] + list(df_questions['category'].dropna().unique())
    selected_cat = st.selectbox("🎯 出題カテゴリーを選択:", categories)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 クイズ開始", use_container_width=True):
            init_quiz(selected_category=selected_cat)
            st.rerun()
            
    with col2:
        wrong_count = len(set(st.session_state.wrong_questions))
        if st.button(f"⚠️ 間違えた問題の復習 ({wrong_count}問)", disabled=(wrong_count == 0), use_container_width=True):
            init_quiz(selected_category="復習")
            st.rerun()
            
else:
    total_q = len(st.session_state.quiz_list)
    curr_idx = st.session_state.current_index
    
    if curr_idx < total_q:
        q_data = st.session_state.quiz_list[curr_idx]
        
        st.progress((curr_idx) / total_q)
        st.markdown(f"### 問題 {curr_idx + 1} / {total_q} (カテゴリー: {q_data.get('category', '一般')})")
        st.markdown(f"**Q. {q_data['question']}**")
        
        shuffle_key = f"shuffled_options_{curr_idx}"
        
        if shuffle_key not in st.session_state:
            raw_options = [
                q_data.get('option1', ''),
                q_data.get('option2', ''),
                q_data.get('option3', ''),
                q_data.get('option4', '')
            ]
            valid_options = [opt for opt in raw_options if opt and str(opt).strip() != '']
            
            options_with_status = [(opt, opt == q_data['answer']) for opt in valid_options]
            random.shuffle(options_with_status)
            st.session_state[shuffle_key] = options_with_status

        options_with_status = st.session_state[shuffle_key]
        options = [item[0] for item in options_with_status]
        correct_ans = next(item[0] for item in options_with_status if item[1])
        
        user_choice = st.radio("選択肢を選んでください:", options, key=f"radio_{curr_idx}", index=None if not st.session_state.answered_current else options.index(st.session_state.user_choice))
        
        if not st.session_state.answered_current:
            if st.button("回答する"):
                if user_choice is None:
                    st.warning("選択肢を選んでください。")
                else:
                    st.session_state.answered_current = True
                    st.session_state.user_choice = user_choice
                    correct_ans = q_data['answer']
                    if user_choice == correct_ans:
                        st.session_state.score += 1
                        if q_data['id'] in st.session_state.wrong_questions:
                            st.session_state.wrong_questions = [q_id for q_id in st.session_state.wrong_questions if str(q_id) != str(q_data['id'])]
                    else:
                        if str(q_data['id']) not in [str(x) for x in st.session_state.wrong_questions]:
                            st.session_state.wrong_questions.append(q_data['id'])
                    st.rerun()
        else:
            correct_ans = q_data['answer']
            if st.session_state.user_choice == correct_ans:
                st.success("🎉 正解です！")
            else:
                st.error(f"❌ 不正解です。（あなたの回答: {st.session_state.user_choice}）")
                st.info(f"**正解:** {correct_ans}")
            
            st.markdown(f"**【解説】**\n{q_data['explanation']}")
            
            if st.button("次の問題へ ➡️"):
                st.session_state.current_index += 1
                st.session_state.answered_current = False
                st.session_state.user_choice = None
                st.rerun()
    else:
        st.header("🎯 クイズ終了！お疲れ様でした！")
        st.metric(label="今回の結果", value=f"{st.session_state.score} / {total_q} 問正解", delta=f"正答率: {(st.session_state.score/total_q)*100:.1f}%")
        
        # ★全問正解（スコアが総問題数と一致し、かつ問題数が1問以上）のときだけ風船を出す
        if st.session_state.score == total_q and total_q > 0:
            st.success("素晴らしい！全問正解です！パーフェクト達成！")
            if not st.session_state.balloons_shown:
                st.balloons()
                st.session_state.balloons_shown = True
        else:
            wrong_count_end = len(set(st.session_state.wrong_questions))
            if wrong_count_end > 0:
                st.warning(f"今回は {wrong_count_end} 問の間違いがありました。")
                if st.button("⚠️ 間違えた問題だけをもう一度解く"):
                    init_quiz(selected_category="復習")
                    st.rerun()
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 もう一度最初から解く"):
                init_quiz(selected_category="すべて")
                st.rerun()
        with col2:
            if st.button("🏠 トップ画面（ホーム）に戻る"):
                st.session_state.quiz_list = []
                st.session_state.current_index = 0
                st.session_state.score = 0
                st.session_state.answered_current = False
                st.session_state.user_choice = None
                st.session_state.balloons_shown = False
                st.rerun()
