from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_123"

# ملف الاكسل
EXCEL_FILE = "برنامج الترقيات  اضافة ارقام وظيفة.xlsx"

MASTER_PASSWORD = "123456"

# =================================
# تنظيف الرقم الوظيفي
# =================================
def normalize_emp_id(x):
    if pd.isna(x):
        return ""
    s = str(x).strip().replace(",", "").replace(" ", "")
    if s.endswith(".0"):
        s = s[:-2]
    try:
        return str(int(float(s)))
    except:
        return s

# =================================
# تحميل البيانات
# =================================
def load_data():
    df = pd.read_excel(EXCEL_FILE, dtype=str)

    # حذف الأعمدة المكررة
    df = df.loc[:,~df.columns.duplicated()]

    df.columns = df.columns.astype(str).str.strip()

    col = detect_emp_column(df)

    df.rename(columns={col: "الرقم الوظيفي"}, inplace=True)
    df["الرقم الوظيفي"] = df["الرقم الوظيفي"].apply(normalize_emp_id)

    return df

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

# =================================
# دالة ذكية لاكتشاف العمود
# =================================
def detect_emp_column(df):

    blocked = [
        "password","hash","login","first",
        "must","change","pass"
    ]

    best_col = None
    best_score = -1

    for col in df.columns:

        col_low = col.lower()

        # تجاهل أعمدة النظام
        if any(b in col_low for b in blocked):
            continue

        s = df[col].astype(str).apply(normalize_emp_id)
        s = s[s != ""]

        if len(s) < 5:
            continue

        numeric_ratio = (s.str.match(r"^\d+$")).mean()
        avg_len = s.str.len().mean()
        long_ratio = (s.str.len() >= 5).mean()

        score = numeric_ratio*0.6 + long_ratio*0.4 + (avg_len/20)

        if score > best_score:
            best_score = score
            best_col = col

    if best_col is None:
        print("\n📌 الأعمدة الموجودة:")
        for c in df.columns:
            print("➡", c)
        raise Exception("❌ لم يتم العثور على عمود الرقم الوظيفي")

    print("✅ تم اختيار عمود الرقم الوظيفي:", best_col)
    return best_col

# =================================
# تهيئة الملف
# =================================
def init_excel():
    df = load_data()

    if "password_hash" not in df.columns:
        df["password_hash"] = ""

    if "first_login" not in df.columns:
        df["first_login"] = 1

    save_data(df)

# =================================
# تسجيل الدخول
# =================================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":

        emp_id = normalize_emp_id(request.form["emp_id"])
        password = request.form["password"]

        df = load_data()

        user = df[df["الرقم الوظيفي"] == emp_id]

        if user.empty:
            return render_template(
                "login.html",
                error="⚠ الرقم الوظيفي غير موجود"
            )

        row = user.iloc[0]
        pwd_hash = row["password_hash"]

        # أول دخول
        if pd.isna(pwd_hash) or pwd_hash == "":
            idx = user.index[0]
            new_hash = generate_password_hash(MASTER_PASSWORD)
            df.loc[idx,"password_hash"] = new_hash
            df.loc[idx,"first_login"] = 1
            save_data(df)
            pwd_hash = new_hash

        if not check_password_hash(str(pwd_hash), password):
            return render_template(
                "login.html",
                error="كلمة المرور خاطئة"
            )

        session["emp_id"] = emp_id

        if int(row["first_login"]) == 1:
            return redirect(url_for("change_password"))

        return redirect(url_for("profile"))

    return render_template("login.html")

# =================================
# تغيير كلمة المرور
# =================================
@app.route("/change_password", methods=["GET","POST"])
def change_password():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        new_pass = request.form["new"]

        if len(new_pass) < 8:
            return render_template(
                "change_password.html",
                error=True,
                error_msg="كلمة المرور ضعيفة (اقل من 8 احرف)"
            )

        df = load_data()
        idx = df[
            df["الرقم الوظيفي"]==session["emp_id"]
        ].index[0]

        df.loc[idx,"password_hash"] = generate_password_hash(new_pass)
        df.loc[idx,"first_login"] = 0

        save_data(df)

        return redirect(url_for("profile"))

    return render_template("change_password.html")

# =================================
# الملف الشخصي
# =================================
@app.route("/profile")
def profile():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    df = load_data()
    user = df[
        df["الرقم الوظيفي"]==session["emp_id"]
    ].iloc[0]

    timestamp = os.path.getmtime(EXCEL_FILE)
    last_update = datetime.fromtimestamp(timestamp)\
                    .strftime("%d/%m/%Y - %H:%M")

    return render_template(
        "profile.html",
        emp_id=session["emp_id"],
        data=user,
        last_update=last_update
    )

# =================================
# تسجيل خروج
# =================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =================================
# تشغيل
# =================================
if __name__ == "__main__":
    init_excel()
    app.run(debug=True)