import os
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_mail import Mail
from models import db, User, LostItem, FoundItem, Match, Notification
from matching import find_matches

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///findit.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_dev_key')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail = Mail(app)

base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
with app.app_context():
    db.create_all()

# ==========================================
#        ERROR HANDLERS
# ==========================================
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({"error": "Internal server error. Please try again."}), 500

# ==========================================
#        FRONTEND PAGE ROUTES
# ==========================================
@app.route('/')
@app.route('/index.html')
def index(): return render_template('index.html')

@app.route('/login.html')
def login_page(): return render_template('login.html')

@app.route('/signup.html')
def signup_page(): return render_template('signup.html')

@app.route('/report-lost.html')
def report_lost_page(): return render_template('report-lost.html')

@app.route('/report-found.html')
def report_found_page(): return render_template('report-found.html')

@app.route('/browse')
def browse_page(): return render_template('browse.html')

@app.route('/notifications')
def notifications_page(): return render_template('notifications.html')

@app.route('/my-reports')
def my_reports_page(): return render_template('my-reports.html')

@app.route('/about')
def about_page(): return render_template('about.html')

# ==========================================
#        BACKEND API ROUTES
# ==========================================
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if not email or not name or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400
        
    if password != data.get('confirm_password'):
        return jsonify({"error": "Passwords do not match."}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 400

    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

    new_user = User(
        name=name,
        email=email,
        phone=data.get('phone', '').strip(),
        university_id=data.get('university_id', '').strip(),
        campus=data.get('campus', '').strip(),
        password_hash=hashed_pw
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Registration failed."}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, data.get('password', '')):
        session['user_id'] = user.id
        return jsonify({"message": "Login successful"}), 200
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out"}), 200

@app.route('/api/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = User.query.get(user_id)
    return jsonify({"name": user.name, "email": user.email, "campus": user.campus}), 200

@app.route('/api/report-lost', methods=['POST'])
def report_lost():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    title = request.form.get('title', '').strip()
    category = request.form.get('category', '').strip()
    campus = request.form.get('campus', '').strip()
    
    if not title or not category or not campus:
        return jsonify({"error": "Title, category, and campus are required."}), 400

    try:
        date_lost = datetime.strptime(request.form.get('date_lost', ''), '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format."}), 400

    photo_url = None
    if 'photo' in request.files and request.files['photo'].filename:
        file = request.files['photo']
        filename = secure_filename(file.filename)
        unique_name = f"lost_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
        photo_url = f"/uploads/{unique_name}"

    new_lost = LostItem(user_id=user_id, title=title, category=category, campus=campus,
                        location=request.form.get('location', '').strip(), 
                        date_lost=date_lost, 
                        description=request.form.get('description', '').strip(), 
                        photo_url=photo_url)
    try:
        db.session.add(new_lost)
        db.session.commit()
        find_matches(new_lost, is_lost=True, mail=mail)
        return jsonify({"message": "Lost item reported!"}), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report."}), 500

@app.route('/api/report-found', methods=['POST'])
def report_found():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    title = request.form.get('title', '').strip()
    category = request.form.get('category', '').strip()
    campus = request.form.get('campus', '').strip()

    if not title or not category or not campus:
        return jsonify({"error": "Title, category, and campus are required."}), 400

    try:
        date_found = datetime.strptime(request.form.get('date_found', ''), '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format."}), 400

    if 'photo' not in request.files or not request.files['photo'].filename:
        return jsonify({"error": "A photo is required for found items."}), 400

    file = request.files['photo']
    filename = secure_filename(file.filename)
    unique_name = f"found_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    photo_url = f"/uploads/{unique_name}"

    new_found = FoundItem(user_id=user_id, title=title, category=category, campus=campus,
                          location=request.form.get('location', '').strip(), 
                          date_found=date_found, 
                          description=request.form.get('description', '').strip(), 
                          photo_url=photo_url)
    try:
        db.session.add(new_found)
        db.session.commit()
        find_matches(new_found, is_lost=False, mail=mail)
        return jsonify({"message": "Found item reported!"}), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report."}), 500

@app.route('/api/items', methods=['GET'])
def get_items():
    campus = request.args.get('campus', '').strip()
    category = request.args.get('category', '').strip()

    lost_query = LostItem.query.filter_by(status='open')
    found_query = FoundItem.query.filter_by(status='open')

    if campus:
        lost_query = lost_query.filter_by(campus=campus)
        found_query = found_query.filter_by(campus=campus)
    if category:
        lost_query = lost_query.filter_by(category=category)
        found_query = found_query.filter_by(category=category)

    results = [{"id": i.id, "type": "lost", "title": i.title, "campus": i.campus, "category": i.category, "date": i.date_lost.strftime("%Y-%m-%d"), "photo_url": i.photo_url} for i in lost_query.all()]
    results += [{"id": i.id, "type": "found", "title": i.title, "campus": i.campus, "category": i.category, "date": i.date_found.strftime("%Y-%m-%d"), "photo_url": i.photo_url} for i in found_query.all()]
    
    return jsonify(results), 200

@app.route('/api/my-items', methods=['GET'])
def my_items():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    lost = LostItem.query.filter_by(user_id=user_id).order_by(LostItem.created_at.desc()).all()
    found = FoundItem.query.filter_by(user_id=user_id).order_by(FoundItem.created_at.desc()).all()

    results = [{"id": i.id, "type": "lost", "title": i.title, "status": i.status, "date": i.date_lost.strftime("%Y-%m-%d"), "photo_url": i.photo_url} for i in lost]
    results += [{"id": i.id, "type": "found", "title": i.title, "status": i.status, "date": i.date_found.strftime("%Y-%m-%d"), "photo_url": i.photo_url} for i in found]

    return jsonify(results), 200

@app.route('/api/my-notifications', methods=['GET'])
def my_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    notifs = Notification.query.filter_by(user_id=user_id).order_by(Notification.sent_at.desc()).all()
    result = [{"id": n.id, "type": n.type, "is_read": n.is_read, "sent_at": n.sent_at.strftime("%Y-%m-%d %H:%M:%S")[:10], "match_id": n.match_id} for n in notifs]
    
    for n in notifs: n.is_read = True
    db.session.commit()
    
    return jsonify(result), 200

@app.route('/api/matches/<int:match_id>/confirm', methods=['POST'])
def confirm_match(match_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"error": "Unauthorized"}), 401

    match = Match.query.get(match_id)
    if not match: return jsonify({"error": "Match not found"}), 404

    lost_item = LostItem.query.get(match.lost_item_id)
    found_item = FoundItem.query.get(match.found_item_id)

    if lost_item.user_id != user_id and found_item.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    match.status = 'confirmed'
    lost_item.status = 'matched'
    found_item.status = 'matched'
    db.session.commit()
    return jsonify({"message": "Match confirmed"}), 200

@app.route('/api/matches/<int:match_id>/reject', methods=['POST'])
def reject_match(match_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"error": "Unauthorized"}), 401

    match = Match.query.get(match_id)
    if not match: return jsonify({"error": "Match not found"}), 404

    lost_item = LostItem.query.get(match.lost_item_id)
    found_item = FoundItem.query.get(match.found_item_id)

    if lost_item.user_id != user_id and found_item.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    match.status = 'rejected'
    db.session.commit()
    return jsonify({"message": "Match rejected"}), 200

if __name__ == '__main__':
    app.run(debug=True)