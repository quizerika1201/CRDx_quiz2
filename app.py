import streamlit as st
import pandas as pd
import random

# ページ設定
st.set_page_config(page_title="検査学 資格試験対策クイズ", page_icon="🔬", layout="centered")

st.title("🔬 検査学 資格試験対策クイズアプリ")
st.write("スプレッドシート連動型・ランダム出題＆弱点克服モード")

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
        
        # スプレッドシート名とタブ名で取得
        spreadsheet = client.open("CRDx_quiz_db")
        sheet = spreadsheet.worksheet("Questions")
        
        # 取得できたすべての行を取り出す
        rows = sheet.get_all_values()
        
        # デバッグ用表示
        #st.warning(f"【デバッグ】スプレッドシートから取得できた行数: {len(rows)} 行")
        #if len(rows) > 0:
            #st.info(f"【デバッグ】1行目の内容（見出し）: {rows[0]}")
        
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

def init_quiz(retry_mode=False):
    st.session_state.mode = "retry" if retry_mode else "normal"
    if retry_mode:
        source_df = df_questions[df_questions['id'].isin(st.session_state.wrong_questions)]
    else:
        source_df = df_questions
        st.session_state.wrong_questions = []
    
    questions = source_df.to_dict(orient="records")
    random.shuffle(questions)
    st.session_state.quiz_list = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answered_current = False
    st.session_state.user_choice = None

# --- サイドバー（メニュー） ---
st.sidebar.header("📌 メニュー")

if st.sidebar.button("🏠 ホームに戻る"):
    st.session_state.quiz_list = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answered_current = False
    st.session_state.user_choice = None
    st.session_state.wrong_questions = []
    st.rerun()

if st.sidebar.button("🔄 すべての問題からランダム出題で開始"):
    init_quiz(retry_mode=False)
    st.rerun()

# --- 常に表示する「間違えた問題の復習」ボタン ---
wrong_count = len(st.session_state.wrong_questions)
if st.sidebar.button(f"⚠️ 間違えた問題だけ復習する ({wrong_count}問)", disabled=(wrong_count == 0)):
    init_quiz(retry_mode=True)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 **使い方**\n1. スプレッドシート側で問題を編集・追加すると、アプリを再読み込みするだけで反映されます。\n2. iPhoneのSafariやPCからブラウザでアクセスできます。")

# --- クイズ画面の本体 ---
if not st.session_state.quiz_list:
    st.info("左側のサイドバーから「すべての問題からランダム出題で開始」をクリックしてクイズを始めてください！")
else:
    total_q = len(st.session_state.quiz_list)
    curr_idx = st.session_state.current_index
    
    if curr_idx < total_q:
        q_data = st.session_state.quiz_list[curr_idx]
        
        st.progress((curr_idx) / total_q)
        st.markdown(f"### 問題 {curr_idx + 1} / {total_q} (モード: {'復習モード' if st.session_state.mode=='retry' else '通常ランダム'})")
        st.markdown(f"**Q. {q_data['question']}**")
        
        options = [q_data['option1'], q_data['option2'], q_data['option3'], q_data['option4']]
        
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
                    else:
                        if q_data['id'] not in st.session_state.wrong_questions:
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
        st.balloons()
        st.header("🎯 クイズ終了！お疲れ様でした！")
        st.metric(label="今回の結果", value=f"{st.session_state.score} / {total_q} 問正解", delta=f"正答率: {(st.session_state.score/total_q)*100:.1f}%")
        
        if st.session_state.wrong_questions:
            st.warning(f"今回は {len(st.session_state.wrong_questions)} 問の間違いがありました。")
            if st.button("⚠️ 間違えた問題だけをもう一度解く"):
                init_quiz(retry_mode=True)
                st.rerun()
        else:
            st.success("素晴らしい！全問正解です！パーフェクト達成！")
            
        if st.button("🏠 最初からやり直す"):
            init_quiz(retry_mode=False)
            st.rerun()
