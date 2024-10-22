from flask import Flask, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_restful import Api, Resource
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Note, Contact
from spellchecker import SpellChecker
from flask_migrate import Migrate
import logging
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.secret_key = 'my_secret_key'
CORS(app, supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://group_five:12345@localhost/note_taking'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db.init_app(app)
spell = SpellChecker()
api = Api(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()

# Helper function for spell checking
def check_spelling(text):
    misspelled = spell.unknown(text.split())
    # Convert sets to lists for JSON serialization
    return {word: list(spell.candidates(word)) for word in misspelled}
class UserResource(Resource):
    def post(self):
        data = request.get_json()
        new_user = User(email=data['email'], password=generate_password_hash(data['password']))
        db.session.add(new_user)

        try:
            db.session.commit()
            logging.info(f"User created: {new_user.email}")
            return {'message': 'User created successfully!'}, 201
        except IntegrityError:
            db.session.rollback()  # Rollback the session on error
            logging.warning(f"Email already exists: {new_user.email}")
            return {"error": "Email already exists"}, 400
        except Exception as e:
            db.session.rollback()  # Rollback in case of other errors
            logging.error(f"Error creating user: {e}", exc_info=True)
            return {'message': 'Internal Server Error'}, 500

class LoginResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data or 'email' not in data or 'password' not in data:
                logging.warning("Missing email or password in login request.")
                return {'message': 'Email and password are required!'}, 400
            
            user = User.query.filter_by(email=data['email']).first()
            if user and check_password_hash(user.password, data['password']):
                session['user_id'] = user.id
                logging.info(f"User logged in: {user.email}")
                return {'message': 'Login successful!'}, 200
            
            logging.warning("Invalid email or password attempt.")
            return {'message': 'Invalid email or password!'}, 401
        except Exception as e:
            logging.error(f"Error during login: {e}", exc_info=True)
            return {'message': 'Internal Server Error'}, 500

class LogoutResource(Resource):
    def post(self):
        session.pop('user_id', None)
        logging.info("User logged out.")
        return {'message': 'Logout successful!'}, 200

class NoteResource(Resource):
    def get(self):
        if 'user_id' not in session:
            logging.warning("Unauthorized access attempt to notes.")
            return {'message': 'Unauthorized'}, 401

        notes = Note.query.filter_by(user_id=session['user_id']).all()
        notes_data = [{
            'id': note.id,
            'title': note.title,
            'content': note.content,
            'tags': note.tags.split(',') if note.tags else []  # Ensure tags are a list
        } for note in notes]

        logging.info(f"User {session['user_id']} accessed their notes.")
        return notes_data, 200

    def post(self):
        if 'user_id' not in session:
            logging.warning("Unauthorized access attempt to create note.")
            return {'message': 'Unauthorized'}, 401
        
        data = request.get_json()
        if not data or 'title' not in data or 'content' not in data:
            logging.warning("Title or content missing in request data for note creation.")
            return {'message': 'Title and content are required'}, 400

        tags = data.get('tags', [])
        if not isinstance(tags, list):
            logging.warning("Tags should be a list.")
            return {'message': 'Tags should be a list.'}, 400

        spelling_errors = check_spelling(data['content'])
        if spelling_errors:
            logging.info(f"Spelling mistakes found: {spelling_errors}")
            return {'message': 'Spelling mistakes found. Try again.', 'errors': spelling_errors}, 400

        try:
            new_note = Note(
                title=data['title'],
                content=data['content'],
                tags=','.join(tag.strip() for tag in tags),  # Join list into string for storage
                user_id=session['user_id']
            )
            db.session.add(new_note)
            db.session.commit()
            logging.info(f"Note created successfully: {new_note.id}")
            return {'message': 'Note created successfully!', 'note': {'id': new_note.id, 'title': new_note.title}}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating note: {e}", exc_info=True)
            return {'message': 'Internal Server Error'}, 500
class ContactResource(Resource):
    def post(self):
        data = request.get_json()
        new_contact = Contact(
            name=data['name'],
            email=data['email'],
            subject=data.get('subject', ''),
            message=data['message']
        )
        db.session.add(new_contact)
        db.session.commit()
        logging.info(f"Contact message sent: {new_contact.name} ({new_contact.email})")
        return {'message': 'Contact message sent successfully!'}, 201   

    def get(self):
        contacts = Contact.query.all()
        contacts_data = [{
            'id': contact.id,
            'name': contact.name,
            'email': contact.email,
            'subject': contact.subject,
            'message': contact.message
        } for contact in contacts]
        return contacts_data, 200

# Registering API Resources
api.add_resource(UserResource, '/signup')
api.add_resource(LoginResource, '/login')
api.add_resource(LogoutResource, '/logout')
api.add_resource(NoteResource, '/notes', '/notes/<int:note_id>')
api.add_resource(ContactResource, '/contact')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5000, debug=True)