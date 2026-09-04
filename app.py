import os
import difflib
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from models import db, User, LostItem, FoundItem, Match, Notification
from flask_mail import Mail
from matching import find_matches
from models import Match

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///findit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_super_secret_key_here'


# Mail Configuration (Use your Gmail App Password here)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'muhammadhanzla7182@gmail.com'
app.config['MAIL_PASSWORD'] = 'utfk hhuk sefl cbes'
mail = Mail(app)

# --- Email configuration (Flask-Mail) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ah5672758@gmail.com'
app.config['MAIL_PASSWORD'] = 'sehw ueal fplx hkfy'
app.config['MAIL_DEFAULT_SENDER'] = 'ah5672758@gmail.com'

mail = Mail(app)

# Photo uploads folder setup
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

MATCH_THRESHOLD = 0.4


# ==========================================
#        MATCHING + EMAIL HELPERS
# ==========================================
def calculate_match_score(item_a, item_b):
    """Compares two items (one LostItem, one FoundItem) and returns a 0-1 score."""
    text_a = f"{item_a.title} {item_a.description or ''}".lower()
    text_b = f"{item_b.title} {item_b.description or ''}".lower()
    text_score = difflib.SequenceMatcher(None, text_a, text_b).ratio()

    date_a = getattr(item_a, 'date_lost', None) or getattr(item_a, 'date_found', None)
    date_b = getattr(item_b, 'date_lost', None) or getattr(item_b, 'date_found', None)

    date_bonus = 0
    if date_a and date_b:
        days_apart = abs((date_a - date_b).days)
        if days_apart <= 3:
            date_bonus = 0.15
        elif days_apart <= 7:
            date_bonus = 0.05

    return min(text_score + date_bonus, 1.0)


def send_match_email(to_email, item_title):
    """Sends the match notification email."""
    try:
        msg = Message(
            subject="FindIt — Possible match found!",
            recipients=[to_email],
            body=(
                f"Good news — we found a possible match for '{item_title}'.\n\n"
                "Log in to FindIt and check your Notifications page to see the details."
            )
        )
        mail.send(msg)
    except Exception as e:
        print(f"[email] Failed to send match email to {to_email}: {e}")


def find_and_create_matches(new_item, is_lost):
    """
    Looks for candidate matches on the opposite side (lost vs found),
    filtered to the same campus + category. Creates a Match + two
    Notifications (and sends two emails) for every candidate that
    scores above MATCH_THRESHOLD.
    """
    if is_lost:
        candidates = FoundItem.query.filter_by(
            campus=new_item.campus, category=new_item.category, status='open'
        ).all()
    else:
        candidates = LostItem.query.filter_by(
            campus=new_item.campus, category=new_item.category, status='open'
        ).all()

    for candidate in candidates:
        score = calculate_match_score(new_item, candidate)
        if score < MATCH_THRESHOLD:
            continue

        lost_id = new_item.id if is_lost else candidate.id
        found_id = candidate.id if is_lost else new_item.id

        already_exists = Match.query.filter_by(
            lost_item_id=lost_id, found_item_id=found_id
        ).first()
        if already_exists:
            continue

        new_match = Match(
            lost_item_id=lost_id,
            found_item_id=found_id,
            match_score=score,
            status='pending'
        )
        db.session.add(new_match)
        db.session.flush()

        lost_item = LostItem.query.get(lost_id)
        found_item = FoundItem.query.get(found_id)

        db.session.add(Notification(user_id=lost_item.user_id, match_id=new_match.id, type='match_found'))
        db.session.add(Notification(user_id=found_item.user_id, match_id=new_match.id, type='match_found'))
        db.session.commit()

        send_match_email(lost_item.user.email, lost_item.title)
        send_match_email(found_item.user.email, found_item.title)


# ==========================================
#        FRONTEND PAGE ROUTES (GET)
# ==========================================
@app.route('/')
@app.route('/index.html')
def index():
    lost_items = LostItem.query.order_by(LostItem.created_at.desc()).limit(4).all()
    found_items = FoundItem.query.order_by(FoundItem.created_at.desc()).limit(4).all()
    return render_template('index.html', lost_items=lost_items, found_items=found_items)

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

@app.route('/browse')
def browse_page():
    return render_template('browse.html')

