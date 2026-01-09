from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "secret_key_123"

EXCEL_FILE = "employees.xlsx"
MASTER_PASSWORD = "123456"

def load_data():
    return pd.read_excel(EXCEL_FILE)

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

def init_excel():
    df = load_data()

    if "password_hash" not in df.columns:
        df["password_hash"] = generate_password_hash(MASTER_PASSWORD)

    if "first_login" not in df.columns:
        df["first_login"] = 1

    save_data(df)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        emp_id = request.form["emp_id"]
        password = request.form["password"]

        df = load_data()
        user = df[df["الرقم الوظيفي"].astype(str)==emp_id]

        if user.empty:
            return "الرقم الوظيفي غير موجود"

        row = user.iloc[0]

        if not check_password_hash(row["password_hash"], password):
            return "كلمة المرور خاطئة"

        session["emp_id"] = emp_id

        if row["first_login"] == 1:
            return redirect(url_for("change_password"))

        return redirect(url_for("profile"))

    return render_template("login.html")

@app.route("/change_password", methods=["GET","POST"])
def change_password():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    if request.method=="POST":
        new = request.form["new"]

        df = load_data()
        i = df[df["الرقم الوظيفي"].astype(str)==session["emp_id"]].index[0]

        df.loc[i,"password_hash"] = generate_password_hash(new)
        df.loc[i,"first_login"] = 0

        save_data(df)
        return redirect(url_for("profile"))

    return render_template("change_password.html")

@app.route("/profile")
def profile():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    df = load_data()
    user = df[df["الرقم الوظيفي"].astype(str)==session["emp_id"]].iloc[0]

    return render_template("profile.html",
                           emp_id=session["emp_id"],
                           data=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__=="__main__":
    init_excel()
    app.run(debug=True)