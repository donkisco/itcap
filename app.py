# Import necessary libraries
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_login import UserMixin
from flask_cors import CORS
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from pymbta3 import Alerts
from pymbta3 import Predictions
import logging

import os

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ITCapstone2024!'  # Replace with a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'ITCapstone2024!'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=14)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True


# Initialize SQLAlchemy database
# db = (app)

#Use for the login page
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Define User model for SQL database


class User(db.Model, UserMixin):  # Include UserMixin here
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
        '/static/image.png',
    ]
    return render_template('index.html', logo_urls=logo_urls)

# Initialize Predictions API with your MBTA V3 API key
predictions_api = Predictions(key=os.getenv('MBTA_API_KEY'))

#RedLine Line Predictions
@app.route('/api/predictions/<string:stop_id>')
def get_predictions(stop_id):
    # Fetch predictions for a specific stop
    try:
        predictions = predictions_api.get(stop=stop_id, route='Red')
        return jsonify(predictions=predictions['data'])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

        

@app.route('/alewife')
def alewife():
    try:
        # Fetch predictions for Alewife Station; replace 'place-alfcl' with the actual stop ID
        predictions = predictions_api.get(stop='place-davis', route='Red')
        predictions_data = predictions['data'] if 'data' in predictions else []

        # Get the current time with timezone
        now = datetime.now(tz=pytz.timezone('America/New_York'))

        # Format and calculate minutes until train departure
        formatted_predictions = []
        for p in predictions_data:
            departure_time = p['attributes']['departure_time']
            if departure_time:
                departure_datetime = datetime.fromisoformat(departure_time[:-6]).replace(tzinfo=pytz.timezone('America/New_York'))
                minutes_until_departure = int((departure_datetime - now).total_seconds() / 60)
                formatted_predictions.append((minutes_until_departure, p['attributes']['direction_id']))

        # Filter predictions based on direction ID
        braintree_predictions = [minutes for minutes, direction in formatted_predictions if direction == 0 and minutes >= 0]
        ashmont_predictions = [minutes for minutes, direction in formatted_predictions if direction == 1 and minutes >= 0]

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return JSON if it's an AJAX request
            return jsonify(braintree_predictions=braintree_predictions, ashmont_predictions=ashmont_predictions)

        # Render page normally if not an AJAX request
        return render_template('alewife.html', braintree_predictions=braintree_predictions, 
                               ashmont_predictions=ashmont_predictions)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error=str(e))
        return render_template('alewife.html', braintree_predictions=[], ashmont_predictions=[], error="Failed to fetch predictions.")