@app.route('/notifications')
def notifications_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('notifications.html')

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

    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # .edu / .edu.pk domain restriction
    if not (email.endswith('.edu') or email.endswith('.edu.pk') or '.edu.' in email):
        error_msg = "Registration failed: Only official university email addresses (.edu / .edu.pk) are allowed."
        if not request.is_json:
            return render_template('signup.html', error=error_msg)
        return jsonify({"error": error_msg}), 400

    if confirm_password and password != confirm_password:
        error_msg = "Passwords do not match"
        if not request.is_json:
            return render_template('signup.html', error=error_msg)
        return jsonify({"error": error_msg}), 400

    if User.query.filter_by(email=email).first():
        error_msg = "Email already registered"
        if not request.is_json:
            return render_template('signup.html', error=error_msg)
        return jsonify({"error": error_msg}), 400

    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

    new_user = User(
        name=data.get('name'),
        email=email,
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
        error_msg = f"Failed to register user: {str(e)}"
        if not request.is_json:
            return render_template('signup.html', error=error_msg)
        return jsonify({"error": "Failed to register user", "details": str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() if request.is_json else request.form

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = (data.get('email') or '').strip().lower()
    user = User.query.filter_by(email=email).first()

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
        if file.filename != '':
            filename = secure_filename(file.filename)
            unique_name = f"lost_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            photo_url = f"/uploads/{unique_name}"

    new_lost_item = LostItem(
        user_id=user_id, title=title, category=category, campus=campus,
        location=location, date_lost=date_lost, description=description, photo_url=photo_url
    )

    try:
        db.session.add(new_lost_item)
        db.session.commit()

        find_and_create_matches(new_lost_item, is_lost=True)

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
        user_id=user_id, title=title, category=category, campus=campus,
        location=location, date_found=date_found, description=description, photo_url=photo_url
    )

    try:
        db.session.add(new_found_item)
        db.session.commit()

        find_and_create_matches(new_found_item, is_lost=False)

        if not request.is_json:
            return redirect('/')
        return jsonify({"message": "Found item reported successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report", "details": str(e)}), 500




@app.route('/api/items', methods=['GET'])
def get_items():
    item_type = request.args.get('type')
    campus = request.args.get('campus')
    category = request.args.get('category')

    results = []

    if item_type != 'found':
        query = LostItem.query.filter_by(status='open')
        if campus:
            query = query.filter_by(campus=campus)
        if category:
            query = query.filter_by(category=category)
        for item in query.order_by(LostItem.created_at.desc()).all():
            results.append({
                "id": item.id,
                "type": "lost",
                "title": item.title,
                "category": item.category,
                "campus": item.campus,
                "location": item.location,
                "photo_url": item.photo_url,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })

    if item_type != 'lost':
        query = FoundItem.query.filter_by(status='open')
        if campus:
            query = query.filter_by(campus=campus)
        if category:
            query = query.filter_by(category=category)
        for item in query.order_by(FoundItem.created_at.desc()).all():
            results.append({
                "id": item.id,
                "type": "found",
                "title": item.title,
                "category": item.category,
                "campus": item.campus,
                "location": item.location,
                "photo_url": item.photo_url,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })

    results.sort(key=lambda x: x['created_at'] or '', reverse=True)
    return jsonify(results), 200


@app.route('/api/my-notifications', methods=['GET'])
def my_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    notifs = Notification.query.filter_by(user_id=user_id).order_by(Notification.sent_at.desc()).all()
    
    result = []
    for n in notifs:
        # Save original state for frontend, include match_id
        result.append({
            "id": n.id, 
            "type": n.type, 
            "is_read": n.is_read, 
            "sent_at": n.sent_at.strftime("%Y-%m-%d %H:%M:%S")[:10],
            "match_id": n.match_id
        })
        # Mark as read in the database silently
        n.is_read = True

    db.session.commit()
    return jsonify(result), 200


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

@app.route('/api/matches/<int:match_id>/confirm', methods=['POST'])
def confirm_match(match_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404

    lost_item = LostItem.query.get(match.lost_item_id)
    found_item = FoundItem.query.get(match.found_item_id)

    # Security: Ensure logged-in user owns either the lost or found item
    if lost_item.user_id != user_id and found_item.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    # Update statuses
    match.status = 'confirmed'
    lost_item.status = 'matched'
    found_item.status = 'matched'
    
    db.session.commit()
    return jsonify({"message": "Match confirmed successfully"}), 200

@app.route('/api/matches/<int:match_id>/reject', methods=['POST'])
def reject_match(match_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404

    lost_item = LostItem.query.get(match.lost_item_id)
    found_item = FoundItem.query.get(match.found_item_id)

    if lost_item.user_id != user_id and found_item.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    # Only update the match status, leave items open
    match.status = 'rejected'
    db.session.commit()
    return jsonify({"message": "Match rejected"}), 200
    app.run(debug=True)

@app.route('/api/my-items', methods=['GET'])
def my_items():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    lost = LostItem.query.filter_by(user_id=user_id).order_by(LostItem.created_at.desc()).all()
    found = FoundItem.query.filter_by(user_id=user_id).order_by(FoundItem.created_at.desc()).all()

    results = []
    for item in lost:
        results.append({"id": item.id, "type": "lost", "title": item.title, "status": item.status, "date": item.date_lost.strftime("%Y-%m-%d"), "photo_url": item.photo_url})
    for item in found:
        results.append({"id": item.id, "type": "found", "title": item.title, "status": item.status, "date": item.date_found.strftime("%Y-%m-%d"), "photo_url": item.photo_url})

    return jsonify(results), 200

if __name__ == '__main__':
    
    app.run(debug=True)