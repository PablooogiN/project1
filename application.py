import os

from flask import Flask, session, render_template, jsonify, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
import simplejson

app = Flask(__name__)
app.secret_key = 'any random string'

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
	if 'user_id' in session:
		user_id = session['user_id']
		return render_template("index.html")
	return redirect(url_for('login'))

@app.route("/login", methods = ['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form.get('username')
		password = request.form.get('password')
		user_id = db.execute("SELECT id FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).fetchone()
		if user_id is None:
			return "wrong information"
		session['user_id'] = user_id.id
		return redirect(url_for('index'))
	return render_template("login.html")

@app.route('/logout')
def logout():
	# remove the username from the session if it is there
	session.pop('user_id', None)
	return redirect(url_for('index'))

@app.route("/register", methods = ['GET', 'POST'])
def register():
	if request.method == 'POST':
	    username = request.form.get('username')
	    password = request.form.get('password')
	    email = request.form.get('email')

	    if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0:
	    	return "username already taken"
	    if db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).rowcount != 0:
	    	return "email already taken"
	    #username is good to use
	    db.execute("INSERT INTO users (username, password, email) VALUES (:username, :password, :email)", {"username": username, "password": password, "email": email})
	    #created user
	    db.commit()

	    return redirect(url_for('index'))
	    # try:
	    #     #see if user/ email is already taken
	    # except ValueError:
	    #     return render_template("error.html", message="User already exists")

	    # # Make sure flight exists.
	    # if db.execute("SELECT * FROM flights WHERE id = :id", {"id": flight_id}).rowcount == 0:
	    #     return render_template("error.html", message="No such flight with that id.")
	    # db.execute("INSERT INTO passengers (name, flight_id) VALUES (:name, :flight_id)",
	    #         {"name": name, "flight_id": flight_id})
	    # #create user
	    # db.commit()
	return render_template("register.html")

@app.route("/results", methods=["POST"])
def results():
	search = request.form.get("search")
	search_input = "%" + search + "%"
	searchResults = db.execute("SELECT * FROM books where isbn LIKE :search_input OR title LIKE :search_input OR author LIKE :search_input OR year::VARCHAR LIKE :search_input", {"search_input": search_input})
	if searchResults.rowcount == 0:
		return render_template("index.html") , 404
	db.commit()
	return render_template("results.html", books=searchResults)

@app.route("/book/<string:isbn>")
def book(isbn):
	#check if is in the databse and get api from goodreads
	book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
	# if book is None:
	#return render_template("index.html")
	reviewdata = ""
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "1joi2uk4Xi7Orewmw7RA", "isbns": book.isbn})
	if res.status_code == 200:
		data = res.json()
		reviewdata = data['books'][0]
		print(reviewdata)
	reviews = db.execute("SELECT rating, review, username FROM reviews INNER JOIN users ON reviews.user_id = users.id WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
	return render_template("book.html", book=book, grbook=reviewdata, reviews=reviews)

@app.errorhandler(404)
def page_not_found(error):
	return render_template("404.html"), 404

@app.route("/api/<string:isbn>")
def book_api(isbn):
	# get the book value
	book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
	if book is None:
		return render_template("index.html"), 404
	ratings = db.execute("SELECT count(*), AVG(rating) FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
	average = 0
	count = 0
	if ratings.count > 0:
		average = ratings.avg
		count = ratings.count
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "1joi2uk4Xi7Orewmw7RA", "isbns": book.isbn})
	if res.status_code == 200:
		data = res.json()
		reviewdata = data['books'][0]
		average = (count*average + reviewdata['work_ratings_count']*float(reviewdata['average_rating']))/(count+reviewdata['work_ratings_count'])
		count += reviewdata['work_ratings_count']
	return jsonify(
		title= book.title,
		author= book.author,
		year= book.year,
		isbn= book.isbn,
		review_count= count,
		average_score= float(average)
	) 
