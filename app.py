# Import necessary libraries
from distutils.util import execute
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from pymbta3 import Alerts
from pymbta3 import Predictions
import os
import subprocess


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ITCapstone2024!'  # Replace with a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'ITCapstone2024!'

# Initialize SQLAlchemy database
# db = (app)

#Use for the login page
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Define User model for SQL database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    phonenumber = db.Column(db.String(120), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Page Routes 
@app.route('/')
def home():
    logo_urls = [
        '/static/MBTAD_title_w_Logo.png',
    ]
    return render_template('index.html', logo_urls=logo_urls)

# Initialize Predictions API with your MBTA V3 API key
predictions_api = Predictions(key=os.getenv('MBTA_API_KEY'))

#RedLine Line Predictions

from flask import Flask, render_template
import subprocess


@app.route('/predictions')
def predictions():
    # Parameters to pass to the script
    line = 'Red'
    destination = 'Alewife'
    
    # Execute the script
    try:
        result = subprocess.run(['python', 'test.py', line, destination], capture_output=True, text=True)
        output = result.stdout
    except Exception as e:
        output = f"Failed to execute script: {str(e)}"
    
    return render_template('predictions.html', output=output)

# Route for registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Hash password before storing it
        hashed_password = generate_password_hash(password)
        first_name = request.form['firstname']
        last_name = request.form['lastname']
        email = request.form['email']
        phonenumber = request.form['phonenumber']
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists, please choose another.')
            return redirect(url_for('register'))
        else:
            # Create a new user and add to the database
            new_user = User(username=username, password=hashed_password, first_name=first_name, last_name=last_name, email=email, phonenumber=phonenumber)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Now available to Login.')
            return redirect(url_for('login'))
    return render_template('register.html')

# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username exists
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            flash('Login successful!')
            return redirect(url_for('profile'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')

# Route for the profile page
@app.route('/profile')
def profile():
    return render_template('profile.html')


#class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Line(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    line_id = db.Column(db.Integer, db.ForeignKey('line.id'), nullable=False)

# Line Route
@app.route('/lines')
def lines():
    return render_template('lines.html')
@app.route('/blueline')
def blueline():
    return render_template('BLUELINE.html')
@app.route('/greenline')
def greenline():
    return render_template('GREENLINE.html')
@app.route('/orangeline')
def orangeline():
    return render_template('ORAnGELINE.html')
@app.route('/redline')
def redline():
    try:
        # Assuming you have some function to fetch predictions
        predictions = predictions_api.get(stop='place-alfcl', route='Red')
        predictions_data = predictions['data'] if 'data' in predictions else []
        
        # Now pass the retrieved predictions to the template
        return render_template('redline.html', predictions=predictions_data)
    except Exception as e:
        # In case of an error, you might want to log it and/or handle it appropriately
        print(f"Error fetching predictions: {e}")
        # Optionally pass an empty list or some default data structure
        return render_template('redline.html', predictions=[])


# Contact Route
@app.route('/contact')
def contact():
    return render_template('contact.html')
# Contact Route
@app.route('/about')
def about():
    return render_template('about.html')


# Route to handle predictions retrieval and render the template with the predictions
#@app.route('/get_predictions', methods=['POST'])
#def get_predictions():
    line = request.form['line']
    destination = request.form['destination']

    # Your existing backend code to retrieve predictions
    # Replace this with your actual predictions retrieval logic

    # For demonstration, let's assume predictions and alerts are retrieved
    predictions = ["Prediction 1", "Prediction 2"]
    alerts = ["Alert 1", "Alert 2"]

    # Render template with predictions and alerts
    return render_template('about.html', predictions=predictions)



@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if request.method == 'POST':
        username = request.form['username']
        station_id = request.form['station_id']
        line_id = request.form['line_id']
        user = User.query.filter_by(username=username).first()
        if user:
            favorite = Favorite(user_id=user.id, station_id=station_id, line_id=line_id)
            db.session.add(favorite)
            db.session.commit()
            return "Favorite added successfully"
        else:
            return "User not found"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

#<===================================================Backend Code=====================================================>

current_dateTime = datetime.now()

print(current_dateTime)

keyy = "99352d4263d4425e89446962e66a7cc7"
at = Alerts(key=keyy)
pt = Predictions(key=keyy)
theline = ""

line = input("Line: ")
if line == "red":
    theline = "Red"
    station = "Station.txt"
    codee = "StationCode.txt"
elif line == "orange":
    theline = "Orange"
    station = "StationO.txt"
    codee = "StationCodeO.txt"
elif line == "green":
    pie = input("Branch: ")
    if pie == "b":
        theline = "Green-B"
        station = "StationGB.txt"
        codee = "StationCodeGB.txt"
    elif pie == "c":
        theline = "Green-C"
        station = "StationGC.txt"
        codee = "StationCodeGC.txt"
    elif pie == "d":
        theline = "Green-D"
        station = "StationGD.txt"
        codee = "StationCodeGD.txt"
    elif pie == "e":
        theline = "Green-E"
        station = "StationGE.txt"
        codee = "StationCodeGE.txt"
    else:
        print("error")
        station = "StationG.txt"
        codee = "StationCodeG.txt"
        quit()
elif line == "blue":
    theline = "Blue"
    station = "StationB.txt"
    codee = "StationCodeB.txt"
else:
    print("error")
    exit()

# Open station file for reading
Rmyfile = open(station, "rt")
contents = Rmyfile.read()
x = contents.split()

Rmyfile2 = open(codee, "rt")
contents2 = Rmyfile2.read()
x2 = contents2.split()

p = -1

# Input full name for red line list
dest = input("Lookup Destination: ")
if dest not in contents:
    print("Not Found")
else:
    for i in x:
        p = p + 1
        if i == dest:
            print(p)
# end loop on successful search
            break
# collects code word depending on placement in list
y = x2[p]

alerts = at.get(stop=y)
predictions = pt.get(stop=y, route=[theline])

# Find the short header for the alert
for alert in alerts['data']:
    alertstr = alert['attributes']['short_header']
    print(alertstr)

# Find arrival times for prediction
# 0 = outbound 1 = inbound
for prediction in predictions['data']:
    predictionstr = str(prediction['attributes']['arrival_time']), str(prediction['attributes']['direction_id'])
    print(predictionstr)
