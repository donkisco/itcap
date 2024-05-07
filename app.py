# Import necessary libraries
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_wtf import csrf, CSRFProtect
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
# Set the session lifetime to 2 days
app.permanent_session_lifetime = timedelta(days=2)
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
    try:
        predictions, alerts = get_station_predictions(line, station_name)
        if predictions is None:
            return jsonify({'error': 'Destination not found'}), 404

        now = datetime.now(tz=pytz.timezone('America/New_York'))
        formatted_predictions = process_predictions(predictions['data'], now)

        # Dynamically build the response based on what's available in formatted_predictions
        response = {k: v for k, v in formatted_predictions.items() if v}  # Include only non-empty lists
        if alerts:
            response['alerts'] = alerts  # Optionally include alerts if they are relevant
        
        return jsonify(response)
    except Exception as e:
        print(f"Error handling request: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500



def process_predictions(predictions_data, now):
    formatted_predictions = {}
    for p in predictions_data:
        attrs = p.get('attributes', {})
        departure_time = attrs.get('departure_time')
        if departure_time:
            try:
                departure_datetime = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                departure_datetime = departure_datetime.astimezone(pytz.timezone('America/New_York'))
                minutes_until_departure = int((departure_datetime - now).total_seconds() / 60)

                direction_id = attrs.get('direction_id')
                direction_key = f'direction_{direction_id}_predictions'
                if direction_key not in formatted_predictions:
                    formatted_predictions[direction_key] = []
                formatted_predictions[direction_key].append({'departure_time': f"{minutes_until_departure} mins"})
            except Exception as e:
                print(f"Error processing prediction: {e}")
    return formatted_predictions





def get_station_predictions(line, destination):
    key = "99352d4263d4425e89446962e66a7cc7"
    at = Alerts(key=key)
    pt = Predictions(key=key)

    # Define station mapping for all lines and branches
    mapping = {
        'red': ('Station.txt', 'StationCode.txt'),
        'orange': ('StationO.txt', 'StationCodeO.txt'),
        'blue': ('StationB.txt', 'StationCodeB.txt'),  # Assuming Blue line stations
        'green-b': ('StationGB.txt', 'StationCodeGB.txt'),
        'green-c': ('StationGC.txt', 'StationCodeGC.txt'),
        'green-d': ('StationGD.txt', 'StationCodeGD.txt'),
        'green-e': ('StationGE.txt', 'StationCodeGE.txt')
    }

    # Check which green branch or handle other lines
    if line == "green":
        print("Select branch: b, c, d, or e")
        branch = input("Branch: ").strip().lower()
        if branch in ['b', 'c', 'd', 'e']:
            line = f"green-{branch}"
        else:
            return None, f"Invalid Green line branch: {branch}"

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
    predictions = pt.get(stop=station_code, route=[line.split('-')[0].capitalize()])
    return predictions, alerts


def get_station_predictions2(line, destination, branch):
    key = "99352d4263d4425e89446962e66a7cc7"
    at = Alerts(key=key)
    pt = Predictions(key=key)

    # Define station mapping for all lines and branches
    mapping = {
        'red': ('Station.txt', 'StationCode.txt'),
        'orange': ('StationO.txt', 'StationCodeO.txt'),
        'blue': ('StationB.txt', 'StationCodeB.txt'),  # Assuming Blue line stations
        'Green-B': ('StationGB.txt', 'StationCodeGB.txt'),
        'Green-C': ('StationGC.txt', 'StationCodeGC.txt'),
        'Green-D': ('StationGD.txt', 'StationCodeGD.txt'),
        'Green-E': ('StationGE.txt', 'StationCodeGE.txt')
    }

    # Check which green branch or handle other lines
    if line == "green":
        print("Select branch: b, c, d, or e")
        
        if branch in ['b', 'c', 'd', 'e']:
            line = f"Green-{branch.capitalize()}"
        else:
            return None, f"Invalid Green line branch: {branch}"

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
    predictions = pt.get(stop=station_code, route=[line])
    return predictions, alerts


@app.route('/greenline/<string:branch>/<string:station_name>')
def green_line(branch, station_name):
    line = "green"
    if branch not in ['b', 'c', 'd', 'e']:
        return jsonify({'error': 'Invalid Green Line branch specified'}), 400

    try:
        predictions, alerts = get_station_predictions2(line, station_name, branch)

        #print(predictions)
        if predictions is None:
            return jsonify({'error': 'Destination not found'}), 404

        now = datetime.now(tz=pytz.timezone('America/New_York'))
        formatted_predictions = process_predictions2(predictions['data'], now)

        # Dynamically build the response based on what's available in formatted_predictions
        response = {k: v for k, v in formatted_predictions.items() if v}  # Include only non-empty lists
        if alerts:
            response['alerts'] = alerts  # Optionally include alerts if they are relevant
        
        return jsonify(response)
    except Exception as e:
        print(f"Error handling request for Green Line {branch}: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500



def process_predictions2(predictions_data, now):
    formatted_predictions = {}
    for p in predictions_data:
        attrs = p.get('attributes', {})
        departure_time = attrs.get('departure_time')
        
        # Proceed only if departure_time is not None
        if departure_time:
            departure_datetime = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
            departure_datetime = departure_datetime.astimezone(pytz.timezone('America/New_York'))
            minutes_until_departure = int((departure_datetime - now).total_seconds() / 60)

            direction_id = attrs.get('direction_id')
            direction_key = f'direction_{direction_id}_predictions'
            if direction_key not in formatted_predictions:
                formatted_predictions[direction_key] = []
            formatted_predictions[direction_key].append({'departure_time': f"{minutes_until_departure} mins"})
        else:
            # Handle cases where departure time is None
            direction_id = attrs.get('direction_id')
            direction_key = f'direction_{direction_id}_predictions'
            if direction_key not in formatted_predictions:
                formatted_predictions[direction_key] = []
            formatted_predictions[direction_key].append({'departure_time': "No scheduled departure"})

    return formatted_predictions



def process_predictions(predictions_data, now):
    formatted_predictions = {}
    for p in predictions_data:
        attrs = p.get('attributes', {})
        departure_time = attrs.get('departure_time')
        if departure_time:
            departure_datetime = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
            departure_datetime = departure_datetime.astimezone(pytz.timezone('America/New_York'))
            minutes_until_departure = int((departure_datetime - now).total_seconds() / 60)

            direction_id = attrs.get('direction_id')
            direction_key = f'direction_{direction_id}_predictions'
            if direction_key not in formatted_predictions:
                formatted_predictions[direction_key] = []
            formatted_predictions[direction_key].append({'departure_time': f"{minutes_until_departure} mins"})

    return formatted_predictions



@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if not current_user.is_authenticated:
        return jsonify({'message': 'User not authenticated'}), 401

    station_id = int(request.form['station_id'])
    line_id = int(request.form['line_id'])
    is_favorite = request.form['favorite'] == 'true'

    if is_favorite:
        # Check if already a favorite
        existing_favorite = Favorite.query.filter_by(user_id=current_user.id, station_id=station_id, line_id=line_id).first()
        if not existing_favorite:
            # Add to favorites
            favorite = Favorite(user_id=current_user.id, station_id=station_id, line_id=line_id)
            db.session.add(favorite)
            db.session.commit()
            return jsonify({'message': 'Added to favorites'})
    else:
        # Remove from favorites
        favorite = Favorite.query.filter_by(user_id=current_user.id, station_id=station_id, line_id=line_id).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            return jsonify({'message': 'Removed from favorites'})

    return jsonify({'message': 'Operation completed'})


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

# Route for the login and logout page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        # Query your database for the user
        user = User.query.filter_by(username=username).first()

        # Check if user exists and the password is correct
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash('Login successful!')
            return redirect(url_for('profile'))  # Redirect to profile upon successful login
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])  # Allow only POST requests
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))


