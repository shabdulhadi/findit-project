import os
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, LostItem, FoundItem 

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///findit.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_super_secret_key_here'

# Photo uploads folder setup
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

# ==========================================
#        FRONTEND PAGE ROUTES (GET)
# ==========================================
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/login')
@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/signup')
@app.route('/signup.html')
def signup_page():
    return render_template('signup.html')

@app.route('/report-lost')
@app.route('/report-lost.html')
def report_lost_page():
    return render_template('report-lost.html')

@app.route('/report-found')
@app.route('/report-found.html')
def report_found_page():
    return render_template('report-found.html')

# Route to serve uploaded photos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ==========================================
#        BACKEND API ROUTES
# ==========================================
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json() if request.is_json else request.form
    
    if not data:
        return jsonify({"error": "No data provided"}), 400

    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if confirm_password and password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400
    
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"error": "Email already registered"}), 400

    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        university_id=data.get('university_id'),
        campus=data.get('campus'),
        password_hash=hashed_pw
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        if not request.is_json:
            return redirect('/login')
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to register user", "details": str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() if request.is_json else request.form
    
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user = User.query.filter_by(email=data.get('email')).first()

    if user and check_password_hash(user.password_hash, data.get('password')):
        session['user_id'] = user.id
        session['user_name'] = user.name
        if not request.is_json:
            return redirect('/')
        return jsonify({"message": "Login successful", "user_id": user.id}), 200
    
    if not request.is_json:
        return render_template('login.html', error="Invalid email or password")
    return jsonify({"error": "Invalid email or password"}), 401


@app.route('/api/report-lost', methods=['POST'])
def report_lost():
    user_id = session.get('user_id')
    if not user_id:
        if not request.is_json:
            return redirect('/login')
        return jsonify({"error": "Unauthorized. Please log in to report an item."}), 401

    title = request.form.get('title')
    category = request.form.get('category')
    campus = request.form.get('campus')
    date_lost_str = request.form.get('date_lost')
    location = request.form.get('location')
    description = request.form.get('description')

    try:
        date_lost = datetime.strptime(date_lost_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format."}), 400

    photo_url = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            unique_name = f"lost_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            photo_url = f"/uploads/{unique_name}"

    new_lost_item = LostItem(
        user_id=user_id,
        title=title,
        category=category,
        campus=campus,
        location=location,
        date_lost=date_lost,
        description=description,
        photo_url=photo_url
    )

    try:
        db.session.add(new_lost_item)
        db.session.commit()
        if not request.is_json:
            return redirect('/')
        return jsonify({"message": "Lost item reported successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report", "details": str(e)}), 500


@app.route('/api/report-found', methods=['POST'])
def report_found():
    user_id = session.get('user_id')
    if not user_id:
        if not request.is_json:
            return redirect('/login')
        return jsonify({"error": "Unauthorized. Please log in to report an item."}), 401

    title = request.form.get('title')
    category = request.form.get('category')
    campus = request.form.get('campus')
    date_found_str = request.form.get('date_found')
    location = request.form.get('location')
    description = request.form.get('description')

    try:
        date_found = datetime.strptime(date_found_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format."}), 400

    if 'photo' not in request.files or request.files['photo'].filename == '':
        return jsonify({"error": "A photo is required for found items."}), 400

    file = request.files['photo']
    filename = secure_filename(file.filename)
    unique_name = f"found_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    photo_url = f"/uploads/{unique_name}"

    new_found_item = FoundItem(
        user_id=user_id,
        title=title,
        category=category,
        campus=campus,
        location=location,
        date_found=date_found,
        description=description,
        photo_url=photo_url
    )

    try:
        db.session.add(new_found_item)
        db.session.commit()
        if not request.is_json:
            return redirect('/')
        return jsonify({"message": "Found item reported successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report", "details": str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


@app.route('/api/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    user = User.query.get(user_id)
    return jsonify({
        "name": user.name,
        "email": user.email,
        "campus": user.campus
    }), 200


if __name__ == '__main__':
    app.run(debug=True)