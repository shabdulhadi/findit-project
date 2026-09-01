from difflib import SequenceMatcher
from models import db, Match, Notification, FoundItem, LostItem, User
from flask_mail import Message

def get_similarity(a, b):
    if not a or not b: return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_matches(new_item, is_lost, mail):
    # Query the opposite table for open items in the same campus and category
    if is_lost:
        candidates = FoundItem.query.filter_by(campus=new_item.campus, category=new_item.category, status='open').all()
    else:
        candidates = LostItem.query.filter_by(campus=new_item.campus, category=new_item.category, status='open').all()

    for candidate in candidates:
        title_score = get_similarity(new_item.title, candidate.title)
        desc_score = get_similarity(new_item.description, candidate.description)
        
        # Weighted base score (title matters more)
        match_score = (title_score * 0.6) + (desc_score * 0.4)

        # Date proximity bonus (within 3 days)
        date_diff = abs((new_item.date_lost - candidate.date_found).days) if is_lost else abs((new_item.date_found - candidate.date_lost).days)
        if date_diff <= 3:
            match_score += 0.1

        if match_score >= 0.4:
            lost_id = new_item.id if is_lost else candidate.id
            found_id = candidate.id if is_lost else new_item.id

            # Create Match
            new_match = Match(lost_item_id=lost_id, found_item_id=found_id, match_score=match_score)
            db.session.add(new_match)
            db.session.flush() # Flush to generate new_match.id before commit

            # Create Notifications
            notif1 = Notification(user_id=new_item.user_id, match_id=new_match.id, type='match_found')
            notif2 = Notification(user_id=candidate.user_id, match_id=new_match.id, type='match_found')
            db.session.add_all([notif1, notif2])

            # Fetch users and send emails
            user1 = User.query.get(new_item.user_id)
            user2 = User.query.get(candidate.user_id)
            send_match_email(user1.email, new_item.title, mail)
            send_match_email(user2.email, candidate.title, mail)

    db.session.commit()

def send_match_email(to_email, item_title, mail):
    msg = Message("FindIt: Possible Match Found!", sender="your_email@gmail.com", recipients=[to_email])
    msg.body = f"Good news — we found a possible match for '{item_title}'. Log in to FindIt to see the details."
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Email failed to send: {e}")