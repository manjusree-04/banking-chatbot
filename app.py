from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from deep_translator import GoogleTranslator
from functools import wraps
import os
import json
import uuid
from user_agents import parse
import logging
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banking_chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    profile = db.relationship('UserProfile', backref='user', uselist=False)
    sessions = db.relationship('UserSession', backref='user', lazy=True)
    chats = db.relationship('Chat', backref='user', lazy=True)

class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))
    device_info = db.Column(db.String(200))
    session_status = db.Column(db.String(20), default='active')

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    address = db.Column(db.String(200))
    date_of_birth = db.Column(db.Date)
    profile_picture = db.Column(db.String(200))

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    message_type = db.Column(db.String(20))
    language = db.Column(db.String(10))

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def translate_text(text, target_lang='en'):
    try:
        if target_lang == 'en':
            return text
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return text

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Chatbot Model
class ChatbotModel:
    def __init__(self):
        try:
            self.label_classes = [
                'FAQ_Account',
                'COMPLAINT_Service',
                'ASSISTANCE_Technical',
                'FRAUD_Unauthorized'
            ]
            logging.info("Chatbot model initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing chatbot model: {e}")
            raise

    def get_response(self, text):
        try:
            text = text.lower()
            if any(word in text for word in ['account', 'balance', 'deposit', 'withdraw']):
                return self.generate_response('FAQ_Account', text)
            elif any(word in text for word in ['complaint', 'issue', 'problem', 'unhappy']):
                return self.generate_response('COMPLAINT_Service', text)
            elif any(word in text for word in ['help', 'support', 'technical', 'login', 'password']):
                return self.generate_response('ASSISTANCE_Technical', text)
            elif any(word in text for word in ['fraud', 'unauthorized', 'suspicious', 'security']):
                return self.generate_response('FRAUD_Unauthorized', text)
            else:
                return "How can I assist you with your banking needs today?"
        except Exception as e:
            logging.error(f"Error in get_response: {e}")
            return "I apologize, but I'm having trouble processing your request. Please try again."

    def generate_response(self, label, query):
        responses = {
            'FAQ_Account': """
                Here's information about your account:
                - We offer various account types including savings, checking, and business accounts
                - Each account has unique features and benefits
                - You can check your balance, transfer funds, and manage payments online
                - We provide 24/7 account access through our mobile app
                Would you like specific information about any particular account type?
            """,
            'COMPLAINT_Service': """
                I apologize for any inconvenience you've experienced. Let me help:
                1. I understand your concern about the service issue
                2. Could you provide more specific details about the problem?
                3. I'll ensure your complaint is addressed promptly
                4. We take all feedback seriously to improve our services
                What additional information can you share about the issue?
            """,
            'ASSISTANCE_Technical': """
                I'll help you with technical support:
                1. First, could you specify what technical issue you're facing?
                2. Have you tried accessing our online banking recently?
                3. I can guide you through common solutions
                4. Our technical team is available for complex issues
                Please provide more details about the technical problem you're experiencing.
            """,
            'FRAUD_Unauthorized': """
                Your security is our top priority. Let's address this immediately:
                1. Don't worry - we'll help secure your account
                2. We'll investigate any unauthorized activity
                3. Your funds are protected against fraud
                4. We'll help you update your security settings
                Could you tell me more about the suspicious activity you've noticed?
            """
        }
        return responses.get(label, "I understand your query. Let me connect you with a representative who can provide more detailed assistance.")

# Initialize chatbot
try:
    chatbot = ChatbotModel()
except Exception as e:
    logging.error(f"Failed to initialize chatbot: {e}")
    chatbot = None

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat_interface'))
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('chat_interface'))
        
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            logging.info(f"Attempting to register user: {username}")

            if not all([username, email, password, confirm_password]):
                flash('Please fill in all fields.', 'error')
                return render_template('register.html')

            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html')

            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return render_template('register.html')

            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template('register.html')

            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()

            # Create initial profile
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()

            logging.info(f"Successfully registered user: {username}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            logging.error(f"Registration error: {e}")
            db.session.rollback()
            flash('An error occurred during registration.', 'error')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('chat_interface'))
        
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            logging.info(f"Login attempt for user: {username}")

            if not username or not password:
                flash('Please enter both username and password.', 'error')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                user.last_login = datetime.utcnow()

                # Create new session
                user_agent = parse(request.headers.get('User-Agent'))
                user_session = UserSession(
                    user_id=user.id,
                    ip_address=request.remote_addr,
                    device_info=f"{user_agent.browser.family} on {user_agent.os.family}"
                )

                db.session.add(user_session)
                db.session.commit()
                logging.info(f"Successful login for user: {username}")
                return redirect(url_for('chat_interface'))
            else:
                flash('Invalid username or password.', 'error')
                logging.warning(f"Failed login attempt for user: {username}")

        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('An error occurred during login.', 'error')

    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if not user.profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        logging.info(f"Created new profile for user: {user.username}")
    
    if request.method == 'POST':
        try:
            user.profile.first_name = request.form.get('first_name')
            user.profile.last_name = request.form.get('last_name')
            user.profile.phone_number = request.form.get('phone_number')
            user.profile.address = request.form.get('address')
            
            dob_str = request.form.get('date_of_birth')
            if dob_str:
                user.profile.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()

            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{user.username}_{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    user.profile.profile_picture = filename

            db.session.commit()
            logging.info(f"Updated profile for user: {user.username}")
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))

        except Exception as e:
            logging.error(f"Profile update error: {e}")
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'error')

    return render_template('profile.html', user=user)

@app.route('/chat_interface')
@login_required
def chat_interface():
    user = User.query.get(session['user_id'])
    return render_template('chat_interface.html', user=user)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        if not chatbot:
            return jsonify({'error': 'Chatbot service is currently unavailable'}), 503

        data = request.json
        user_message = data.get('message')
        language = data.get('language', 'en')
        message_type = data.get('type', 'text')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Translate to English if needed
        if language != 'en':
            user_message = translate_text(user_message, 'en')

        # Get response from model
        response = chatbot.get_response(user_message)

        # Translate response if needed
        if language != 'en':
            response = translate_text(response, language)

        # Save chat to database
        chat = Chat(
            user_id=session['user_id'],
            message=user_message,
            response=response,
            message_type=message_type,
            language=language
        )
        db.session.add(chat)
        db.session.commit()
        logging.info(f"Chat message saved for user_id: {session['user_id']}")

        return jsonify({'response': response})

    except Exception as e:
        logging.error(f"Chat error: {e}")
        db.session.rollback()
        return jsonify({'error': 'An error occurred processing your request'}), 500

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
@login_required
def logout():
    try:
        user_id = session.get('user_id')
        if user_id:
            active_session = UserSession.query.filter_by(
                user_id=user_id,
                session_status='active'
            ).first()
            
            if active_session:
                active_session.logout_time = datetime.utcnow()
                active_session.session_status = 'closed'
                db.session.commit()
                logging.info(f"User {user_id} logged out successfully")

        session.clear()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        logging.error(f"Logout error: {e}")
        session.clear()
        return redirect(url_for('login'))

def init_db():
    with app.app_context():
        try:
            # Create necessary directories
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs('static/css', exist_ok=True)
            os.makedirs('templates', exist_ok=True)
            
            # Create database and tables
            db.create_all()
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise

if __name__ == '__main__':
    try:
        init_db()
        app.run(debug=True)
    except Exception as e:
        logging.error(f"Application startup error: {e}")
