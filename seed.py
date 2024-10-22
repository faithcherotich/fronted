from app import app, db
from models import User, Note

def seed_data():
    # Create dummy users
    user1 = User(email='fay@gmail', password='password123')
    user2 = User(email='jane@gmail', password='password456')
    
    # Create dummy notes
    note1 = Note(title='First Note', content='This is the first note.', user_id=1)
    note2 = Note(title='Second Note', content='This is the second note.', user_id=1)
    note3 = Note(title='Third Note', content='This is the third note.', user_id=2)

    # Add users and notes to the session
    db.session.add(user1)
    db.session.add(user2)
    db.session.add(note1)
    db.session.add(note2)
    db.session.add(note3)

    # Commit the session to save the records in the database
    db.session.commit()
    print("Dummy data added successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        seed_data()