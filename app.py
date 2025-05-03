from flask import Flask, render_template, redirect, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import pytz

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
            session["username"] = username
            (captain, admin) = checkPerms(username)
            print(captain + admin)
            session["captain"] = captain
            session["admin"] = admin
            return redirect("/index")
        else:
            flash("wrong password")
    else:
        flash("no accounts with this username")
    return redirect("/loginPage")

# check account perms
def checkPerms(username):
    conn = get_db_connection()
    (captain, admin) = conn.execute("SELECT captain, admin FROM logins WHERE username = ?", (username,)).fetchone()
    if captain == 1:
        isCaptain = True
    else:
        isCaptain = False
    if admin == 1:
        isAdmin = True
    else:
        isAdmin = False
    conn.close()
    return isCaptain, isAdmin


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

def getUpcomingGames(team):
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    if len(team) > 0:
        games = conn.execute("SELECT * FROM games WHERE datetime > ? AND (home = ? OR away = ?)", (now_str, team, team)).fetchall()
    else:
        games = conn.execute("SELECT * FROM games WHERE datetime > ?", (now_str,)).fetchall()
    conn.close()
    return games

def utc_to_local(utc_dt, timezone_str):
    local_tz = pytz.timezone(timezone_str)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_dt

def getTimezonedGames(team):
    games_data = getUpcomingGames(team)
    user_timezone_str = session.get('timezone') 

    updated_games = []

    for game in games_data:
        game_dict = dict(game) 
        utc_dt = datetime.strptime(game_dict['datetime'], '%Y-%m-%d %H:%M:%S')

        if user_timezone_str:
            game_dict['local_datetime'] = utc_to_local(utc_dt, user_timezone_str).strftime('%Y-%m-%d %H:%M:%S')
            session["abbreviatedTimezone"] = utc_dt.astimezone(pytz.timezone(user_timezone_str)).tzname()

        else:
            game_dict['local_datetime'] = game_dict['datetime']
            session["abbreviatedTimezone"] = "UTC"

        updated_games.append(game_dict)

    return updated_games


# TEAM

@app.route("/showTeam/<string:teamName>")
def team(teamName):
    conn = get_db_connection()
    stats = conn.execute("SELECT * FROM teams WHERE name = ?", (teamName,)).fetchone()
    conn.close()
    games = getTimezonedGames(teamName)
    if session.get("loggedIn") and stats["captain"] == session["username"]:
        return render_template("team.html", stats=stats, games=games, captain=True)
    else:
        return render_template("team.html", stats=stats, games=games, captain=False)

# MANAGE TEAM

@app.route("/manageTeam")
def manageTeam():
    conn = get_db_connection()
    stats = conn.execute("SELECT * FROM teams WHERE captain = ?", (session["username"], )).fetchone()
    conn.close()
    games = getUpcomingGames(stats["name"])
    return render_template("team.html", stats=stats, games=games, captain=True)


# ADMIN

@app.route("/admin")
def admin():
    return render_template("admin.html")  

# INDEX

@app.route("/index")
def index():
    teams = getStandings()
    games = getTimezonedGames("")
    return render_template("index.html", teams=teams, games=games)

# LOADED

@app.route("/loaded")
def loaded():
    # SET TIMEZONE
    timezone = request.args.get("timezone")
    if timezone:
        session["timezone"] = timezone
    #load index
    return index()

# MAIN

@app.route("/")
def root():
    
    # SESSION VARIABLES

    if "loggedIn" not in session:
        session["loggedIn"] = False
    if "username" not in session:
        session["username"] = ""
    if "captain" not in session:
        session["captain"] = False
    if "adminperms" not in session:
        session["adminperms"] = False

    # LOAD

    return render_template("load.html")


if __name__ == "__main__":
    app.run(debug=True)





# 