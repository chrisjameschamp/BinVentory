from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

import os
import hashlib
import secrets
import sqlite3

# Load environment variables from .env file
load_dotenv()

# Function to create a new .env file with a generated secret key
def create_env_file():
    secret_key = secrets.token_hex(16)
    with open('.env', 'w') as f:
        f.write(f'SECRET_KEY={secret_key}\n')
    print(f"Generated new SECRET_KEY and saved to .env file: {secret_key}")
    return secret_key

# Retrieve the SECRET_KEY from environment, or create a new one if not found
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = create_env_file()

# Create the Flask app
app = Flask(__name__)
app.secret_key = secret_key  # Set the secret key for the Flask app
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=14)  # Change this to any duration you like

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not logged in

# Inactivity timeout (in seconds)
INACTIVITY_TIMEOUT = 30 * 60  # 30 minutes

# Function to connect to the SQLite database
def connect_db():
    return sqlite3.connect('inventory.db')

# Password Hashing Function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User Model for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@app.before_request
def track_user_activity():
    # Skip activity tracking for static files, login, and PIN entry page
    if request.endpoint in ['login', 'pin_entry', 'static']:
        return None

    now = datetime.now(timezone.utc)  # Timezone-aware datetime object
    if 'last_activity' in session:
        last_activity = session['last_activity']
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)

        # Check if the inactivity timeout has been exceeded
        if (now - last_activity).total_seconds() > INACTIVITY_TIMEOUT:
            session.pop('pin_authenticated', None)  # Reset the PIN authentication
            session['next'] = request.url  # Store the original URL
            return redirect(url_for('pin_entry'))  # Redirect to PIN page

    session['last_activity'] = now.isoformat()  # Update last activity timestamp

# Load User for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return User(id=user[0], username=user[1])
    return None

# Function to create the default admin user if it doesn't exist
def create_default_admin_user():
    conn = connect_db()
    cursor = conn.cursor()

    # Check if an admin user already exists
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    admin_user = cursor.fetchone()

    if not admin_user:
        # Create a default admin user
        default_username = 'admin'
        default_password = generate_password_hash('password')  # Use Flask's generate_password_hash
        default_pin = generate_password_hash('1234')  # Use Flask's generate_password_hash for the pin
        cursor.execute('INSERT INTO users (username, password, pin) VALUES (?, ?, ?)', 
                       (default_username, default_password, default_pin))
        conn.commit()
        print("Default admin user created with username 'admin' and password 'password'")

    conn.close()

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form  # Check if "Remember Me" is checked

        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            user_obj = User(id=user[0], username=user[1])
            login_user(user_obj, remember=remember)

            session['last_activity'] = datetime.utcnow()  # Track user activity
            session['pin_authenticated'] = True  # PIN authentication for the current session

            return redirect(url_for('homepage'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

# Route for logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/pin_entry', methods=['GET', 'POST'])
@login_required
def pin_entry():
    if request.method == 'POST':
        entered_pin = request.form['pin']

        # Connect to the database and fetch the stored hashed PIN
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT pin FROM users WHERE username = ?', (current_user.username,))
        stored_pin = cursor.fetchone()[0]
        conn.close()

        # Compare the entered PIN with the stored hash using werkzeug's check_password_hash
        if check_password_hash(stored_pin, entered_pin):
            session['pin_authenticated'] = True

            session['last_activity'] = datetime.utcnow()

            # Check if there's a 'next' key in the session and redirect there
            next_page = session.pop('next', None)
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('homepage'))  # Fallback to homepage if 'next' is not set
        else:
            flash('Incorrect PIN. Please try again.', 'danger')
            return redirect(url_for('pin_entry'))  # Redirect back to the pin page on failure

    # Store the intended next page in the session if it isn't already set
    if 'next' not in session:
        session['next'] = request.args.get('next') or request.referrer or url_for('homepage')

    return render_template('pin_entry.html')

@app.route('/account_settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    if request.method == 'POST':
        username = request.form['username']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        new_pin = request.form['pin']

        # Connect to the database
        conn = connect_db()
        cursor = conn.cursor()

        # Fetch current user's hashed password from the database
        cursor.execute('SELECT password FROM users WHERE username = ?', (current_user.username,))
        user_info = cursor.fetchone()

        # Check if the provided password matches the hash in the database
        if not check_password_hash(user_info[0], current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('account_settings'))

        # Validate the new password and confirm password match
        if new_password and new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('account_settings'))

        # Update username, password, and PIN if applicable
        if username and username != current_user.username:
            cursor.execute('UPDATE users SET username = ? WHERE username = ?', (username, current_user.username))
            current_user.username = username

        if new_password:
            hashed_password = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_password, current_user.username))

        if new_pin:
            hashed_pin = generate_password_hash(new_pin)  # Hash the new PIN as well
            cursor.execute('UPDATE users SET pin = ? WHERE username = ?', (hashed_pin, current_user.username))

        conn.commit()
        conn.close()

        flash('Account settings updated successfully!', 'success')
        return redirect(url_for('account_settings'))

    # Pass the current user's username to the template
    return render_template('account_settings.html', username=current_user.username)

