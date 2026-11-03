import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

# ==================================================
#  ตั้งค่า
# ==================================================

app = Flask(__name__)
app.secret_key = "goyolo-trip-local-dev-key-change-this"

BASE_DIR = Path(app.root_path)

DATABASE = BASE_DIR / "users.db"

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# ==================================================
#  ฐานข้อมูลสมาชิก
# ==================================================

def init_user_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def init_user_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # สิทธิ์แอดมิน
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "is_admin" not in columns:
            conn.execute("""
                ALTER TABLE users
                ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0
            """)

        # สร้างบัญชีแอดมิน
        conn.execute("""
            INSERT INTO users (
                username, email, password_hash,
                full_name, phone, is_admin
            )
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(username) DO NOTHING
        """, (
            "Goyolo admin",
            "admin@goyolotrip.local",
            generate_password_hash("Goyolo1234"),
            "GoYolo Administrator",
            "0000000000"
        ))

        # กำหนดมีสิทธิ์แอดมิน
        conn.execute("""
            UPDATE users
            SET is_admin = 1
            WHERE username = ? COLLATE NOCASE
        """, ("Goyolo admin",))


init_user_db()

# ==================================================
# เก็บข้อมูลการจองทริป
# ==================================================

def init_booking_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                province TEXT NOT NULL,
                tour_name TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                travelers INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                hotel_name TEXT,
                nights INTEGER DEFAULT 0,
                single_rooms INTEGER DEFAULT 0,
                double_rooms INTEGER DEFAULT 0,
                trip_total REAL NOT NULL,
                hotel_total REAL NOT NULL,
                total REAL NOT NULL,
                slip_filename TEXT,
                status TEXT NOT NULL DEFAULT 'รอตรวจสอบการชำระเงิน',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

init_booking_db()

# ==================================================
# หน้าแรก
# ==================================================

@app.route("/")
def home():
    images = sorted(
        file.name
        for file in UPLOAD_FOLDER.iterdir()
        if file.is_file()
        and file.suffix.lower() in ALLOWED_EXTENSIONS
    )

    return render_template("index.html", images=images)

# ==================================================
# Trips
# ==================================================

@app.route("/map")
def map():
    return render_template("map.html")


# ==================================================
# จังหวัดทั้ง 6
# ==================================================

@app.route("/bangkok")
def bangkok():
    return render_template("bangkok.html")


@app.route("/nonthaburi")
def nonthaburi():
    return render_template("nonthaburi.html")


@app.route("/pathum_thani")
def pathum_thani():
    return render_template("pathum_thani.html")


@app.route("/samut_prakan")
def samut_prakan():
    return render_template("samut_prakan.html")


@app.route("/samut_sakhon")
def samut_sakhon():
    return render_template("samut_sakhon.html")


@app.route("/nakhon_pathom")
def nakhon_pathom():
    return render_template("nakhon_pathom.html")


# ==================================================
# อัปโหลดรูปภาพ
# ==================================================

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("images")

    for file in files:
        if not file or not file.filename:
            continue

        filename = secure_filename(file.filename)
        suffix = Path(filename).suffix.lower()

        if not filename or suffix not in ALLOWED_EXTENSIONS:
            continue

        destination = UPLOAD_FOLDER / filename
        counter = 1

        while destination.exists():
            destination = UPLOAD_FOLDER / (
                f"{Path(filename).stem}_{counter}{suffix}"
            )
            counter += 1

        file.save(destination)

    return redirect(url_for("home"))

