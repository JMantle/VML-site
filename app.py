from flask import Flask, render_template, redirect, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import pytz
from initdb import makeTeam, deleteTeam, makeGame, deleteGame, deleteRequest

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
            session["adminperms"] = admin
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
    games = getTimezonedGames(teamName)
    if session.get("loggedIn") and stats["captain"] == session["username"]:
        requests = conn.execute("SELECT * FROM requests WHERE teamid = ?", (stats["id"],)).fetchall()
        conn.close()
        return render_template("team.html", stats=stats, games=games, captain=True, member=True, requests=requests)
    else:
        if session["username"] + ", " in stats["members"] or bool(conn.execute("SELECT 1 FROM requests WHERE username = ? AND teamid = ?", (session["username"], stats["id"]))):
            member = True
        else:
            member = False
        conn.close()

        return render_template("team.html", stats=stats, games=games, captain=False, member=member)
    
@app.route("/requestMembership/<int:teamId>/<string:username>", methods=["POST"])
def requestMembership(teamId, username):
    message = request.form.get("message")
    conn = get_db_connection()
    conn.execute("INSERT INTO requests (teamid, username, message) VALUES (?, ?, ?)", (teamId, username, message))
    conn.commit()

    #get team to redirect to
    team = conn.execute("SELECT name FROM teams WHERE id = ?", (teamId,)).fetchone()
    conn.close()

    return redirect("/showTeam/" + team[0])

# MANAGE TEAM

@app.route("/manageTeam")
def manageTeam():
    conn = get_db_connection()
    team = conn.execute("SELECT name FROM teams WHERE captain = ?", (session["username"], )).fetchone()
    conn.close()
    return redirect("/showTeam/" + team[0])

@app.route("/removeFromTeam/<int:id>/<string:member>", methods=["POST"])
def removeFromTeam(id, member):
    #get members
    conn = get_db_connection()
    members = conn.execute("SELECT members FROM teams WHERE id = ?", (id,)).fetchone()

    #remove sepcific member
    membersString = members[0]
    members = []
    while len(membersString) > 0:
        comma = membersString.find(",")
        if comma == -1:
            members.append(membersString)
            membersString = ""
        else:
            members.append(membersString[:comma])
            membersString = membersString[comma + 2:]
    members.remove(member)
    membersString = ""

    #add all items except last with comma
    for i in range(0, len(members) - 1):
        membersString = membersString + members[i] + ", "
    
    #add last item without comma
    membersString = membersString + members[len(members) - 1]
    
    #put back into database
    conn.execute("UPDATE teams SET members = ? where id = ?", (membersString.strip(), id))
    conn.commit()
    conn.close()

    return redirect("/manageTeam")

@app.route("/addMember/<int:id>", methods=["POST"])
def addMember(id):
    name = request.form.get("name").strip()

    conn = get_db_connection()
    members = conn.execute("SELECT members FROM teams WHERE id = ?", (id,)).fetchone()[0]

    if members:
        members += ", " + name
    else:
        members = name

    conn.execute("UPDATE teams SET members = ? WHERE id = ?", (members, id))
    conn.commit()
    conn.close()
    return redirect("/manageTeam")

@app.route("/assignPlayers/<int:gameId>/<string:teamName>", methods=["POST"])
def assignPlayers(gameId, teamName):
    players = request.form.get("players").strip()
    conn = get_db_connection()

    side = conn.execute("SELECT home FROM games WHERE id = ?", (gameId,)).fetchone()
    if side[0] == teamName:
        #home team
        conn.execute("UPDATE games SET homeplayers = ? WHERE id = ?", (players, gameId))
    else:
        #away team
        conn.execute("UPDATE games SET awayplayers = ? WHERE id = ?", (players, gameId))

    conn.commit()
    conn.close()

    return redirect("/manageTeam")

@app.route("/acceptRequest/<int:id>", methods=["POST"])
def acceptRequest(id):
    conn = get_db_connection()

    #get request
    request = conn.execute("SELECT * FROM requests WHERE id = ?", (id,)).fetchone()
    #insert it into members
    members = conn.execute("SELECT members FROM teams WHERE id = ?", (id,)).fetchone()
    members = members + ", " + request["username"]
    conn.execute("UPDATE teams SET members = ? WHERE id = ?", (members, id))
    
    #delete request
    deleteRequest(id)

    return redirect("/manageTeam")

@app.route("/declineRequest/<int:id>", methods=["POST"])
def declineRequest(id):
    deleteRequest(id)
    return redirect("/manageTeam")

# ADMIN

@app.route("/admin")
def admin():
    #get data
    teams = getStandings()
    games = getTimezonedGames("")
    users = getUsers()
    #load page
    return render_template("admin.html", teams=teams, games=games, users=users) 

# users

def getUsers():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM logins").fetchall()
    conn.close()
    return users

