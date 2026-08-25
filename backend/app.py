from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from backend.models import db, User

app = Flask(__name__)

# Replace with your actual PostgreSQL URI, or use SQLite for testing
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///findit.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_super_secret_key_here' # Needed for sessions

db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# --- SIGNUP ENDPOINT ---
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    # Check if user already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"error": "Email already registered"}), 400

    # Hash the password
    hashed_pw = generate_password_hash(data.get('password'), method='pbkdf2:sha256')

    # Create new user
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
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to register user", "details": str(e)}), 500

# --- LOGIN ENDPOINT ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = User.query.filter_by(email=data.get('email')).first()

    # Check user exists and password is correct
    if user and check_password_hash(user.password_hash, data.get('password')):
        # Create session
        session['user_id'] = user.id
        return jsonify({"message": "Login successful", "user_id": user.id}), 200
    
    return jsonify({"error": "Invalid email or password"}), 401

# --- LOGOUT ENDPOINT ---
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out successfully"}), 200

# --- TEST ENDPOINT ---
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