# ==================================================
#  สมัครสมาชิก
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not all([
            username,
            email,
            password,
            confirm_password,
            full_name,
            phone,
        ]):
            return render_template(
                "register.html",
                error="กรุณากรอกข้อมูลให้ครบทุกช่อง"
            )

        if not 3 <= len(username) <= 30:
            return render_template(
                "register.html",
                error="ชื่อผู้ใช้ต้องมีความยาว 3–30 ตัวอักษร"
            )

        if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
            return render_template(
                "register.html",
                error="ชื่อผู้ใช้ใช้ได้เฉพาะตัวอักษรอังกฤษ ตัวเลข _ . และ -"
            )

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return render_template(
                "register.html",
                error="รูปแบบอีเมลไม่ถูกต้อง"
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                error="รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="รหัสผ่านทั้งสองช่องไม่ตรงกัน"
            )

        if len(full_name) > 100 or len(phone) > 30:
            return render_template(
                "register.html",
                error="ชื่อหรือเบอร์โทรศัพท์ยาวเกินกำหนด"
            )

        password_hash = generate_password_hash(password)

        try:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("""
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        full_name,
                        phone
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    username,
                    email,
                    password_hash,
                    full_name,
                    phone,
                ))

        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="ชื่อผู้ใช้หรืออีเมลนี้มีผู้สมัครแล้ว"
            )

        return render_template(
            "register.html",
            success="สมัครสมาชิกสำเร็จ! บัญชีของคุณถูกบันทึกแล้ว"
        )

    return render_template("register.html")

# ==================================================
#  เข้าสู่ระบบ
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")

        if not login_id or not password:
            return render_template(
                "login.html",
                error="กรุณากรอกชื่อผู้ใช้หรืออีเมล และรหัสผ่าน"
            )

        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row

            user = conn.execute("""
                SELECT id, username, password_hash, is_admin
                FROM users
                WHERE username = ? COLLATE NOCASE
                   OR email = ? COLLATE NOCASE
            """, (login_id, login_id)).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return render_template(
                "login.html",
                error="ชื่อผู้ใช้ อีเมล หรือรหัสผ่านไม่ถูกต้อง"
            )

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["is_admin"] = bool(user["is_admin"])

        return redirect(url_for("home"))

    # สำคัญ: เปิดหน้า Login ด้วย GET ต้องคืนหน้าเว็บเสมอ
    return render_template("login.html")

# ==================================================
#  ออกจากระบบ
# ==================================================

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))

# ==============================
# จองทริป
# ==============================

BOOKING_TOURS = {
    # กรุงเทพมหานคร
    "BKK-01": {
        "province": "กรุงเทพมหานคร",
        "name": "เสน่ห์กรุงเก่าและวิถีริมเจ้าพระยา",
        "price": 1500,
        "days": 1,
        "hotels": []
    },
    "BKK-02": {
        "province": "กรุงเทพมหานคร",
        "name": "กรุงเทพฯ มุมใหม่ สายแลนด์มาร์ก",
        "price": 2200,
        "days": 2,
        "hotels": [
            {
                "name": "ibis Bangkok Riverside",
                "single": 1800,
                "double": 1800
            },
            {
                "name": "Holiday Inn Express Bangkok Siam",
                "single": 2000,
                "double": 2000
            }
        ]
    },

    # นนทบุรี
    "NTB-01": {
        "province": "นนทบุรี",
        "name": "ทริปนนทบุรี 1",
        "price": 1200,
        "days": 1,
        "hotels": []
    },
    "NTB-02": {
        "province": "นนทบุรี",
        "name": "ทริปนนทบุรี 2",
        "price": 1800,
        "days": 2,
        "hotels": [
            {
                "name": "Riverine Place Hotel and Residence",
                "single": 1000,
                "double": 1000
            },
            {
                "name": "ibis Bangkok IMPACT",
                "single": 1500,
                "double": 1500
            }
        ]
    },

    # ปทุมธานี
    "PTT-01": {
        "province": "ปทุมธานี",
        "name": "ทริปปทุมธานี 1",
        "price": 1300,
        "days": 1,
        "hotels": []
    },
    "PTT-02": {
        "province": "ปทุมธานี",
        "name": "ทริปปทุมธานี 2",
        "price": 2000,
        "days": 2,
        "hotels": [
            {
                "name": "Novotel Bangkok Future Park Rangsit",
                "single": 2500,
                "double": 2500
            },
            {
                "name": "Tinidee Hotel Bangkok Golf Club",
                "single": 1500,
                "double": 1500
            }
        ]
    },

    # สมุทรปราการ
    "SPK-01": {
        "province": "สมุทรปราการ",
        "name": "ทริปสมุทรปราการ 1",
        "price": 1200,
        "days": 1,
        "hotels": []
    },
    "SPK-02": {
        "province": "สมุทรปราการ",
        "name": "ทริปสมุทรปราการ 2",
        "price": 1800,
        "days": 2,
        "hotels": [
            {
                "name": "โรงแรมคูณ (Koon Hotel Sukhumvit)",
                "single": 1200,
                "double": 1200
            },
            {
                "name": "โรงแรมเบย์ (Bay Hotel Srinakarin)",
                "single": 1500,
                "double": 1500
            }
        ]
    },

    # สมุทรสาคร
    "SMK-01": {
        "province": "สมุทรสาคร",
        "name": "ทริปสมุทรสาคร 1",
        "price": 899,
        "days": 1,
        "hotels": []
    },
    "SMK-02": {
        "province": "สมุทรสาคร",
        "name": "ทริปสมุทรสาคร 2",
        "price": 1799,
        "days": 2,
        "hotels": [
            {
                "name": "Central Place Hotel",
                "single": 900,
                "double": 900
            },
            {
                "name": "Grand Inter Hotel",
                "single": 1200,
                "double": 1200
            }
        ]
    },

    # นครปฐม
    "NPT-01": {
        "province": "นครปฐม",
        "name": "ทริปนครปฐม 1",
        "price": 1200,
        "days": 1,
        "hotels": []
    },
    "NPT-02": {
        "province": "นครปฐม",
        "name": "ทริปนครปฐม 2",
        "price": 1900,
        "days": 2,
        "hotels": [
            {
                "name": "เอ็กซ์ทู นครปฐม (X2 Nakhon Pathom)",
                "single": 1500,
                "double": 1500
            },
            {
                "name": "โรงแรมไมด้า ทวารวดี แกรนด์ นครปฐม",
                "single": 1800,
                "double": 1800
            }
        ]
    }
}

@app.route("/booking", methods=["GET", "POST"])
def booking():
    if "user_id" not in session:
        return redirect(url_for("login"))
     
    code = request.values.get("tour", "").strip().upper()
    tour = BOOKING_TOURS.get(code)

    if not tour:
        return "ไม่พบข้อมูลทริปที่เลือก กรุณากลับไปเลือกทริปใหม่", 404

    hotels = tour.get("hotels") or []
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        start_date = request.form.get("start_date", "").strip()

        try:
            travelers = int(request.form.get("travelers", "1"))
        except (ValueError, TypeError):
            travelers = 0

        hotel_index = -1
        single_rooms = 0
        double_rooms = 0

        if hotels:
            try:
                hotel_index = int(request.form.get("hotel_index", "-1"))
                single_rooms = int(request.form.get("single_rooms", "0"))
                double_rooms = int(request.form.get("double_rooms", "0"))
            except (ValueError, TypeError):
                error = "กรุณาตรวจสอบข้อมูลที่พักและจำนวนห้อง"

        if not error:
            if not name:
                error = "กรุณากรอกชื่อผู้จอง"
            elif not phone.isdigit() or not 9 <= len(phone) <= 10:
                error = "กรุณากรอกเบอร์โทรศัพท์ 9–10 หลัก"
            elif not 1 <= travelers <= 5:
                error = "จำนวนผู้เดินทางต้องอยู่ระหว่าง 1–5 คน"

        end_date = ""
        nights = max(int(tour.get("days", 1)), 1) - 1

        if not error:
            try:
                parsed_start = datetime.strptime(
                    start_date, "%Y-%m-%d"
                ).date()

                if parsed_start < datetime.today().date():
                    error = "กรุณาเลือกวันที่เดินทางตั้งแต่วันนี้เป็นต้นไป"
                else:
                    end_date = (
                        parsed_start + timedelta(days=nights)
                    ).strftime("%Y-%m-%d")
            except ValueError:
                error = "กรุณาเลือกวันที่เดินทาง"

        if not error and hotels:
            if not 0 <= hotel_index < len(hotels):
                error = "กรุณาเลือกที่พัก"
            elif single_rooms < 0 or double_rooms < 0:
                error = "จำนวนห้องพักต้องไม่ติดลบ"
            elif single_rooms + double_rooms < 1:
                error = "กรุณาเลือกอย่างน้อย 1 ห้อง"

        if error:
            return render_template(
                "booking.html",
                tour=tour,
                code=code,
                error=error,
                now_date=datetime.today().strftime("%Y-%m-%d")
            )

        hotel = hotels[hotel_index] if hotels else None

        trip_total = float(tour["price"])
        hotel_total = 0

        if hotel:
            hotel_total = (
                single_rooms * float(hotel["single"])
                + double_rooms * float(hotel["double"])
            ) * nights

        total = trip_total + hotel_total

        
        session["pending_payment"] = {
            "code": code,
            "province": tour["province"],
            "tour_name": tour["name"],
            "name": name,
            "phone": phone,
            "travelers": travelers,
            "start_date": start_date,
            "end_date": end_date,
            "hotel_name": hotel["name"] if hotel else None,
            "nights": nights,
            "single_rooms": single_rooms,
            "double_rooms": double_rooms,
            "trip_total": trip_total,
            "hotel_total": hotel_total,
            "total": total
        }

        return render_template(
            "booking_summary.html",
            tour=tour,
            code=code,
            name=name,
            phone=phone,
            travelers=travelers,
            start_date=start_date,
            end_date=end_date,
            hotel=hotel,
            hotel_index=hotel_index,
            single_rooms=single_rooms,
            double_rooms=double_rooms,
            nights=nights,
            trip_total=trip_total,
            hotel_total=hotel_total,
            total=total
        )

    return render_template(
        "booking.html",
        tour=tour,
        code=code,
        error=None,
        now_date=datetime.today().strftime("%Y-%m-%d")
    )

# ==================================================
# ระบบชำระเงิน อัปโหลดสลิป
# ==================================================

SLIP_FOLDER = UPLOAD_FOLDER / "slips"
SLIP_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_SLIP_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@app.route("/payment", methods=["GET", "POST"])
def payment():
    # ต้องผ่านขั้นตอนสรุปการจองก่อน
    booking_data = session.get("pending_payment")

    if not booking_data:
        return redirect(url_for("home"))

    if request.method == "POST":
        slip = request.files.get("slip")

        if not slip or not slip.filename:
            return render_template(
                "payment.html",
                booking=booking_data,
                error="กรุณาเลือกไฟล์สลิปก่อนส่ง"
            )

        filename = secure_filename(slip.filename)
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_SLIP_EXTENSIONS:
            return render_template(
                "payment.html",
                booking=booking_data,
                error="รองรับไฟล์ JPG, JPEG, PNG และ WebP เท่านั้น"
            )

        # สร้างชื่อไฟล์ใหม่เพื่อป้องกันชื่อซ้ำ
        import uuid
        saved_name = f"{uuid.uuid4().hex}{suffix}"
        slip.save(SLIP_FOLDER / saved_name)
        
        # ต้องเข้าสู่ระบบเพื่อบันทึกทริปเข้าบัญชี
        user_id = session.get("user_id")

        if not user_id:
            return redirect(url_for("login"))

        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""
                INSERT INTO bookings (
                    user_id, code, province, tour_name,
                    name, phone, travelers,
                    start_date, end_date, hotel_name,
                    nights, single_rooms, double_rooms,
                    trip_total, hotel_total, total,
                    slip_filename, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                booking_data["code"],
                booking_data["province"],
                booking_data["tour_name"],
                booking_data["name"],
                booking_data["phone"],
                booking_data["travelers"],
                booking_data["start_date"],
                booking_data["end_date"],
                booking_data["hotel_name"],
                booking_data["nights"],
                booking_data["single_rooms"],
                booking_data["double_rooms"],
                booking_data["trip_total"],
                booking_data["hotel_total"],
                booking_data["total"],
                saved_name,
                "รอตรวจสอบการชำระเงิน"
            ))

        session["slip_submitted"] = True
        session["slip_filename"] = saved_name
        session.pop("booking_saved", None)
        session.pop("pending_payment", None)

        return redirect(url_for("my_trips"))


        return render_template(
            "payment.html",
            booking=booking_data,
            success="ได้รับหลักฐานการชำระแล้ว รอการตรวจสอบ สามารถเช็คสถานะได้ที่หน้าทริปของฉัน"
        )

    return render_template(
        "payment.html",
        booking=booking_data
    )

# ==================================================
# ทริปของฉัน
# ==================================================

@app.route("/my-trips")
def my_trips():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row

        trips = conn.execute("""
            SELECT *
            FROM bookings
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        """, (session["user_id"],)).fetchall()

    return render_template("my_trips.html", trips=trips)

# ==================================================
# ระบบแอดมิน
# ==================================================

BOOKING_STATUSES = [
    "รอตรวจสอบการชำระเงิน",
    "ชำระเงินแล้ว",
    "รอวันเดินทาง",
    "กำลังเดินทาง",
    "เสร็จสิ้น",
    "ยกเลิกการจอง",
]

def admin_required():
    return (
        "user_id" in session
        and session.get("is_admin") is True
    )

@app.route("/admin")
def admin():
    if not admin_required():
        return redirect(url_for("login"))

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row

        users = conn.execute("""
            SELECT id, username, email, full_name, phone, created_at
            FROM users
            WHERE is_admin = 0
            ORDER BY id DESC
        """).fetchall()

        bookings = conn.execute("""
            SELECT
                b.*,
                u.username AS account_username,
                u.email AS account_email
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            ORDER BY b.created_at DESC, b.id DESC
        """).fetchall()

    return render_template(
        "admin.html",
        users=users,
        bookings=bookings,
        statuses=BOOKING_STATUSES
    )

@app.route("/admin/booking/<int:booking_id>/status",
           methods=["POST"])
def admin_update_status(booking_id):
    if not admin_required():
        return redirect(url_for("login"))

    new_status = request.form.get("status", "")

    if new_status not in BOOKING_STATUSES:
        return "สถานะไม่ถูกต้อง", 400

    with sqlite3.connect(DATABASE) as conn:
        result = conn.execute("""
            UPDATE bookings
            SET status = ?
            WHERE id = ?
        """, (new_status, booking_id))

        if result.rowcount == 0:
            return "ไม่พบรายการจอง", 404

    return redirect(url_for("admin"))

@app.route("/admin/slips/<filename>")
def admin_slip(filename):
    if not admin_required():
        return redirect(url_for("login"))

    with sqlite3.connect(DATABASE) as conn:
        exists = conn.execute("""
            SELECT 1
            FROM bookings
            WHERE slip_filename = ?
        """, (filename,)).fetchone()

    if not exists:
        return "ไม่พบไฟล์สลิป", 404

    return send_from_directory(
        str(SLIP_FOLDER),
        filename,
        as_attachment=False
    )

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