@app.route('/station/<string:line>/<string:station_name>')
def porter(line, station_name):
    # Example line and destination - adjust based on actual use case
    line = line
    destination = station_name # Ensure 'Porter' is correctly formatted and exists in your station list

    try:
        # Fetch predictions and alerts
        predictions, alerts = get_station_predictions(line, destination)
        if predictions is None:
            return jsonify({'error': 'Destination not found'}), 404  # Return JSON error message with HTTP 404 status code

        now = datetime.now(tz=pytz.timezone('America/New_York'))
        formatted_predictions = process_predictions(predictions['data'], now)

        # Pass the structured predictions as JSON
        return jsonify({
            'alewife_predictions': formatted_predictions['alewife_predictions'],
            'braintree_predictions': formatted_predictions['braintree_predictions'],
            'ashmont_predictions': formatted_predictions['ashmont_predictions'],
            'alerts': alerts  # Optionally include alerts if they are relevant
        })
    except Exception as e:
        # It's usually not good practice to expose raw exception messages in production
        # Consider logging the exception and returning a generic error message
        print(f"Error handling request: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500  # Internal Server Error

# @app.route('/station/<string:station_name>')
# def porter(station_name):
#     # Example line and destination - adjust based on actual use case
#     line = 'red'
#     destination = station_name  # Ensure 'Porter' is correctly formatted and exists in your station list

#     try:
#         # Fetch predictions and alerts
#         predictions, alerts = get_station_predictions(line, destination)
#         if predictions is None:
#             message = "Destination not found"
#             return render_template('REDLINE.html', message=message, alewife_predictions=[], braintree_predictions=[], ashmont_predictions=[])

#         now = datetime.now(tz=pytz.timezone('America/New_York'))
#         formatted_predictions = process_predictions(predictions['data'], now)

#         # Pass the structured predictions to the HTML template
#         return render_template('REDLINE.html', message="Predictions fetched successfully",
#                                alewife_predictions=formatted_predictions['alewife_predictions'],
#                                braintree_predictions=formatted_predictions['braintree_predictions'],
#                                ashmont_predictions=formatted_predictions['ashmont_predictions'])
#     except Exception as e:
#         return render_template('REDLINE.html', message=str(e), alewife_predictions=[], braintree_predictions=[], ashmont_predictions=[])



def process_predictions(predictions_data, now):
    formatted_predictions = {'alewife_predictions': [], 'braintree_predictions': [], 'ashmont_predictions': [], 'worderland_predictions': [], 'bowdoin_predictions': [], 'governamentcenter_predictions': []}
    for p in predictions_data:
        attrs = p.get('attributes', {})
        departure_time = attrs.get('departure_time')
        if departure_time:
            try:
                # Safely parse and calculate time
                departure_datetime = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                departure_datetime = departure_datetime.astimezone(pytz.timezone('America/New_York'))
                minutes_until_departure = int((departure_datetime - now).total_seconds() / 60)

                # Append formatted time directly
                direction_id = attrs.get('direction_id')
                if direction_id == 0:
                    formatted_predictions['alewife_predictions'].append({'departure_time': f"{minutes_until_departure} mins"})
                elif direction_id == 1:
                    formatted_predictions['braintree_predictions'].append({'departure_time': f"{minutes_until_departure} mins"})
                elif direction_id == 2:
                    formatted_predictions['ashmont_predictions'].append({'departure_time': f"{minutes_until_departure} mins"})
            except Exception as e:
                # Log errors but continue processing
                print(f"Error processing prediction: {e}")
    return formatted_predictions





def get_station_predictions(line, destination):
    key = "99352d4263d4425e89446962e66a7cc7"
    at = Alerts(key=key)
    pt = Predictions(key=key)

    # Define station mapping
    mapping = {
        'red': ('Station.txt', 'StationCode.txt'),
        'orange': ('StationO.txt', 'StationCodeO.txt'),
        'green-b': ('StationGB.txt', 'StationCodeGB.txt'),
        'green-c': ('StationGC.txt', 'StationCodeGC.txt'),
        'green-d': ('StationGD.txt', 'StationCodeGD.txt'),
        'green-e': ('StationGE.txt', 'StationCodeGE.txt'),
        'blue': ('StationB.txt', 'StationCodeB.txt')
        
    }

    # Get the file names based on line
    files = mapping.get(line, None)
    if not files:
        return None, f"No files found for line {line}"

    station_file, code_file = files

    # Read station and code data
    try:
        with open(station_file, 'rt') as file:
            stations = file.read().split()
        with open(code_file, 'rt') as file:
            codes = file.read().split()
    except FileNotFoundError:
        return None, "File not found. Check your file paths and names."

    # Check if destination is valid
    if destination not in stations:
        return None, f"Destination {destination} not found in stations."

    # Retrieve index and ensure index is within bounds for codes
    index = stations.index(destination)
    if index >= len(codes):
        return None, f"No code available for {destination}. Index out of range."

    station_code = codes[index]

    # Fetching alerts and predictions
    alerts = at.get(stop=station_code)
    predictions = pt.get(stop=station_code, route=[line.capitalize()])
    return predictions, alerts


def station_predictions(station_name):
    line = 'red','blue','orange','green'  # Assuming all these stations are on the 'red' line for the example
    try:
        # Fetch predictions and alerts
        predictions, alerts = get_station_predictions(line, station_name)
        if predictions is None:
            message = "Destination not found"
            return render_template('REDLINE.html', 'BLUELINE.html', message=str(e), alewife_predictions=[], braintree_predictions=[], ashmont_predictions=[], wonderland_predictions=[], bowdoin_predictions=[], governmentcenter_predictions=[])

        now = datetime.now(tz=pytz.timezone('America/New_York'))
        formatted_predictions = process_predictions(predictions['data'], now)

        # Pass the structured predictions to the HTML template
        return render_template('REDLINE.html', message=f"Predictions fetched successfully for {station_name}",
                               alewife_predictions=formatted_predictions['alewife_predictions'],
                               braintree_predictions=formatted_predictions['braintree_predictions'],
                               ashmont_predictions=formatted_predictions['ashmont_predictions'],
                               wonderland_predictions=formatted_predictions['wonderland_predictions'],
                               bowdoin_predictions=formatted_predictions['bowdoin_predictions'],
                               governmentcenter_predictions=formatted_predictions['governmentcenter_predictions'],)
    except Exception as e:
        return render_template('REDLINE.html', 'BLUELINE.html', message=str(e), alewife_predictions=[], braintree_predictions=[], ashmont_predictions=[], wonderland_predictions=[], bowdoin_predictions=[], governmentcenter_predictions=[])




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
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash('Login successful!')
            return redirect(url_for('profile'))  # Redirect to profile
        else:
            flash('Invalid username or password.')
    return render_template('login.html')



# Route for the profile page
@app.route('/profile')
 # Ensure that only logged-in users can access this page
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
