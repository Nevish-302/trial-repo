import os

from cs50 import SQL
import datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# This is how you do it

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    table = db.execute("SELECT * FROM inde WHERE user_id = ?", session["user_id"])
    Sel = {}
    # so that the initial sum is 0
    suma = 0
    for row in table:
        Sel[row["symbol"]] = lookup(row["symbol"])["price"]
        # Showing the current price and total value of stocks of a particular symbol
        suma += lookup(row["symbol"])["price"] * row["quantity"]
    return render_template("index.html", table=db.execute("SELECT * FROM inde WHERE user_id = ?", session["user_id"]), cash=db.execute("SELECT cash FROM users WHERE id = ?;", session["user_id"]), su=suma, Se=Sel)


@app.route("/change", methods=["GET", "POST"])
def change():
    if request.method == "GET":
        return render_template("change.html")
    # When the user entered information
    if request.method == "POST":
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # checking if confirmation is correct or null op password is null
        if not password or not confirmation or password != confirmation:
            return apology("Must Provide Password And Correct Confirmation")
        db.execute("UPDATE users SET hash = ?", generate_password_hash(password))
    return redirect("/")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    if request.method == "POST":
        result = lookup(str(request.form.get("symbol")))
        QTY = request.form.get("shares")
        # Checking if entered quantity is not non-numeric, or null or negative
        if not QTY.isnumeric():
            return apology("Write The Correct Quantity")
        qty = float(QTY)
        if not request.form.get("symbol") or not lookup(request.form.get("symbol")):
            return apology("Must Provide Symbol")
        if qty < 0 or not qty:
            return apology("Write The Correct Quantity")
        cash = db.execute("SELECT cash FROM users WHERE id = ?;", session["user_id"])
        # Checking if the user has the required quantity of cash
        if cash[0]["cash"] < qty * result["price"]:
            return ("Not Enough Cash To Buy Stocks")
        db.execute("INSERT INTO bght(user_id, symbol, quantity,  price, time) VALUES(?, ?, ?, ?, ?)",
                   session["user_id"], result["symbol"], qty, result["price"], datetime.datetime.now())
        # Updating two tables in a row, one for bought and one for index
        if not db.execute("SELECT * FROM inde WHERE user_id = ? AND symbol = ?", session["user_id"], result["symbol"]):
            db.execute("INSERT INTO inde(user_id, symbol, quantity) VALUES(?, ?, ?)", session["user_id"], result["symbol"], qty)
        else:
            db.execute("UPDATE inde SET quantity = ? WHERE user_id = ? AND symbol = ?;", float(db.execute(
                "SELECT quantity FROM inde WHERE user_id = ? AND symbol = ?", session["user_id"], result["symbol"])[0]["quantity"]) + qty, session["user_id"], result["symbol"])
        db.execute("UPDATE users SET cash = ? WHERE id = ?;", cash[0]["cash"] - qty * result["price"], session["user_id"])
        return redirect("/")


@app.route("/history")
@login_required
def history():
    # adding two tables sold and bought to one
    return render_template("history.html", table1=db.execute("SELECT * FROM bght WHERE user_id = ?", session["user_id"]), table2=db.execute("SELECT * FROM sold WHERE user_id = ?", session["user_id"]))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        # There must be a symbol to lookup
        if not request.form.get("symbol") or not lookup(request.form.get("symbol")):
            return apology("Must Provide Symbol")
        return render_template("quoted.html", result=lookup(request.form.get("symbol")))
    return apology("Unknown Error")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")
        # Checking password and confirmation
        confirmation = request.form.get("confirmation")
        if not name:
            return apology("Must Provide Username")
        user = []
        # Checking if the username already exists
        lis = db.execute("SELECT username FROM users")
        for row in lis:
            user.append(row["username"])
        if name in user:
            return apology("USERNAME already exists")
        if not password or not confirmation or password != confirmation:
            return apology("Must Provide Correct Password And Confirmation")
        else:
            # adding the new user to users table
            jolly = db.execute("INSERT INTO users(username, hash) VALUES(?, ?);", name, generate_password_hash(password))
            return render_template("login.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        return render_template("sell.html", select=db.execute("SELECT symbol FROM inde"))
    if request.method == "POST":
        result = lookup(str(request.form.get("symbol")))
        qty = float(request.form.get("shares"))
        cash = db.execute("SELECT cash FROM users WHERE id = ?;", session["user_id"])
        # checking if the use has correct quantity of cash or the quantity is not null or sth
        if qty < 0 or not qty:
            return apology("Write The Correct Quantity")
        Qty = float(db.execute("SELECT quantity FROM inde WHERE user_id = ? AND symbol = ?",
                    session["user_id"], result["symbol"])[0]["quantity"])
        if Qty < qty or not Qty:
            return apology("You Do not Have Enough Stocks")
        db.execute("INSERT INTO sold(user_id, symbol, quantity, price, time) VALUES(?, ?, ?, ?, ?)",
                   session["user_id"], result["symbol"], qty, result["price"], datetime.datetime.now())
        db.execute("UPDATE inde SET quantity = ? WHERE user_id = ? AND symbol = ?;",
                   Qty - qty, session["user_id"], result["symbol"])
        db.execute("UPDATE users SET cash = ? WHERE id = ?;",
                   cash[0]["cash"] + qty * result["price"], session["user_id"])
        return redirect("/")
