from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_ME_SECRET_KEY")

EXCEL_PATH = os.environ.get("EXCEL_PATH", "employees.xlsx")
SHEET_NAME = os.environ.get("SHEET_NAME", "Sheet1")

REQUIRED_COLUMNS = [
    "الرقم الوظيفي",
    "الاسم الكامل",
    "العنوان الوظيفي",
    "الدرجة",
    "المرحلة",
    "تاريخ الاستحقاق",
    "عدد كتب الشكر",
    "الملاحظات",
]

PASSWORD_COL = "password_hash"
MUST_CHANGE_COL = "must_change_password"

DEFAULT_PASSWORD = os.environ.get("DEFAULT_PASSWORD", "1234")  # الباسوورد الابتدائي


def load_df():
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"ملف الإكسل غير موجود: {EXCEL_PATH}")

    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)
    # تنظيف
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # تحقق أعمدة أساسية
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"الأعمدة ناقصة بالإكسل: {missing}")

    # إنشاء أعمدة الباسوورد إذا مو موجودة
    changed = False
    if PASSWORD_COL not in df.columns:
        df[PASSWORD_COL] = ""
        changed = True
    if MUST_CHANGE_COL not in df.columns:
        df[MUST_CHANGE_COL] = "1"
        changed = True

    # تعبئة password_hash للموظفين اللي ما عندهم
    for i in range(len(df)):
        if not df.at[i, PASSWORD_COL] or df.at[i, PASSWORD_COL] == "nan":
            df.at[i, PASSWORD_COL] = generate_password_hash(DEFAULT_PASSWORD)
            df.at[i, MUST_CHANGE_COL] = "1"
            changed = True

    if changed:
        save_df(df)

    return df


def save_df(df: pd.DataFrame):
    # نخليها ترجع نفس ترتيب الأعمدة مع إضافة أعمدة النظام بالنهاية
    cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    for extra in [PASSWORD_COL, MUST_CHANGE_COL]:
        if extra in df.columns:
            cols.append(extra)

    df_out = df[cols].copy()
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="w") as writer:
        df_out.to_excel(writer, index=False, sheet_name=SHEET_NAME)


def find_employee(df, emp_id: str):
    emp_id = str(emp_id).strip()
    match = df[df["الرقم الوظيفي"].astype(str).str.strip() == emp_id]
    if match.empty:
        return None, None
    idx = match.index[0]
    return idx, match.loc[idx]


@app.route("/", methods=["GET"])
def home():
    if session.get("emp_id"):
        return redirect(url_for("profile"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        emp_id = (request.form.get("emp_id") or "").strip()
        password = request.form.get("password") or ""

        try:
            df = load_df()
            idx, row = find_employee(df, emp_id)
        except Exception as e:
            return render_template("login.html", error=str(e))

        if row is None:
            return render_template("login.html", error="الرقم الوظيفي غير موجود")

        if not check_password_hash(str(row[PASSWORD_COL]), password):
            return render_template("login.html", error="الباسوورد خطأ")

        session["emp_id"] = emp_id
        # إذا لازم يغير باسوورد
        must_change = str(row.get(MUST_CHANGE_COL, "0")).strip()
        if must_change == "1":
            return redirect(url_for("change_password"))

        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/profile", methods=["GET"])
def profile():
    emp_id = session.get("emp_id")
    if not emp_id:
        return redirect(url_for("login"))

    df = load_df()
    idx, row = find_employee(df, emp_id)
    if row is None:
        session.clear()
        return redirect(url_for("login"))

    data = {col: ("" if str(row.get(col, "")).lower() == "nan" else str(row.get(col, ""))) for col in REQUIRED_COLUMNS}

    return render_template("profile.html", emp_id=emp_id, data=data)


@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    emp_id = session.get("emp_id")
    if not emp_id:
        return redirect(url_for("login"))

    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new1 = request.form.get("new_password") or ""
        new2 = request.form.get("confirm_password") or ""

        if new1 != new2:
            return render_template("change_password.html", error="الباسوورد الجديد غير متطابق")

        if len(new1) < 6:
            return render_template("change_password.html", error="الباسوورد لازم 6 أحرف/أرقام على الأقل")

        df = load_df()
        idx, row = find_employee(df, emp_id)
        if row is None:
            session.clear()
            return redirect(url_for("login"))

        if not check_password_hash(str(row[PASSWORD_COL]), current):
            return render_template("change_password.html", error="الباسوورد الحالي خطأ")

        df.at[idx, PASSWORD_COL] = generate_password_hash(new1)
        df.at[idx, MUST_CHANGE_COL] = "0"
        save_df(df)

        flash("تم تغيير الباسوورد بنجاح")
        return redirect(url_for("profile"))

    return render_template("change_password.html")


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)