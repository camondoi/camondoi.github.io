import os

from cs50 import SQL
# from flask import Flask, flash, redirect, render_template, request, session
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, human_format

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    
    all_group_type = db.execute(
        "SELECT group_type FROM sp500 GROUP BY group_type"
    )
    #if request.method == "GET":
    if (request.args.get('g')):
        group_type = request.args.get('g')
        stocks = db.execute(
                "SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 WHERE group_type = ?", group_type
        )
        #app.logger.info('%s index page - Stocks select: ', group_type)
    else:
        if (request.args.get('p')):
            page = request.args.get('p')
            from_item = int(page)*20
            to_item = 20
            if from_item == 480:
                to_item = 30
            stocks = db.execute(
                "SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 LIMIT ? OFFSET ?;", to_item, from_item
            )
            #app.logger.info('%s index page - Stocks select: ', stocks)
        else:
            stocks = db.execute(
                "SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 LIMIT 20"
            )
    
    
    empty_list = []
    sp500_symbol = "^GSPC"
    #sp500_symbol = "BRK-B"
    
    sp500_result = lookup(sp500_symbol)
    sp500_current_price = float(sp500_result['price'])
    sp500 ={'symbol': sp500_symbol,'current_price': sp500_current_price }
    
    for stock in stocks:
        result = lookup(stock['symbol'])
        current_price = float(result['price'])

        if (stock['symbol']=="BRK-B"):
            stock['symbol'] = "BRK.B"
            
        market_cap = human_format(current_price*stock['volume'])
        item = {'id': stock['id'], 'symbol': stock['symbol'], 'name': stock['name'], 'volume': human_format(stock['volume']),
                 'link_wiki': stock['link_wiki'],'group_id': stock['group_type'], 'current_price': current_price, 'market_cap': market_cap}
                
        empty_list.append(item)

    return render_template("index.html", stocks=empty_list, sp500 = sp500, all_group_type=all_group_type)
    # return apology("TODO  after Login - INDEX")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol of Stock", 400)

        # Ensure password was submitted
        elif not request.form.get("shares"):
            return apology("must provide number of shares", 400)
        else:
            # check the amount of money
            money = db.execute(
                "SELECT cash FROM users WHERE id = ?", session["user_id"]
            )
            result = lookup(request.form.get("symbol"))
            if (result):
                price = float(result['price'])
                shares = int(request.form.get("shares"))
                for k, v in money[0].items():
                    money_left = float(v)  # float(new_list[0])
                # money_left =float(new_list[0])
                if (price*shares > money_left):
                    return apology("NOT enough money to buy", 403)
                else:
                    # Query database insert into bought stock
                    rows = db.execute(
                        "INSERT INTO purchase (symbol, amount, price, user_id) VALUES (?, ?, ? , ?)",
                        request.form.get("symbol"), shares, price, session["user_id"]
                    )
                    # Query database update remain money of user
                    rows = db.execute(
                        "UPDATE users SET cash = ? WHERE id = ?",
                        money_left - price*shares, session["user_id"]
                    )

            else:
                price = 0
                return apology("STOCK symbol not found", 400)

        return redirect("/buy")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        stocks = db.execute(
            "SELECT symbol, amount, price, created_at FROM purchase WHERE user_id = ?", session["user_id"]
        )
        #app.logger.info('%s Stocks select: ', stocks)
        return render_template("buy.html", stocks=stocks)

    # return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    stocks = db.execute(
        "SELECT symbol, amount, price, created_at FROM purchase WHERE user_id = ?", session["user_id"]
    )
    empty_list = []
    total = 0
    inscrease = 0
    for stock in stocks:
        result = lookup(stock['symbol'])
        current_price = round(float(result['price']), 2)
        price = round(stock['price'], 2)
        item = {'symbol': stock['symbol'], 'amount': stock['amount'],
                'price': price, 'created_at': stock['created_at'], 'current_price': current_price}
        empty_list.append(item)
        total += current_price*int(stock['amount'])
        inscrease += (current_price - int(stock['price']))*int(stock['amount'])
    inscrease = round(inscrease, 2)
    money = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"]
    )
    for k, v in money[0].items():
        money_left = float(v)
    return render_template("history.html", stocks=empty_list, total=total, cash=money_left, ins=inscrease)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
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
    """Get stock quote."""
    if request.method == "POST":
        stock_symbol = request.form.get("symbol")
        stock_list = stock_symbol.split()
        
        placeholders = '('
        for i in stock_list:
            placeholders += "'" + i + "',"
        placeholders = placeholders[:-1]
        placeholders += ')'
        
        app.logger.info('Stocks list: %s', placeholders)
        # IN ?", stock_list        ({placeholders})
        # Construct the query
        
        query = f"SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 WHERE symbol IN {placeholders}"
        
        app.logger.info('Query: %s', query)
        
        stocks = db.execute(query)
        
        # "SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 WHERE symbol IN ?", placeholders
        # SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 WHERE symbol IN ['NVDA', 'APPL'];
        if (stocks):
            empty_list = []
            for stock in stocks:
                result = lookup(stock['symbol'])
                current_price = float(result['price'])

                if (stock['symbol']=="BRK-B"):
                    stock['symbol'] = "BRK.B"
                    
                market_cap = human_format(current_price*stock['volume'])
                item = {'id': stock['id'], 'symbol': stock['symbol'], 'name': stock['name'], 'volume': human_format(stock['volume']),
                        'link_wiki': stock['link_wiki'],'group_id': stock['group_type'], 'current_price': current_price, 'market_cap': market_cap}
                empty_list.append(item)
            return render_template("quoted.html", stocks=empty_list, stock_symbol=stock_symbol)
        else:
            return apology("Stock not found in S&P 500", 400)

    else:
        stocks = db.execute(
            "SELECT id, symbol, name, volume, link_wiki, group_type FROM sp500 LIMIT 10"
        )
        empty_list = []
        for stock in stocks:
            result = lookup(stock['symbol'])
            current_price = float(result['price'])

            if (stock['symbol']=="BRK-B"):
                stock['symbol'] = "BRK.B"
                
            market_cap = human_format(current_price*stock['volume'])
            item = {'id': stock['id'], 'symbol': stock['symbol'], 'name': stock['name'], 'volume': human_format(stock['volume']),
                    'link_wiki': stock['link_wiki'],'group_id': stock['group_type'], 'current_price': current_price, 'market_cap': market_cap}
            empty_list.append(item)
        return render_template("quote.html", stocks=empty_list)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Password not match", 400)
        else:
            # Query database for username
            rows = db.execute(
                "SELECT * FROM users WHERE username = ?", request.form.get("username")
            )
            if len(rows) != 0:
                return apology("Usernam already exist", 400)

        # if everything OK, insert new user to database

        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        # https://werkzeug.palletsprojects.com/en/2.3.x/utils/#werkzeug.security.generate_password_hash
        rows = db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)", username, password
        )
        return apology(f"User {username} registered sucessfull", 200)
        """
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)
        """
        # Remember which user has logged in
        # session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    i = 0
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol of Stock", 403)

        # Ensure password was submitted
        elif not request.form.get("shares"):
            return apology("must provide number of shares", 403)
        else:
            amount = db.execute(
                "SELECT SUM(amount) FROM purchase  WHERE symbol = ? GROUP BY symbol", request.form.get(
                    "symbol")
            )
            app.logger.info('%s Amount of Shares: ', amount)
            # INFO: [{'SUM(amount)': 7}] Amount of Shares:
            for k, v in amount[0].items():
                number_shares = int(v)
            shares = int(request.form.get("shares"))
            shares_sold = -shares
            if (shares > number_shares):
                return apology("NOT Shares to sell", 403)
            else:
                result = lookup(request.form.get("symbol"))
                if (result):
                    price = float(result['price'])

                    sell_stock = db.execute(
                        "INSERT INTO purchase (symbol, amount, price, user_id) VALUES (?, ?, ? , ?)",
                        request.form.get("symbol"), shares_sold, price, session["user_id"]
                    )
                    # Query database update remain money of user
                    rows = db.execute(
                        "UPDATE users SET cash = cash +? WHERE id = ?",
                        price*shares, session["user_id"]
                    )
                    i = 1  # sell success
                    sell_stock = request.form.get("symbol")
                    sell_amount = shares
                    sell_price = price
                else:
                    return apology("Can not get price of Stock to sell", 403)

            stocks = db.execute(
                "SELECT symbol, amount, price, created_at FROM purchase WHERE user_id = ?", session[
                    "user_id"]
            )
            empty_list = []
            total = 0
            inscrease = 0
            for stock in stocks:
                result = lookup(stock['symbol'])
                current_price = float(result['price'])
                item = {'symbol': stock['symbol'], 'amount': stock['amount'],
                        'price': stock['price'], 'created_at': stock['created_at'], 'current_price': current_price}
                empty_list.append(item)
                total += current_price*int(stock['amount'])
                inscrease += (current_price - int(stock['price']))*int(stock['amount'])
            inscrease = round(inscrease, 2)
            money = db.execute(
                "SELECT cash FROM users WHERE id = ?", session["user_id"]
            )
            for k, v in money[0].items():
                money_left = float(v)
            return render_template("sell.html", stocks=empty_list, total=total, cash=money_left, ins=inscrease,
                                   sell_stock=sell_stock, sell_amount=sell_amount, sell_price=sell_price, i=i)
    else:
        stocks = db.execute(
            "SELECT symbol, amount, price, created_at FROM purchase WHERE user_id = ?", session["user_id"]
        )
        #app.logger.info('%s index page - Stocks select: ', stocks)
        # [{'symbol': '', 'amount': 0, 'price': 0.0, 'created_at': '2024-01-01 12:00:00', 'current_price': 0.0}]
        empty_list = []
        total = 0
        inscrease = 0
        for stock in stocks:
            result = lookup(stock['symbol'])
            current_price = float(result['price'])
            item = {'symbol': stock['symbol'], 'amount': stock['amount'],
                    'price': stock['price'], 'created_at': stock['created_at'], 'current_price': current_price}
            empty_list.append(item)
            total += current_price*int(stock['amount'])
            inscrease += (current_price - int(stock['price']))*int(stock['amount'])
        inscrease = round(inscrease, 2)
        money = db.execute(
            "SELECT cash FROM users WHERE id = ?", session["user_id"]
        )
        for k, v in money[0].items():
            money_left = float(v)
        return render_template("sell.html", stocks=empty_list, total=total, cash=money_left, ins=inscrease, i=i)