# Route for the profile page
@app.route('/profile')
@login_required  # This decorator ensures only logged in users can access this route
def profile():
    return render_template('profile.html', user=current_user)


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

@app.route('/api/favorites')
@login_required
def get_favorites():
    # Join the Favorite and Station tables and select required fields.
    # Note: Here, we ensure to include Favorite.line_id directly.
    favorites = db.session.query(
        Favorite.id,
        Station.name,
        Favorite.line_id  # Accessing line_id from Favorite directly
    ).join(Station, Favorite.station_id == Station.id)\
     .filter(Favorite.user_id == current_user.id)\
     .all()

    # Prepare a list of dictionaries for JSON response.
    favorites_list = [{'id': fav.id, 'name': fav.name, 'line_id': fav.line_id} for fav in favorites]
    return jsonify(favorites_list)



def load_stations():
    # Define base IDs and files
    base_ids = {'red': 100, 'blue': 200, 'green': 300, 'orange': 400}
    files = {
        'red': 'Station.txt',
        'blue': 'StationB.txt',
        'orange': 'StationO.txt',
        'green': 'StationGB.txt'  # Example for a single Green branch
    }

    for line, start_id in base_ids.items():
        path = files[line]
        try:
            with open(path, 'rt') as file:
                stations = file.read().split()
            current_id = start_id
            for station in stations:
                if not Station.query.filter_by(name=station).first():  # Avoid duplicate entries
                    new_station = Station(id=current_id, name=station)
                    db.session.add(new_station)
                    current_id += 1
            db.session.commit()
            print(f'Successfully loaded stations for {line} line.')
        except Exception as e:
            print(f"Failed to load stations for {line} line: {e}")

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
