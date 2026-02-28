from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'foodbridge-secret-key-change-in-production'

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'foodbridge.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with open(os.path.join(os.path.dirname(__file__), 'database', 'db.sql'), 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# ---- HOME ----
@app.route('/')
def home():
    return render_template('home.html')

# ---- LOGIN ----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email=? AND password=? AND user_type=?',
            (email, password, user_type)
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            session['name'] = user['name']
            if user['user_type'] == 'hotel':
                return redirect(url_for('hotel_dashboard'))
            else:
                return redirect(url_for('ngo_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

# ---- REGISTER ----
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        phone = request.form.get('phone')
        address = request.form.get('address')

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password, user_type, phone, address) VALUES (?,?,?,?,?,?)',
                (name, email, password, user_type, phone, address)
            )
            conn.commit()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'error')
        finally:
            conn.close()
    return render_template('register.html')

# ---- LOGOUT ----
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ---- HOTEL DASHBOARD ----
@app.route('/hotel')
def hotel_dashboard():
    if session.get('user_type') != 'hotel':
        return redirect(url_for('login'))

    conn = get_db()
    hotel_id = session['user_id']
    listings = conn.execute(
        'SELECT * FROM food_listings WHERE hotel_id=? ORDER BY created_at DESC',
        (hotel_id,)
    ).fetchall()

    # Impact stats
    impact = conn.execute('''
        SELECT 
            SUM(fl.quantity) as meals_shared,
            COUNT(DISTINCT fr.ngo_id) as ngos_helped
        FROM food_requests fr
        JOIN food_listings fl ON fr.food_id = fl.id
        WHERE fl.hotel_id=? AND fr.status='completed'
    ''', (hotel_id,)).fetchone()
    
    impact_data = {
        'meals_shared': impact['meals_shared'] or 0,
        'kg_saved': round((impact['meals_shared'] or 0) * 0.3, 1),
        'ngos_helped': impact['ngos_helped'] or 0,
        'co2_saved': round((impact['meals_shared'] or 0) * 0.5, 1)
    }
    conn.close()
    return render_template('hotel.html', listings=listings, impact=impact_data)

# ---- POST FOOD ----
@app.route('/hotel/post-food', methods=['POST'])
def post_food():
    if session.get('user_type') != 'hotel':
        return redirect(url_for('login'))

    data = request.form
    allergens = ', '.join(data.getlist('allergens'))

    conn = get_db()
    conn.execute('''
        INSERT INTO food_listings 
        (hotel_id, food_name, category, quantity, unit, food_type, prepared_at, best_before,
         pickup_address, instructions, contact_name, contact_phone, allergens)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        session['user_id'],
        data['food_name'], data['category'], data['quantity'], data['unit'],
        data['food_type'], data['prepared_at'], data['best_before'],
        data['pickup_address'], data.get('instructions', ''),
        data.get('contact_name', ''), data.get('contact_phone', ''), allergens
    ))
    conn.commit()
    conn.close()
    flash('🎉 Food listed successfully! NGOs can now see and request it.', 'success')
    return redirect(url_for('hotel_dashboard'))

# ---- NGO DASHBOARD ----
@app.route('/ngo')
def ngo_dashboard():
    if session.get('user_type') != 'ngo':
        return redirect(url_for('login'))

    conn = get_db()
    ngo_id = session['user_id']

    # Available food (not claimed)
    available_food = conn.execute('''
        SELECT fl.*, u.name as hotel_name 
        FROM food_listings fl
        JOIN users u ON fl.hotel_id = u.id
        WHERE fl.is_claimed = 0
        ORDER BY fl.created_at DESC
    ''').fetchall()

    # Enrich with hours_left
    available_list = []
    for item in available_food:
        d = dict(item)
        try:
            best = datetime.strptime(d['best_before'], '%H:%M')
            now = datetime.now()
            best_today = best.replace(year=now.year, month=now.month, day=now.day)
            diff = (best_today - now).total_seconds() / 3600
            d['hours_left'] = max(0, diff)
        except:
            d['hours_left'] = 3
        available_list.append(d)

    # My requests
    my_requests = conn.execute('''
        SELECT fr.*, fl.food_name, fl.quantity, fl.unit, u.name as hotel_name
        FROM food_requests fr
        JOIN food_listings fl ON fr.food_id = fl.id
        JOIN users u ON fl.hotel_id = u.id
        WHERE fr.ngo_id=?
        ORDER BY fr.created_at DESC
    ''', (ngo_id,)).fetchall()

    # Impact
    impact = conn.execute('''
        SELECT 
            SUM(fr.people_count) as people_fed,
            COUNT(*) as pickups,
            COUNT(DISTINCT fl.hotel_id) as hotels_partnered
        FROM food_requests fr
        JOIN food_listings fl ON fr.food_id = fl.id
        WHERE fr.ngo_id=? AND fr.status='completed'
    ''', (ngo_id,)).fetchone()

    impact_data = {
        'people_fed': impact['people_fed'] or 0,
        'pickups': impact['pickups'] or 0,
        'hotels_partnered': impact['hotels_partnered'] or 0,
        'meals_this_month': impact['people_fed'] or 0
    }
    conn.close()
    return render_template('ngo.html', available_food=available_list, my_requests=my_requests, impact=impact_data)

# ---- REQUEST FOOD ----
@app.route('/ngo/request-food', methods=['POST'])
def request_food():
    if session.get('user_type') != 'ngo':
        return redirect(url_for('login'))

    data = request.form
    conn = get_db()
    conn.execute('''
        INSERT INTO food_requests (food_id, ngo_id, people_count, pickup_eta, message, status)
        VALUES (?,?,?,?,?,?)
    ''', (
        data['food_id'], session['user_id'],
        data['people_count'], data['pickup_eta'],
        data.get('message', ''), 'pending'
    ))
    # Mark listing as claimed
    conn.execute('UPDATE food_listings SET is_claimed=1, ngo_id=? WHERE id=?',
                 (session['user_id'], data['food_id']))
    conn.commit()
    conn.close()
    flash('💛 Request sent! The hotel will confirm shortly.', 'success')
    return redirect(url_for('ngo_dashboard'))

if __name__ == '__main__':
    if not os.path.exists('database'):
        os.makedirs('database')
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True)