# Homepage: Lists locations and options to add bins or locations
@app.route('/')
@login_required
def homepage():
    conn = connect_db()
    cursor = conn.cursor()
    
    # Fetch all locations
    cursor.execute('SELECT * FROM locations')
    locations = cursor.fetchall()
    
    conn.close()
    return render_template('homepage.html', locations=locations)

# Route to add a new location
@app.route('/add_location', methods=['POST'])
@login_required
def add_location():
    name = request.form['name']
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO locations (name) VALUES (?)', (name,))
    conn.commit()
    conn.close()

    return redirect(url_for('homepage'))

# Route to view all bins in a location
@app.route('/location/<int:location_id>')
@login_required
def view_location(location_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch bins at this location
    cursor.execute('SELECT id, bin_id, name FROM bins WHERE location_id = ?', (location_id,))
    bins = cursor.fetchall()

    # Fetch the location name
    cursor.execute('SELECT name FROM locations WHERE id = ?', (location_id,))
    location_name = cursor.fetchone()[0]

    # Fetch other locations for move functionality
    cursor.execute('SELECT id, name FROM locations WHERE id != ?', (location_id,))
    other_locations = cursor.fetchall()

    # Construct the full URL for the location
    full_location_url = request.url_root + 'location/' + str(location_id)

    return render_template('location.html', 
                           bins=bins, 
                           location_name=location_name, 
                           location_id=location_id, 
                           other_locations=other_locations, 
                           location_url=full_location_url)

# Route to view all bins in a location
@app.route('/qr_scan')
@login_required
def qr_scan():
    host_url = request.host_url  # This gets the current host
    return render_template('qr_scan.html', host_url=host_url)

@app.route('/bin/<int:bin_id>')
@login_required
def bin_page(bin_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch the items in the bin
    cursor.execute('SELECT * FROM items WHERE bin_id = ?', (bin_id,))
    items = cursor.fetchall()

    # Fetch bin details including location_id and location_name
    cursor.execute('SELECT bin_id, name, location_id FROM bins WHERE id = ?', (bin_id,))
    bin_data = cursor.fetchone()

    cursor.execute('SELECT name FROM locations WHERE id = ?', (bin_data[2],))
    location_name = cursor.fetchone()[0]

    # Fetch all other bins for the "Move Item" modal
    cursor.execute('SELECT id, bin_id, name FROM bins WHERE id != ?', (bin_id,))
    other_bins = cursor.fetchall()

    # Generate full URL for the current bin
    bin_url = f"{request.host_url}bin/{bin_id}"

    if bin_data:
        return render_template('bin_page.html', 
                               items=items, 
                               bin_id=bin_data[0], 
                               bin_name=bin_data[1], 
                               location_id=bin_data[2], 
                               location_name=location_name, 
                               other_bins=other_bins, 
                               bin_url=bin_url)  # Pass the URL to the template
    else:
        return "Bin not found", 404

@app.route('/add_bin/<int:location_id>', methods=['POST'])
@login_required
def add_bin(location_id):
    bin_name = request.form['name']
    
    conn = connect_db()
    cursor = conn.cursor()

    # Find the next available 4-digit bin ID, treating bin_id as an integer
    cursor.execute('SELECT COALESCE(MAX(CAST(bin_id AS INTEGER)), 0) + 1 FROM bins')
    next_bin_id = cursor.fetchone()[0]

    # Ensure the new bin ID is formatted as 4 digits
    formatted_bin_id = f'{next_bin_id:04}'  # Format as 4 digits
    
    try:
        # Insert the new bin with a unique bin_id
        cursor.execute('INSERT INTO bins (bin_id, name, location_id, contents) VALUES (?, ?, ?, ?)', (formatted_bin_id, bin_name, location_id, ''))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        flash('Error: Bin ID conflict, please try again.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('view_location', location_id=location_id))

@app.route('/edit_location/<int:location_id>', methods=['POST'])
@login_required
def edit_location(location_id):
    name = request.form['name']
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE locations SET name = ? WHERE id = ?', (name, location_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/delete_location/<int:location_id>')
@login_required
def delete_location(location_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM locations WHERE id = ?', (location_id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/edit_bin/<int:bin_id>', methods=['POST'])
@login_required
def edit_bin(bin_id):
    name = request.form['name']
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bins SET name = ? WHERE id = ?', (name, bin_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/delete_bin/<int:bin_id>')
@login_required
def delete_bin(bin_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bins WHERE id = ?', (bin_id,))
    conn.commit()
    conn.close()
    return redirect('/location/' + str(bin_id))

# Route to add a new item to the bin
@app.route('/add_item/<int:bin_id>', methods=['POST'])
@login_required
def add_item(bin_id):
    name = request.form['name']
    description = request.form.get('description', '')

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO items (bin_id, name, description) VALUES (?, ?, ?)', (bin_id, name, description))
    conn.commit()
    conn.close()

    return redirect(url_for('bin_page', bin_id=bin_id))

@app.route('/edit_item/<int:item_id>', methods=['POST'])
@login_required
def edit_item(item_id):
    name = request.form['name']
    description = request.form.get('description', '')

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE items SET name = ?, description = ? WHERE id = ?', (name, description, item_id))
    conn.commit()
    conn.close()

    # Redirect back to the bin page
    return redirect(request.referrer)

@app.route('/delete_item/<int:item_id>')
@login_required
def delete_item(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    # Redirect back to the bin page
    return redirect(request.referrer)

@app.route('/move_item/<int:item_id>/<int:new_bin_id>')
@login_required
def move_item(item_id, new_bin_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE items SET bin_id = ? WHERE id = ?', (new_bin_id, item_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/move_bin/<int:bin_id>/<int:new_location_id>')
@login_required
def move_bin(bin_id, new_location_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bins SET location_id = ? WHERE id = ?', (new_location_id, bin_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/search')
@login_required
def search():
    query = request.args.get('query')
    if not query:
        flash('Please enter a search query.', 'warning')
        return redirect(url_for('homepage'))

    conn = connect_db()
    cursor = conn.cursor()

    search_query = f"%{query}%"
    
    # Normalize bin number: strip out "Bin " and leading zeros for numeric comparison
    if query.lower().startswith('bin'):
        # If the query starts with 'Bin', extract the number part
        bin_number = query.lower().replace('bin', '').strip()
        try:
            # Try to convert it to an integer and back to handle both "Bin 2" and "Bin 0002"
            bin_number_normalized = f"%{int(bin_number)}%"
        except ValueError:
            # If the bin number is not a valid integer, fallback to normal search query
            bin_number_normalized = search_query
    else:
        bin_number_normalized = search_query

    # Fetch locations
    cursor.execute("""
        SELECT 'location' as type, locations.id, locations.name, NULL, NULL
        FROM locations
        WHERE locations.name LIKE ?
    """, (search_query,))
    locations = cursor.fetchall()

    # Fetch bins: matching either by name, bin_id, or normalized bin number
    cursor.execute("""
        SELECT 'bin' as type, bins.id, bins.name, bins.bin_id, locations.name
        FROM bins
        JOIN locations ON bins.location_id = locations.id
        WHERE bins.name LIKE ? OR bins.bin_id LIKE ? OR bins.bin_id LIKE ?
    """, (search_query, search_query, bin_number_normalized))
    bins = cursor.fetchall()

    # Fetch items and related bins and locations
    cursor.execute("""
        SELECT 'item' as type, items.id, items.name, bins.bin_id, locations.name, items.description
        FROM items
        JOIN bins ON items.bin_id = bins.id
        JOIN locations ON bins.location_id = locations.id
        WHERE items.name LIKE ? OR items.description LIKE ?
    """, (search_query, search_query))
    items = cursor.fetchall()

    # Combine all results
    results = locations + bins + items
    conn.close()

    return render_template('search_results.html', query=query, results=results)

if __name__ == '__main__':
    # Initialize the SQLite database
    conn = connect_db()
    cursor = conn.cursor()

    # Create locations table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    ''')

    # Create bins table with unique bin_id and location reference
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bin_id TEXT UNIQUE,  -- Ensure bin_id is unique across all locations
        name TEXT,
        location_id INTEGER,
        contents TEXT,
        FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
    )
    ''')

    # Create items table for individual bin items
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bin_id INTEGER,
        name TEXT,
        description TEXT,
        FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE CASCADE
    )
    ''')

    # Create users table for users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        pin TEXT NOT NULL
    )
    ''')
    create_default_admin_user()

    conn.commit()
    conn.close()

    # Start the Flask app
    app.run(host='0.0.0.0', port=5000)
