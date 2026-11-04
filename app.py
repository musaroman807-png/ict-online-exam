import os
import sqlite3
import hmac
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-this-password")
DB = "exam.db"


def database():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with database() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            started TEXT NOT NULL,
            submitted TEXT,
            score INTEGER,
            latitude REAL,
            longitude REAL,
            consent INTEGER DEFAULT 0
        )
        """)


init_db()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/begin", methods=["POST"])
def begin():
    name = request.form.get("name", "").strip()
    consent = request.form.get("location_consent")

    if not name:
        return "নাম লিখতে হবে।", 400

    if consent != "yes":
        return "Location সংগ্রহের সম্মতি প্রয়োজন।", 400

    session.clear()
    session["pending_name"] = name
    session["location_consent"] = True

    return redirect(url_for("location_page"))


@app.route("/location")
def location_page():
    if not session.get("pending_name") or not session.get("location_consent"):
        return redirect(url_for("home"))

    return render_template("location.html")


@app.route("/save-location", methods=["POST"])
def save_location():
    if not session.get("pending_name") or not session.get("location_consent"):
        return jsonify(error="অনুমতি পাওয়া যায়নি।"), 403

    data = request.get_json(silent=True) or {}

    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError()

    except (KeyError, TypeError, ValueError):
        return jsonify(error="সঠিক Location পাওয়া যায়নি।"), 400

    name = session.pop("pending_name")
    session.pop("location_consent", None)
    started = datetime.now(timezone.utc).isoformat()

    with database() as con:
        cur = con.execute("""
        INSERT INTO students
        (name, started, latitude, longitude, consent)
        VALUES (?, ?, ?, ?, 1)
        """, (name, started, lat, lon))

        session["student_id"] = cur.lastrowid

    return jsonify(ok=True, redirect=url_for("exam"))

QUESTIONS = [
    {"question": "দশমিক ১৫-এর বাইনারি মান কত?", "options": ["১০১০", "১১১০", "১১১১", "১০০১"], "answer": 2},
    {"question": "(0.625)₁₀ এর বাইনারি মান কত?", "options": ["0.011", "0.101", "0.110", "0.111"], "answer": 1},
    {"question": "দূর থেকে চিকিৎসা সেবা দেওয়ার পদ্ধতিকে কী বলে?", "options": ["ই-কমার্স", "টেলিমেডিসিন", "ই-গভর্ন্যান্স", "বায়োমেট্রিক্স"], "answer": 1},
    {"question": "যে যোগাযোগ ব্যবস্থায় তথ্য একদিকে যায় তাকে কী বলে?", "options": ["Half Duplex", "Full Duplex", "Simplex", "Multiplex"], "answer": 2},
    {"question": "হেক্সাডেসিমেল 3A7-এর বাইনারি মান কোনটি?", "options": ["0011 1010 0111", "0011 0110 0111", "1010 0011 0111", "0011 1011 0111"], "answer": 0},
    {"question": "জীবের জিন পরিবর্তন সংক্রান্ত প্রযুক্তি কোনটি?", "options": ["ন্যানোটেকনোলজি", "জেনেটিক ইঞ্জিনিয়ারিং", "রোবোটিক্স", "বায়োমেট্রিক্স"], "answer": 1},
    {"question": "ভিন্ন ধরনের নেটওয়ার্ক সংযুক্ত করে কোন ডিভাইস?", "options": ["Gateway", "Repeater", "Hub", "Switch"], "answer": 0},
    {"question": "বাইনারি ১০১০-এর দশমিক মান কত?", "options": ["৮", "৯", "১০", "১১"], "answer": 2},
    {"question": "সরকার থেকে নাগরিকের সেবা প্রদানকে কী বলে?", "options": ["B2B", "G2C", "C2C", "G2G"], "answer": 1},
    {"question": "খ্রিষ্টাব্দ বোঝাতে কোন সংক্ষিপ্ত রূপ ব্যবহৃত হয়?", "options": ["BC", "AD", "BCE", "CE"], "answer": 1},
    {"question": "কৃত্রিম বুদ্ধিমত্তা ও রোবোটিক্স কোন ক্ষেত্রের অন্তর্ভুক্ত?", "options": ["AI & Robotics", "Networking", "Database", "Graphics"], "answer": 0},
    {"question": "IPv4-এর লুপব্যাক ঠিকানা 127.0.0.1-এ প্রথম অংশ কত?", "options": ["১২৬", "১২৭", "১২৮", "১৯২"], "answer": 1},
    {"question": "একসঙ্গে এক বিট করে ডেটা পাঠানোর পদ্ধতি কোনটি?", "options": ["Parallel", "Serial", "Broadcast", "Multicast"], "answer": 1},
    {"question": "দশমিক 53.625-এর মান কত?", "options": ["53.525", "53.625", "53.725", "53.825"], "answer": 2},
    {"question": "আঙুলের ছাপ দিয়ে পরিচয় শনাক্ত করার পদ্ধতি কী?", "options": ["ফায়ারওয়াল", "বায়োমেট্রিক্স", "এনক্রিপশন", "ডেটাবেজ"], "answer": 1},
    {"question": "১০ Mbps বলতে কী বোঝায়?", "options": ["১০ megabytes/sec", "১০ megabits/sec", "১০ kilobits/sec", "১০ bytes/sec"], "answer": 1},
    {"question": "অক্টাল 735-এর বাইনারি মান কোনটি?", "options": ["111011101", "111101101", "101111101", "111011011"], "answer": 0},
    {"question": "একটি নেটওয়ার্কের কেন্দ্রীয় ডিভাইস নষ্ট হলে কী হতে পারে?", "options": ["গতি বাড়বে", "পুরো নেটওয়ার্ক বন্ধ হতে পারে", "শুধু রং বদলাবে", "কিছুই হবে না"], "answer": 1},
    {"question": "অক্টাল 253-এর দশমিক মান কত?", "options": ["১৭১", "১৭২", "১৭৩", "১৭৪"], "answer": 2},
    {"question": "ভুয়া ওয়েবসাইট বা বার্তার মাধ্যমে তথ্য চুরির কৌশল কী?", "options": ["Phishing", "Formatting", "Browsing", "Streaming"], "answer": 0},
    {"question": "Asynchronous serial communication-এ কী ব্যবহৃত হয়?", "options": ["Start & Stop bits", "শুধু parity bit", "শুধু clock", "শুধু data bit"], "answer": 0},
    {"question": "৮-বিটে -37-এর 2's complement কোনটি?", "options": ["11011010", "11011011", "10110101", "00100101"], "answer": 1},
    {"question": "Global Village ধারণার প্রবক্তা কে?", "options": ["Bill Gates", "Marshall McLuhan", "Charles Babbage", "Tim Berners-Lee"], "answer": 1},
    {"question": "অক্টাল 345-এর দশমিক মান কত?", "options": ["২২৭", "২২৮", "২২৯", "২৩0"], "answer": 2},
    {"question": "দ্রুতগতির ডেটা পরিবহনে কোন মাধ্যমটি বেশি কার্যকর?", "options": ["Twisted Pair", "Coaxial Cable", "Optical Fiber", "Telephone Line"], "answer": 2},
    {"question": "বাইনারি 101101 থেকে 1101 বিয়োগ করলে ফল কত?", "options": ["100000", "101000", "100000", "110000"], "answer": 2},
    {"question": "অতি ক্ষুদ্র প্রযুক্তি নিয়ে কাজ করার ক্ষেত্র কোনটি?", "options": ["Biotechnology", "Robotics", "Nanotechnology", "Telemedicine"], "answer": 2},
    {"question": "এক নেটওয়ার্ক থেকে অন্য নেটওয়ার্কে ডেটা পাঠায় কোন ডিভাইস?", "options": ["Mouse", "Keyboard", "Router", "Monitor"], "answer": 2},
    {"question": "হেক্সাডেসিমেল A9 + 37 = কত?", "options": ["D0", "DF", "E0", "F0"], "answer": 2},
    {"question": "কম্পিউটার-নির্মিত কৃত্রিম পরিবেশকে কী বলে?", "options": ["AI", "AR", "VR", "ICT"], "answer": 2},
    {"question": "1's complement পেতে কী করতে হয়?", "options": ["প্রতিটি বিট উল্টাতে হয়", "১ যোগ করতে হয়", "২ বিয়োগ করতে হয়", "বিট সরাতে হয়"], "answer": 0},
    {"question": "হেক্সাডেসিমেল 2D.4-এর মান কোনটি?", "options": ["2C.4", "2D.2", "2D.4", "2E.4"], "answer": 2},
    {"question": "নেটওয়ার্কে দুর্বল সিগন্যালকে পুনরায় শক্তিশালী করে কোন ডিভাইস?", "options": ["Router", "Repeater", "Gateway", "Modem"], "answer": 1},
    {"question": "একই সময়ে উভয় দিকে ডেটা আদান-প্রদানের পদ্ধতি কী?", "options": ["Simplex", "Half Duplex", "Full Duplex", "Serial"], "answer": 2},
    {"question": "হেক্সাডেসিমেল 59-এর বাইনারি মান কোনটি?", "options": ["0101 1001", "0101 1010", "0110 1001", "0100 1001"], "answer": 0},
    {"question": "Gray code 1011-এর বাইনারি মান কোনটি?", "options": ["1101", "1110", "1010", "1001"], "answer": 1},
    {"question": "ইন্টারনেটের মাধ্যমে বিদেশি প্রতিষ্ঠানের কাজ করে আয় করাকে কী বলে?", "options": ["E-commerce", "Outsourcing", "Browsing", "Networking"], "answer": 1},
    {"question": "৮-বিটে -18-এর 1's complement কোনটি?", "options": ["11101101", "11101110", "11101100", "10010010"], "answer": 0},
    {"question": "বাইনারি 10000-এর দশমিক মান কত?", "options": ["৮", "১৬", "৩২", "৬৪"], "answer": 1},
    {"question": "তথ্য ও যোগাযোগ প্রযুক্তি ব্যবহারের সুযোগের বৈষম্যকে কী বলে?", "options": ["Cyber Crime", "Digital Divide", "Data Mining", "E-commerce"], "answer": 1}
]


@app.route("/exam")
def exam():
    if not session.get("student_id"):
        return redirect(url_for("home"))

    safe_questions = [
        {"question": q["question"], "options": q["options"]}
        for q in QUESTIONS
    ]
    return render_template("exam.html", questions=safe_questions)


@app.route("/submit", methods=["POST"])
def submit():
    student_id = session.get("student_id")

    if not student_id:
        return jsonify(error="পরীক্ষার সেশন পাওয়া যায়নি।"), 401

    data = request.get_json(silent=True) or {}
    answers = data.get("answers", {})
    score = 0

    for index, question in enumerate(QUESTIONS):
        if answers.get(str(index)) == question["answer"]:
            score += 1

    submitted = datetime.now(timezone.utc).isoformat()

    with database() as con:
        con.execute("""
        UPDATE students
        SET score=?, submitted=?
        WHERE id=?
        """, (score, submitted, student_id))

    session.pop("student_id", None)

    return jsonify(score=score, total=len(QUESTIONS))


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)
    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")

        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("admin"))

        return "ভুল পাসওয়ার্ড।"

    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin():
    with database() as con:
        students = con.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()

    return render_template("admin.html", students=students)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
