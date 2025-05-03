import sqlite3

def resetLogins():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("""

        DROP TABLE IF EXISTS logins

    """)

    c.execute("""

        CREATE TABLE logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            team TEXT,
            captain BOOLEAN DEFAULT 0,
            admin BOOLEAN DEFAULT 0
        )

    """)

    connect.commit()
    connect.close()

def resetTeams():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("""

        DROP TABLE IF EXISTS teams

    """)

    c.execute("""

        CREATE TABLE teams (
            name TEXT PRIMARY KEY NOT NULL,
            place INT NOT NULL,
            games INT NOT NULL,
            wins INT NOT NULL,
            captain TEXT NOT NULL,
            members TEXT,
            points INT
        )

    """)

    connect.commit()
    connect.close()

def makeTeam(name, place, games, wins, captain, members, points):  # feels OO to me but i dont think making it OO will help
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("INSERT INTO teams (name, place, games, wins, captain, members, points) VALUES (?, ?, ?, ?, ?, ?, ?)", (name, place, games, wins, captain, members, points))

    connect.commit()
    connect.close()

def deleteTeam(name):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DELETE FROM teams WHERE name = ?", (name,))

    connect.commit()
    connect.close()

def resetGames():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DROP TABLE IF EXISTS games")

    c.execute("""

        CREATE TABLE games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            winner TEXT,
            datetime DATETIME,
            homeplayers TEXT,
            awayplayers TEXT,
            other TEXT
        )

    """)

    connect.commit()
    connect.close()

def makeGame(home, away, datetime):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()
    c.execute("INSERT INTO games (home, away, datetime) VALUES (?, ?, ?)", (home, away, datetime))  
    connect.commit()
    connect.close()

def editGame(attribute, value, id):
    connect = sqlite3.connect("database.db")
    c= connect.cursor()
    c.execute(f"UPDATE games SET {attribute} = ? WHERE id = ?", (value, id))
    connect.commit()
    connect.close()





def main():
    loop = True
    while loop:
        answer = input(">")
        if answer == "rl":
            resetLogins()
        elif answer == "e":
            loop = False
        elif answer == "rt":
            resetTeams()
        elif answer == "mt":
            name = input("Name: ")
            place = int(input("Place: "))
            games = int(input("Games: "))
            wins = int(input("Wins: "))
            captain = input("Captain: ")
            members = input("All Members: ")
            points = int(input("Points: "))
            makeTeam(name, place, games, wins, captain, members, points)
        elif answer == "dt":
            name = input("name of team to delete: ")
            deleteTeam(name)
        elif answer == "rg":
            resetGames()
        elif answer == "eg":
            id = input("Id: ")
            attribute = input("attribute: ")
            value = input("value: ")
            editGame(attribute, value, id)
        elif answer == "mg":
            home = input("home: ")
            away = input("away: ")
            datetime = input("datetime: ")
            makeGame(home, away, datetime)


if __name__ == "__main__":
    main()