@app.route("/updateUser/<string:id>", methods=["POST"])
def updateUser(id):
    conn = get_db_connection()

    if "makeCaptain" in request.form:
        row = conn.execute("SELECT captain FROM logins WHERE id = ?", (id,)).fetchone()
        current = row["captain"]
        conn.execute("UPDATE logins SET captain = ? WHERE id = ?", (0 if current else 1, id))

    elif "makeAdmin" in request.form:
        row = conn.execute("SELECT admin FROM logins WHERE id = ?", (id,)).fetchone()
        current = row["admin"]
        conn.execute("UPDATE logins SET admin = ? WHERE id = ?", (0 if current else 1, id))

    conn.commit()
    conn.close()
    return redirect("/admin")

# teams

@app.route("/updateTeam/<int:id>", methods=["POST"])
def updateTeam(id):
    conn = get_db_connection()

    name = request.form.get("name").strip()
    mapWins = request.form.get("mapwins").strip()
    matchWins = request.form.get("matchwins").strip()
    captain = request.form.get("captain").strip()
    members = request.form.get("members").strip()
    points = request.form.get("points").strip()
    mmr = request.form.get("mmr").strip()

    team = conn.execute("SELECT * FROM teams WHERE id = ?", (id,)).fetchone()

    updatedName = name if name else team['name']
    updatedMapWins = mapWins if mapWins else team['mapwins']
    updatedMatchWins = matchWins if matchWins else team['matchwins']
    updatedCaptain = captain if captain else team['captain']
    updatedMembers = members if members else team["members"]
    updatedPoints = points if points else team['points']
    updatedmmr = mmr if mmr else team["mmr"]

    conn.execute("UPDATE teams SET name = ?, mapwins = ?, matchwins = ?, captain = ?, members = ?, points = ?, mmr = ? WHERE id = ?", (updatedName, updatedMapWins, updatedMatchWins, updatedCaptain, updatedMembers, updatedPoints, updatedmmr, id))

    conn.commit()
    conn.close()

    sortTeams()

    return redirect("/admin")

@app.route("/createTeam", methods=["POST"])
def createTeam():

    name = request.form.get("name").strip()
    mapwins = request.form.get("mapwins").strip()
    matchwins = request.form.get("matchwins").strip()
    captain = request.form.get("captain").strip()
    points = request.form.get("points").strip()
    mmr = request.form.get("mmr").strip()

    makeTeam(name, mapwins, matchwins, captain, points, mmr)
    sortTeams()
    return redirect("/admin")

@app.route("/deleteTeam/<int:id>", methods=["POST"])
def deleteTeamRoute(id):
    deleteTeam(id)
    return redirect("/admin")

def sortTeams():
    conn = get_db_connection()
    teams = conn.execute("SELECT id, mmr FROM teams").fetchall()

    array = []
    for i in range(0,len(teams)):
        array.append(teams[i])

    # bubble sort teams because data size is very low
    swap = True
    while swap:
        swap = False
        for i in range(0, len(array) - 1):
            if array[i]["mmr"] < array[i+1]["mmr"]:
                array[i], array[i + 1] = array[i + 1], array[i]
                swap = True
    
    # return places into database
    for i in range(0,len(array)):
        conn.execute("UPDATE teams SET place = ? WHERE id = ?", (i + 1, array[i]["id"]))
    conn.commit()
    conn.close()

    #procedure
            
# games

@app.route("/updateGame/<int:id>", methods=["POST"])
def updateGame(id):
    conn = get_db_connection()

    home = request.form.get("home").strip()
    away = request.form.get("away").strip()
    datetime = request.form.get("datetime").strip()
    homePlayers = request.form.get("homeplayers").strip()
    awayPlayers = request.form.get("awayplayers").strip()
    other = request.form.get("other").strip()
    
    game = conn.execute("SELECT * FROM games WHERE id = ?", (id,)).fetchone()

    updatedHome = home if home else game['home']
    updatedAway = away if away else game['away']
    updatedDatetime = datetime if datetime else game['datetime']
    updatedHomePlayers = homePlayers if homePlayers else game['homeplayers']
    updatedAwayPlayers = awayPlayers if awayPlayers else game["awayplayers"]
    updatedOther = other if other else game['other']

    conn.execute("UPDATE games SET home = ?, away = ?, datetime = ?, homeplayers = ?, awayplayers = ?, other = ? WHERE id = ?", (updatedHome, updatedAway, updatedDatetime, updatedHomePlayers, updatedAwayPlayers, updatedOther, id))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/deleteGame/<int:id>", methods=["POST"])
def deleteGameRoute(id):
    deleteGame(id)
    return redirect("/admin")

@app.route("/createGame", methods=["POST"])
def createGame():

    home = request.form.get("home").strip()
    away = request.form.get("away").strip()
    datetime = request.form.get("datetime").strip()

    makeGame(home, away, datetime)
    sortTeams()
    return redirect("/admin")




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