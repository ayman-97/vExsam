import streamlit as st
import sqlite3

DB_NAME = "exam_simulator.db"

st.set_page_config(page_title="المراجعة - الامتحان الوطني الافتراضي", page_icon="📖", layout="wide")

# تنسيق القائمة الجانبية بالعربي
st.markdown("""
<style>
[data-testid="stSidebar"] {
    direction: rtl;
    text-align: right;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
    direction: rtl;
    padding-top: 15px;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    direction: rtl;
    text-align: right;
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {
    font-size: 16px !important;
}
.sidebar-title {
    text-align: center;
    padding: 15px 10px;
    border-bottom: 1px solid #3e3e42;
    margin-bottom: 15px;
}
.sidebar-title h3 {
    background: linear-gradient(135deg, #ff4b4b, #ff8f00);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.3rem;
    font-weight: 900;
    margin: 0;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="sidebar-title"><h3>📝 الامتحان الوطني</h3></div>', unsafe_allow_html=True)

# ==========================================
# CSS للتنسيق
# ==========================================
st.markdown("""
<style>
/* اتجاه النص من اليمين لليسار */
.main .block-container {
    direction: rtl;
    text-align: right;
}
/* بطاقة السؤال */
.q-card {
    background: #1a1a2e;
    border: 1px solid #3e3e42;
    border-radius: 12px;
    padding: 20px 25px;
    margin-bottom: 15px;
}
.q-card:hover { border-color: #ff4b4b; }
.q-num {
    color: #ff4b4b;
    font-weight: bold;
    font-size: 14px;
    margin-bottom: 8px;
}
.q-text {
    color: #e0e0e0;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 12px;
    direction: rtl;
    text-align: right;
}
.q-passage {
    background: rgba(255,193,7,0.08);
    border-right: 4px solid #ffc107;
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 12px;
    direction: rtl;
    text-align: right;
    color: #ccc;
    font-size: 14px;
    max-height: 200px;
    overflow-y: auto;
}
.opts-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 10px;
}
.opt {
    background: #16213e;
    border: 1px solid #3e3e42;
    border-radius: 8px;
    padding: 10px 15px;
    color: #aaa;
    font-size: 15px;
}
.opt.correct {
    border-color: #27ae60;
    background: rgba(39,174,96,0.15);
    color: #2ecc71;
    font-weight: bold;
}
/* عداد */
.section-badge {
    background: linear-gradient(135deg, #ff4b4b, #ff8f00);
    color: white;
    padding: 6px 18px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 14px;
    display: inline-block;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# جلب البيانات
# ==========================================
@st.cache_data
def get_subjects():
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute("SELECT DISTINCT subject FROM Questions ORDER BY subject").fetchall()
    return [r[0] for r in rows]

@st.cache_data
def get_sections(subject):
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute("SELECT DISTINCT section FROM Questions WHERE subject=? ORDER BY section", (subject,)).fetchall()
    return [r[0] for r in rows]

@st.cache_data
def get_questions(subject, section):
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute(
            "SELECT id, passage_text, question_text, option_a, option_b, option_c, option_d, correct_option FROM Questions WHERE subject=? AND section=? ORDER BY id",
            (subject, section)
        ).fetchall()
    return rows

# ==========================================
# الواجهة
# ==========================================

# الشعار
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    st.image("logo.png", width=300)

st.markdown("""
<div style="text-align:center; margin-bottom:30px;">
    <h1 style="
        background: linear-gradient(135deg, #ff4b4b, #ff8f00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem; font-weight: 900; margin: 0;
    ">📖 وضع المراجعة</h1>
    <p style="color:#888; font-size:14px;">راجع جميع الأسئلة مع الإجابات الصحيحة</p>
</div>
""", unsafe_allow_html=True)

# اختيار المادة
subjects = get_subjects()
if not subjects:
    st.error("قاعدة البيانات فارغة. قم بإضافة أسئلة أولاً.")
    st.stop()

selected_subject = st.selectbox("📚 اختر المادة:", subjects, key="rev_subject")

# جلب الأقسام
sections = get_sections(selected_subject)

if not sections:
    st.warning("لا توجد أقسام لهذه المادة.")
    st.stop()

# إظهار/إخفاء الإجابات
show_answers = st.toggle("👁️ إظهار الإجابات الصحيحة", value=False)

st.divider()

# عرض الأسئلة حسب القسم
total_all = 0
for sec in sections:
    questions = get_questions(selected_subject, sec)
    total_all += len(questions)
    
    with st.expander(f"📂 {sec}  ({len(questions)} سؤال)", expanded=False):
        for i, q in enumerate(questions, 1):
            q_id, passage, q_text, opt_a, opt_b, opt_c, opt_d, correct = q
            
            # بناء HTML للسؤال
            html = f'<div class="q-card">'
            html += f'<div class="q-num">سؤال {i}</div>'
            
            if passage and passage.strip():
                html += f'<div class="q-passage">{passage}</div>'
            
            html += f'<div class="q-text">{q_text}</div>'
            html += '<div class="opts-grid">'
            
            options = [("A", opt_a), ("B", opt_b), ("C", opt_c), ("D", opt_d)]
            for letter, text in options:
                is_correct = (text == correct) and show_answers
                cls = "opt correct" if is_correct else "opt"
                mark = " ✅" if is_correct else ""
                html += f'<div class="{cls}">{letter}) {text}{mark}</div>'
            
            html += '</div>'
            
            if show_answers:
                html += f'<div style="color:#2ecc71; font-size:13px; margin-top:5px;">✔ الإجابة: {correct}</div>'
            
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

# إحصائيات
st.divider()
st.markdown(f"""
<div style="text-align:center; padding:15px;">
    <span class="section-badge">📊 إجمالي الأسئلة: {total_all}</span>
    &nbsp;&nbsp;
    <span class="section-badge">📂 عدد الأقسام: {len(sections)}</span>
</div>
""", unsafe_allow_html=True)

# التوقيع
st.markdown("""
    <hr style="margin-top:40px; border:none; border-top:1px solid #3e3e42;">
    <div style="text-align:center; padding:15px 0 10px; color:#888; font-size:14px;">
        Developed by <span style="color:#ff4b4b; font-weight:bold;">Aymen N. Hamad</span>
    </div>
""", unsafe_allow_html=True)
