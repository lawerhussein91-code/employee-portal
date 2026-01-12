from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# مسار نسبي (مهم للنشر)
EXCEL_FILE = "master_employees.xlsx"

# 🔐 الباسورد الموحد الجديد
MASTER_PASSWORD = "1234"

AUTH_FILE = "auth.json"


# ================= قراءة البيانات =================
def load_data():
    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        print("❌ فشل قراءة ملف الاكسل:", e)
        return None

    df.columns = df.columns.str.strip()

    # حذف الصفوف الفارغة
    df = df[df["الرقم الوظيفي"].notna()]

    # تحويل الرقم الوظيفي لنص بدون .0
    df["الرقم الوظيفي"] = (
        df["الرقم الوظيفي"]
        .astype(float)
        .astype(int)
        .astype(str)
    )

    return df


# ================= كلمات المرور =================
def load_auth():
    if not os.path.exists(AUTH_FILE):
        return {}

    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_auth(data):
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================= تسجيل الدخول =================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        emp_id = request.form["emp_id"].strip()
        password = request.form["password"]

        df = load_data()
        if df is None:
            return "❌ فشل قراءة قاعدة البيانات"

        auth = load_auth()

        if emp_id not in df["الرقم الوظيفي"].values:
            return render_template("login.html",
                                   error="الرقم الوظيفي غير موجود")

        # إنشاء باسورد لأول مرة
        if emp_id not in auth:
            auth[emp_id] = {
                "password_hash": generate_password_hash(
                    MASTER_PASSWORD,
                    method="pbkdf2:sha256"
                ),
                "first_login": 1
            }
            save_auth(auth)

        user = auth[emp_id]

        if not check_password_hash(user["password_hash"], password):
            return render_template("login.html",
                                   error="كلمة المرور خاطئة")

        session["emp_id"] = emp_id

        if user["first_login"] == 1:
            return redirect(url_for("change_password"))

        return redirect(url_for("profile"))

    return render_template("login.html")


# ================= تغيير كلمة المرور =================
@app.route("/change_password", methods=["GET", "POST"])
def change_password():

    if "emp_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        new = request.form["new"]
        confirm = request.form["confirm"]

        if new != confirm:
            return render_template("change_password.html",
                                   error=True,
                                   error_msg="كلمتا المرور غير متطابقتين")

        if len(new) < 8:
            return render_template("change_password.html",
                                   error=True,
                                   error_msg="كلمة المرور ضعيفة (اقل من 8 احرف)")

        auth = load_auth()
        emp_id = session["emp_id"]

        auth[emp_id]["password_hash"] = generate_password_hash(
            new,
            method="pbkdf2:sha256"
        )
        auth[emp_id]["first_login"] = 0
        save_auth(auth)

        return redirect(url_for("profile"))

    return render_template("change_password.html")


# ================= الملف الشخصي =================
@app.route("/profile")
def profile():

    if "emp_id" not in session:
        return redirect(url_for("login"))

    df = load_data()
    if df is None:
        return "❌ فشل قراءة البيانات"

    user = df[df["الرقم الوظيفي"] == session["emp_id"]].iloc[0]

    # تنسيق تاريخ الاستحقاق
    date_val = user["تاريخ الاستحقاق"]

    if pd.notna(date_val):
        try:
            formatted_date = date_val.strftime("%Y-%m-%d")
        except:
            formatted_date = str(date_val)
    else:
        formatted_date = "غير محدد"

    last_update = datetime.now().strftime("%d/%m/%Y - %H:%M")

    return render_template(
        "profile.html",
        emp_id=session["emp_id"],
        data=user,
        formatted_date=formatted_date,
        last_update=last_update
    )


# ================= تسجيل خروج =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= تشغيل =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)