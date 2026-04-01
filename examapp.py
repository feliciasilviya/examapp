import streamlit as st
import sqlite3
import pandas as pd
from twilio.rest import Client
import streamlit.components.v1 as components

# ---------------- DATABASE ---------------- #
conn = sqlite3.connect("school.db", check_same_thread=False)
c = conn.cursor()

c.execute(
    """CREATE TABLE IF NOT EXISTS teachers(
    username TEXT PRIMARY KEY,
    password TEXT
)"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS students(
    id TEXT PRIMARY KEY,
    name TEXT,
    password TEXT,
    parent_phone TEXT
)"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS questions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson TEXT,
    qtype TEXT,
    question TEXT,
    a TEXT,
    b TEXT,
    c TEXT,
    d TEXT,
    answer TEXT,
    marks INTEGER
)"""
)

c.execute(
    """CREATE TABLE IF NOT EXISTS results(
    student_id TEXT,
    name TEXT,
    lesson TEXT,
    score INTEGER
)"""
)

c.execute("INSERT OR IGNORE INTO teachers VALUES ('admin','1234')")
c.execute(
    "INSERT OR IGNORE INTO students VALUES ('S001','John','1234','+919876543210')"
)
conn.commit()

# ---------------- TWILIO CONFIG ---------------- #
ACCOUNT_SID = "AC337cdfe18377ccb408fd45d449ef6b0d"
AUTH_TOKEN = "17cb73ce7e5dbe120f397ed880a3973c"
TWILIO_WHATSAPP = "whatsapp:+14155238886"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ---------------- VOICE FUNCTION ---------------- #
def voice_input():
    html_code = """
    <div>
        <button onclick="startDictation()" style="padding:8px 15px;">🎤 Speak</button>
        <p id="status"></p>
        <textarea id="voiceText" style="width:100%;height:60px;margin-top:10px;"></textarea>
    </div>

    <script>
    function startDictation() {
        if (!('webkitSpeechRecognition' in window)) {
            alert("Use Google Chrome");
            return;
        }

        var recognition = new webkitSpeechRecognition();
        recognition.lang = "en-IN";

        document.getElementById("status").innerHTML = "🎤 Listening...";

        recognition.onresult = function(event) {
            document.getElementById("voiceText").value =
                event.results[0][0].transcript;
            document.getElementById("status").innerHTML = "✅ Done";
        };

        recognition.start();
    }
    </script>
    """
    components.html(html_code, height=200)


# ---------------- LOGIN ---------------- #
st.title("🏫 AI Exam ERP System")

role = st.selectbox("Login As", ["Teacher", "Student"])
username = st.text_input("Username / ID")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if role == "Teacher":
        user = c.execute(
            "SELECT * FROM teachers WHERE username=? AND password=?",
            (username, password),
        ).fetchone()
    else:
        user = c.execute(
            "SELECT * FROM students WHERE id=? AND password=?", (username, password)
        ).fetchone()

    if user:
        st.session_state.user = user
        st.session_state.role = role
        st.success("Login Successful")
    else:
        st.error("Invalid Login")

# ---------------- LOGOUT ---------------- #
if "user" in st.session_state:
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# =====================================================
# 👩‍🏫 TEACHER PANEL
# =====================================================
if "role" in st.session_state and st.session_state.role == "Teacher":

    st.header("👩‍🏫 Teacher Panel")

    # -------- STUDENTS -------- #
    st.subheader("👨‍🎓 Manage Students")

    sid = st.text_input("Student ID")
    name = st.text_input("Student Name")
    spass = st.text_input("Password")
    phone = st.text_input("Parent WhatsApp (+91...)")

    if st.button("Add Student"):
        c.execute(
            "INSERT OR REPLACE INTO students VALUES (?,?,?,?)",
            (sid, name, spass, phone),
        )
        conn.commit()
        st.success("Student Added")

    st.dataframe(pd.read_sql_query("SELECT * FROM students", conn))

    # -------- VOICE INPUT -------- #
    st.subheader("🎤 Voice Input")
    voice_input()

    st.info("👉 Copy voice text above and paste below")

    voice_text = st.text_area("Paste Voice Text Here")

    if st.button("Use Voice"):
        st.session_state.voice_q = voice_text

    # -------- ADD QUESTION -------- #
    st.subheader("➕ Add Question")

    lesson = st.text_input("Lesson")
    qtype = st.selectbox("Type", ["MCQ", "True/False", "Fill"])

    question = st.text_area("Question", value=st.session_state.get("voice_q", ""))

    a = b = c_opt = d = ""

    if qtype == "MCQ":
        a = st.text_input("Option A")
        b = st.text_input("Option B")
        c_opt = st.text_input("Option C")
        d = st.text_input("Option D")
        answer = st.selectbox("Correct Answer", ["A", "B", "C", "D"])

    elif qtype == "True/False":
        answer = st.selectbox("Answer", ["True", "False"])

    else:
        answer = st.text_input("Correct Answer")

    marks = st.number_input("Marks", value=1)

    if st.button("Save Question"):
        c.execute(
            """
        INSERT INTO questions 
        (lesson,qtype,question,a,b,c,d,answer,marks)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
            (lesson, qtype, question, a, b, c_opt, d, answer, marks),
        )
        conn.commit()
        st.success("Question Saved")

# =====================================================
# 👨‍🎓 STUDENT PANEL
# =====================================================
if "role" in st.session_state and st.session_state.role == "Student":

    st.header("📝 Student Exam")

    student = st.session_state.user
    sid = student[0]
    name = student[1]
    phone = student[3]

    lesson = st.text_input("Enter Lesson")

    if st.button("Start Exam"):
        st.session_state.start = True

    if "start" in st.session_state:

        questions = c.execute(
            "SELECT * FROM questions WHERE lesson=?", (lesson,)
        ).fetchall()

        answers = {}

        for q in questions:
            st.write(f"### {q[3]}")

            if q[2] == "MCQ":
                ans = st.radio("", ["A", "B", "C", "D"], key=q[0])
            elif q[2] == "True/False":
                ans = st.radio("", ["True", "False"], key=q[0])
            else:
                ans = st.text_input("Answer", key=q[0])

            answers[q[0]] = (ans, q[8], q[9])

        if st.button("Submit Exam"):

            score = 0

            for qid in answers:
                student_ans, correct_ans, marks = answers[qid]

                if str(student_ans).lower().strip() == str(correct_ans).lower().strip():
                    score += marks

            st.success(f"🎉 Score: {score}")

            c.execute(
                "INSERT INTO results VALUES (?,?,?,?)", (sid, name, lesson, score)
            )
            conn.commit()

            if phone:
                try:
                    message = client.messages.create(
                        body=f"🎓 Student {name} scored {score} in {lesson}",
                        from_="whatsapp:+14155238886",
                        to=f"whatsapp:{phone}",
                    )
                    st.success("📲 WhatsApp sent!")
                    st.write("Message SID:", message.sid)

                except Exception as e:
                    st.error(f"WhatsApp Error: {e}")
