from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    university_id = db.Column(db.String(50), nullable=False)
    campus = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships to access a user's items easily
    lost_items = db.relationship('LostItem', backref='user', lazy=True)
    found_items = db.relationship('FoundItem', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

class LostItem(db.Model):
    __tablename__ = 'lostitems'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    campus = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    date_lost = db.Column(db.Date, nullable=False)
    photo_url = db.Column(db.String(255))
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Adding the constraint to restrict categories
    __table_args__ = (
        db.CheckConstraint("category IN ('Bag / Backpack','Electronics','ID / Cards','Keys','Water Bottle','Clothing','Other')", name='chk_lost_category'),
    )

class FoundItem(db.Model):
    __tablename__ = 'founditems'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    campus = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    date_found = db.Column(db.Date, nullable=False)
    photo_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("category IN ('Bag / Backpack','Electronics','ID / Cards','Keys','Water Bottle','Clothing','Other')", name='chk_found_category'),
    )

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('lostitems.id'))
    found_item_id = db.Column(db.Integer, db.ForeignKey('founditems.id'))
    match_score = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
    type = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)