import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import time
import math

DB_NAME = "exam_simulator.db"

# ==========================================
# 1. تهيئة قاعدة البيانات والأسئلة
# ==========================================

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                section TEXT DEFAULT 'عام',
                passage_text TEXT DEFAULT '',
                question_text TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_option TEXT
            )
        ''')
        conn.commit()

def get_balanced_questions(subject, total_limit):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # جلب الأقسام المتاحة ديناميكياً من قاعدة البيانات
        cursor.execute('SELECT DISTINCT section FROM Questions WHERE subject=?', (subject,))
        sections = [r[0] for r in cursor.fetchall()]
        if not sections:
            return []
        q_per = total_limit // len(sections)
        rem = total_limit % len(sections)
        qs = []
        selected_ids = set()
        # الجولة الأولى: توزيع متوازن على الأقسام
        for i, sec in enumerate(sections):
            limit = q_per + (1 if i < rem else 0)
            if selected_ids:
                placeholders = ','.join('?' * len(selected_ids))
                cursor.execute(f'SELECT * FROM Questions WHERE subject=? AND section=? AND id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?', (subject, sec, *selected_ids, limit))
            else:
                cursor.execute('SELECT * FROM Questions WHERE subject=? AND section=? ORDER BY RANDOM() LIMIT ?', (subject, sec, limit))
            rows = cursor.fetchall()
            for r in rows:
                selected_ids.add(r[0])
            qs.extend(rows)
        # جولة التعويض: إذا لم يكتمل العدد المطلوب، نجلب أسئلة إضافية من أي قسم
        deficit = total_limit - len(qs)
        if deficit > 0 and selected_ids:
            placeholders = ','.join('?' * len(selected_ids))
            cursor.execute(f'SELECT * FROM Questions WHERE subject=? AND id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?', (subject, *selected_ids, deficit))
            qs.extend(cursor.fetchall())
    return qs

def save_answer(q_id):
    st.session_state.user_answers[q_id] = st.session_state[f"q_{q_id}"]

def finish_exam():
    if st.session_state.get('phase') == 'results': return
    score = 0
    incorrect = []
    for q in st.session_state.questions:
        q_id, q_txt, correct, sec = q[0], q[4], q[9], q[2]
        ans = st.session_state.user_answers.get(q_id)
        if ans == correct: score += 1
        else: incorrect.append({'sec': sec, 'q': q_txt, 'user': ans if ans else "لم يجب", 'right': correct})
    st.session_state.update({'raw_score': score, 'incorrect_answers': incorrect, 'phase': 'results'})

# ==========================================
# 2. الحل الهندسي للمؤقت والواجهة (CSS & JS)
# ==========================================

def inject_exam_engine(end_ts):
    dark = st.session_state.get('dark_mode', True)
    radio_bg = "#1a1a1b" if dark else "#f0f2f6"
    radio_border = "#3e3e42" if dark else "#dee2e6"
    radio_text = "white" if dark else "#1a1a2e"
    sel_bg = "#2d1616" if dark else "#ffe0e0"
    # CSS فقط عبر st.markdown — يعمل بشكل طبيعي
    st.markdown(f"""
        <style>
        /* اتجاه النص من اليمين لليسار */
        .main .block-container {{
            direction: rtl;
            text-align: right;
        }}
        /* إخفاء دوائر الراديو */
        div[role="radiogroup"] > label > div:first-child {{ display: none !important; }}
        div[role="radiogroup"] svg {{ display: none !important; }}
        div[role="radiogroup"] > label > div:first-of-type {{
            display: none !important; width: 0 !important; height: 0 !important;
            overflow: hidden !important; margin: 0 !important; padding: 0 !important;
        }}
        [data-testid="stRadio"] [role="radiogroup"] label > div:first-of-type {{ display: none !important; }}

        /* تحويل الخيارات إلى بطاقات */
        div[role="radiogroup"] > label {{
            background-color: {radio_bg} !important;
            border: 1px solid {radio_border} !important;
            padding: 15px 25px !important;
            border-radius: 10px !important;
            margin-bottom: 8px !important;
            width: 100% !important;
            cursor: pointer !important;
            color: {radio_text} !important;
            display: block !important;
            direction: rtl !important;
            text-align: right !important;
        }}
        div[role="radiogroup"] > label[aria-checked="true"] {{
            border: 2px solid #ff4b4b !important;
            background-color: {sel_bg} !important;
            box-shadow: 0 4px 12px rgba(255, 75, 75, 0.4) !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # المؤقت + تمييز الإجابات عبر components.html
    components.html(f"""
    <script>
    (function() {{
        var pd = window.parent.document;
        var ps = window.parent.sessionStorage;
        var KEY = 'vexsam_end';
        var serverEnd = {end_ts} * 1000;

        var stored = parseInt(ps.getItem(KEY) || '0');
        if (serverEnd > stored) ps.setItem(KEY, serverEnd);
        var endTime = parseInt(ps.getItem(KEY));

        // إنشاء div المؤقت في صفحة الأب إن لم يكن موجوداً
        var el = pd.getElementById('_vex_timer_');
        if (!el) {{
            el = pd.createElement('div');
            el.id = '_vex_timer_';
            el.style.cssText = [
                'position:fixed', 'top:85px', 'right:25px', 'z-index:999999',
                'background:#ff4b4b', 'color:white', 'padding:12px 20px',
                'border-radius:8px', 'font-weight:bold', 'font-family:monospace',
                'font-size:26px', 'border:2px solid white',
                'box-shadow:0 6px 20px rgba(0,0,0,0.5)',
                'min-width:110px', 'text-align:center'
            ].join(';');
            pd.body.appendChild(el);
        }}

        // ── تمييز الخيار المحدد بلون أحمر ────────────────────────────
        function highlightRadio() {{
            var labels = pd.querySelectorAll('div[role="radiogroup"] > label');
            for (var i = 0; i < labels.length; i++) {{
                var lbl = labels[i];
                var inp = lbl.querySelector('input[type="radio"]');
                if (inp && inp.checked) {{
                    lbl.style.border          = '2px solid #ff4b4b';
                    lbl.style.backgroundColor = '{sel_bg}';
                    lbl.style.boxShadow       = '0 4px 12px rgba(255,75,75,0.4)';
                }} else {{
                    lbl.style.border          = '1px solid {radio_border}';
                    lbl.style.backgroundColor = '{radio_bg}';
                    lbl.style.boxShadow       = 'none';
                }}
            }}
        }}
        if (window._hl) clearInterval(window._hl);
        window._hl = setInterval(highlightRadio, 200);

        // ── المؤقت ───────────────────────────────────────────────────
        function tick() {{
            var e = pd.getElementById('_vex_timer_');
            if (!e) return;
            var rem = endTime - Date.now();
            if (rem <= 0) {{
                e.textContent = '00:00';
                ps.removeItem(KEY);
                clearInterval(window._vt);
                var btns = pd.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {{
                    if (btns[i].innerText.includes('\u0625\u0646\u0647\u0627\u0621') ||
                        btns[i].innerText.includes('\u062a\u0633\u0644\u064a\u0645')) {{
                        btns[i].click(); break;
                    }}
                }}
                return;
            }}
            var m = Math.floor(rem / 60000);
            var s = Math.floor((rem % 60000) / 1000);
            e.textContent =
                (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }}
        if (window._vt) clearInterval(window._vt);
        window._vt = setInterval(tick, 500);
        tick();
    }})();
    </script>
    """, height=0)

# ==========================================
# 3. مراحل التطبيق
# ==========================================

def phase_setup():
    # مسح المؤقت من صفحة الأب ومن sessionStorage بشكل فعلي
    components.html("""
    <script>
    (function() {
        window.parent.sessionStorage.removeItem('vexsam_end');
        var el = window.parent.document.getElementById('_vex_timer_');
        if (el) el.remove();
        if (window.parent._vt) { clearInterval(window.parent._vt); window.parent._vt = null; }
    })();
    </script>
    """, height=0)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.image("logo.png", width=300)
    st.markdown("""
        <div style="text-align:center; padding:0 0 10px;">
            <h1 style="
                background: linear-gradient(135deg, #ff4b4b, #ff8f00);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 2.4rem;
                font-weight: 900;
                margin: 0;
                direction: rtl;
            ">الامتحان الوطني الافتراضي</h1>
            <p style="color:#888; font-size:14px; margin-top:5px;">منصة محاكاة الاختبارات الوطنية</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("اسم الطالب:")
        p_mark = c2.number_input("النجاح %:", 0, 100, 50)
        c3, c4 = st.columns(2)
        sub = c3.selectbox("المادة:", ['اللغة الإنجليزية', 'اللغة العربية', 'الحاسوب'])
        num = c4.selectbox("الأسئلة:", [20, 40, 60, 80, 100])
    
    if st.button("بدء الامتحان", type="primary", use_container_width=True):
        if not name: return st.error("أدخل الاسم.")
        qs = get_balanced_questions(sub, num)
        if not qs: return st.error("قاعدة البيانات فارغة.")
        st.session_state.update({
            'student_name': name, 'pass_mark': p_mark, 'subject': sub, 
            'questions': qs, 'current_q_index': 0, 'user_answers': {}, 
            'phase': 'exam', 'end_time': time.time() + 3600
        })
        st.rerun()

def phase_exam():
    dark = st.session_state.get('dark_mode', True)
    txt_color = '#ffffff' if dark else '#1a1a2e'
    passage_color = '#e0e0e0' if dark else '#333'
    passage_bg = 'rgba(255,193,7,0.1)' if dark else 'rgba(255,193,7,0.15)'
    # التحقق من الوقت في السيرفر
    if time.time() > st.session_state.end_time:
        finish_exam()
        st.rerun()

    inject_exam_engine(st.session_state.end_time)
    
    idx = st.session_state.current_q_index
    total = len(st.session_state.questions)
    q = st.session_state.questions[idx]
    
    q_id, sec, passage, txt = q[0], q[2], q[3], q[4]
    opts = [q[5], q[6], q[7], q[8]]

    # Sidebar
    st.sidebar.title("خريطة الأسئلة")
    st.sidebar.caption(f"الطالب: {st.session_state.student_name}")
    cols = st.sidebar.columns(4)
    for i in range(total):
        is_ans = st.session_state.questions[i][0] in st.session_state.user_answers
        if cols[i%4].button(f"{'✅' if is_ans else ''}{i+1}", key=f"nav_{i}", type="primary" if i == idx else "secondary"):
            st.session_state.current_q_index = i
            st.rerun()
            
    if st.sidebar.button("تسليم الامتحان", type="primary", use_container_width=True):
        finish_exam()
        st.rerun()

    # Main Area
    st.caption(f"القسم: {sec}")
    st.subheader(f"سؤال {idx + 1} من {total}")
    if passage:
        st.markdown(f'<div style="background:{passage_bg}; border-right:5px solid #ffc107; padding:20px; border-radius:8px; direction:ltr; text-align:left; margin-bottom:20px; color:{passage_color};">{passage}</div>', unsafe_allow_html=True)

    dir_css = "ltr" if st.session_state.subject == 'اللغة الإنجليزية' else "rtl"
    st.markdown(f"<div style='direction:{dir_css}; text-align:right; font-size:22px; margin-bottom:20px; color:{txt_color};'><b>{txt}</b></div>", unsafe_allow_html=True)

    ans = st.session_state.user_answers.get(q_id)
    st.radio("Options", opts, index=opts.index(ans) if ans in opts else None, key=f"q_{q_id}", on_change=save_answer, args=(q_id,), label_visibility="collapsed")

    st.divider()
    c1, _, c3 = st.columns([1, 1, 1])
    if idx > 0 and c1.button("السابق", use_container_width=True):
        st.session_state.current_q_index -= 1
        st.rerun()
    if idx < total - 1:
        if c3.button("التالي", type="primary", use_container_width=True):
            st.session_state.current_q_index += 1
            st.rerun()
    else:
        if c3.button("إنهاء وتسليم", type="primary", use_container_width=True):
            finish_exam()
            st.rerun()

def phase_results():
    st.title("النتيجة النهائية")
    pct = (st.session_state.raw_score / len(st.session_state.questions)) * 100
    st.metric(st.session_state.student_name, f"{pct:.2f} %")
    if pct >= st.session_state.pass_mark: st.success("اجتياز")
    else: st.error("إخفاق")
    
    for idx, e in enumerate(st.session_state.incorrect_answers, 1):
        with st.expander(f"خطأ {idx}: {e['q']}"):
            st.error(f"إجابتك: {e['user']}")
            st.success(f"الصحيحة: {e['right']}")
    
    if st.button("امتحان جديد"):
        st.session_state.clear()
        st.rerun()

def main():
    st.set_page_config(page_title="الامتحان الوطني الافتراضي", page_icon="📝", layout="wide")
    
    # تهيئة الوضع (داكن افتراضياً)
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True

    # ألوان الوضع الداكن والفاتح
    if st.session_state.dark_mode:
        bg = "#0e1117"; card_bg = "#1a1a1b"; border = "#3e3e42"
        text = "#ffffff"; text2 = "#e0e0e0"; muted = "#888"
        selected_bg = "#2d1616"; sidebar_bg = "#0e1117"; sidebar_text = "#ffffff"
        radio_bg = "#1a1a1b"; radio_text = "white"
    else:
        bg = "#ffffff"; card_bg = "#f8f9fa"; border = "#dee2e6"
        text = "#1a1a2e"; text2 = "#333333"; muted = "#666"
        selected_bg = "#ffe0e0"; sidebar_bg = "#f0f2f6"; sidebar_text = "#1a1a2e"
        radio_bg = "#f0f2f6"; radio_text = "#1a1a2e"

    # CSS الرئيسي مع دعم الوضعين
    st.markdown(f"""
    <style>
    /* القائمة الجانبية RTL */
    [data-testid="stSidebar"] {{
        direction: rtl;
        text-align: right;
        background-color: {sidebar_bg} !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {sidebar_bg} !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {sidebar_text} !important;
    }}
    [data-testid="stSidebar"] .stButton button {{
        color: {sidebar_text} !important;
        border-color: {border} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
        direction: rtl;
        padding-top: 15px;
    }}
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
        direction: rtl;
        text-align: right;
        font-size: 16px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {{
        font-size: 16px !important;
    }}
    /* عنوان القائمة الجانبية */
    .sidebar-title {{
        text-align: center;
        padding: 15px 10px;
        border-bottom: 1px solid {border};
        margin-bottom: 15px;
    }}
    .sidebar-title h3 {{
        background: linear-gradient(135deg, #ff4b4b, #ff8f00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.3rem;
        font-weight: 900;
        margin: 0;
    }}
    /* ألوان الوضع */
    .main .block-container {{
        color: {text} !important;
    }}
    .stApp {{
        background-color: {bg} !important;
    }}
    .stApp [data-testid="stHeader"] {{
        background-color: {bg} !important;
    }}
    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {{
        color: {text} !important;
    }}
    .stCaption, .stCaption p {{
        color: {muted} !important;
    }}
    hr {{
        border-color: {border} !important;
    }}
    /* أزرار */
    .stButton button {{
        color: {text} !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f'<div class="sidebar-title"><h3>📝 الامتحان الوطني</h3></div>', unsafe_allow_html=True)

    # زر تبديل الوضع
    theme_label = "☀️ الوضع النهاري" if st.session_state.dark_mode else "🌙 الوضع الليلي"
    if st.sidebar.button(theme_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    # تغيير أسماء الصفحات في القائمة الجانبية من الإنجليزي للعربي
    components.html("""
    <script>
    (function(){
        var map = {
            'app': '📝 الامتحان',
            '2   المراجعة': '📖 المراجعة',
            'المراجعة': '📖 المراجعة'
        };
        function rename(){
            var pd = window.parent.document;
            var links = pd.querySelectorAll('[data-testid="stSidebarNav"] a span');
            for(var i=0;i<links.length;i++){
                var txt = links[i].textContent.trim().toLowerCase();
                for(var key in map){
                    if(txt === key.toLowerCase() || txt.includes(key.toLowerCase())){
                        links[i].textContent = map[key];
                        break;
                    }
                }
            }
        }
        rename();
        setInterval(rename, 500);
    })();
    </script>
    """, height=0)
    init_db()
    if 'phase' not in st.session_state: st.session_state.phase = 'setup'
    if st.session_state.phase == 'setup': phase_setup()
    elif st.session_state.phase == 'exam': phase_exam()
    elif st.session_state.phase == 'results': phase_results()

    # التوقيع في أسفل الصفحة
    st.markdown("""
        <hr style="margin-top:60px; border:none; border-top:1px solid #3e3e42;">
        <div style="text-align:center; padding:15px 0 10px; color:#888; font-size:14px;">
            Developed by <span style="color:#ff4b4b; font-weight:bold;">Aymen N. Hamad</span>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__": main()