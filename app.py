from flask import Flask, render_template, redirect, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secretKey"   ## ENTER SECRET KEY HERE

# subroutine to get database connection and format
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn 

# LOGIN AND SIGNUP

# handle attempted log in
@app.route("/loginSubmit", methods=["POST"])
def inputSubmitted():
    username = request.form["username"]
    attemptedPassword = request.form["password"]
    conn = get_db_connection()
    found = conn.execute("SELECT password FROM logins WHERE username = ?", (username,)).fetchone()
    conn.close()
    if found:
        if check_password_hash(found[0], attemptedPassword):
            session["loggedIn"] = True
            return redirect("/index")
        else:
            flash("wrong password")
    else:
        flash("no accounts with this username")
    return redirect("/loginPage")

# send user to sign up page
@app.route("/goToSignUp", methods=["GET"])
def goToSignUp():
    return render_template("signUpPage.html")

# handle attempted sign up
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
    
# send user to log in page
@app.route("/loginPage", methods=["GET"])
def loginPage():
    return render_template("loginPage.html")

# STANDINGS

def getStandings():
    conn = get_db_connection()
    teams = conn.execute("SELECT * FROM teams ORDER BY place ASC").fetchall()
    conn.close()
    return teams

# GAMES

def getUpcomingGames():
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    games = conn.execute("SELECT * FROM games WHERE datetime > ?", (now_str,)).fetchall()
    conn.close()
    return games





# TEAM

@app.route("/team")
def team():
    return render_template("team.html")  

# ADMIN

@app.route("/admin")
def admin():
    return render_template("admin.html")  

# INDEX

@app.route("/index")
def index():
    teams = getStandings()
    games = getUpcomingGames()
    return render_template("index.html", teams=teams, games=games)


# MAIN

@app.route("/")
def root():
    
    # SESSION VARIABLES

    session["captain"] = True
    session["loggedIn"] = False
    session["adminperms"] = True

    # LOAD HOME SCREEN

    return index()

if __name__ == "__main__":
    app.run(debug=True)
