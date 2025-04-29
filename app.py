from flask import Flask, render_template, redirect, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "bum"   ## ENTER SECRET KEY HERE

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# GLOBALS

captain = True
loggedIn = False
adminperms = True





# LOGIN AND SIGNUP

@app.route("/loginSubmit", methods=["POST"])
def inputSubmitted():
    username = request.form["username"]
    attemptedPassword = request.form["password"]
    conn = get_db_connection()
    found = conn.execute("SELECT password FROM logins WHERE username = ?", (username,)).fetchone()
    conn.close()
    if found:
        if check_password_hash(found[0], attemptedPassword):
            loggedIn = True
            return redirect("/")
        else:
            flash("wrong password")
    else:
        flash("no accounts with this username")
    return redirect("/")

@app.route("/goToSignUp", methods=["GET"])
def goToSignUp():
    return render_template("signUpPage.html")

@app.route("/signUpSubmit", methods=["POST"])
def signUp():
    username = request.form["username"]
    hashedPassword = generate_password_hash(request.form["password"])
    conn = get_db_connection()
    found = conn.execute("SELECT password FROM logins WHERE username = ?", (username,)).fetchone()
    if found:
       conn.close()
       flash("Username already taken")
       return render_template("/signUpPage.html")
    else:
        conn.execute("INSERT INTO logins (username, password) VALUES (?, ?)", (username, hashedPassword))
        conn.commit()
        conn.close()
        return redirect("/loginPage")
    
@app.route("/loginPage", methods=["GET"])
def loginPage():
    return render_template("loginPage.html")

# STANDINGS

@app.route("/standings")
def standings():
    return render_template("standings.html")

# GAMES

@app.route("/games")
def games():
    return render_template("games.html")

# INFO

@app.route("/info")
def info():
    return render_template("info.html")

# TEAM

@app.route("/team")
def team():
    return render_template("team.html")  

# ADMIN

@app.route("/admin")
def admin():
    return render_template("admin.html")  





@app.route("/")
def index():
    return render_template("index.html", loggedIn = loggedIn, captain = captain, adminperms = adminperms)

if __name__ == "__main__":
    app.run(debug=True)