from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import logging
import os
from datetime import datetime
from chatbot_model import BankingChatbot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
app.secret_key = os.environ.get('SECRET_KEY', 'f58f73f1bc36ce25')

# Initialize chatbot
chatbot = BankingChatbot()

# Database setup
def init_db():
    conn = sqlite3.connect('banking_chatbot.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create chat_history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            intent TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Database connection context manager
class Database:
    def __enter__(self):
        self.conn = sqlite3.connect('banking_chatbot.db')
        self.conn.row_factory = sqlite3.Row
        return self.conn.cursor()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, password, confirm_password]):
            flash('Please fill in all fields.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        try:
            with Database() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        with Database() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_message = request.json.get('message', '').strip()
        language = request.json.get('language', 'en')
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        try:
            # Get prediction and response from model
            intent, confidence, response = chatbot.predict(user_message)
            logging.info(f"Predicted intent: {intent} with confidence: {confidence}")
            
            # Save to database
            with Database() as cursor:
                cursor.execute("""
                    INSERT INTO chat_history (user_id, message, response, intent, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (session['user_id'], user_message, response, intent, confidence))
            
            return jsonify({
                'response': response,
                'intent': intent,
                'confidence': confidence
            })
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return jsonify({
                'response': "I apologize, but I'm having trouble processing your request at the moment.",
                'intent': 'error',
                'confidence': 0.0
            })
    
    # Get chat history
    try:
        with Database() as cursor:
            cursor.execute("""
                SELECT message, response, intent, confidence, timestamp
                FROM chat_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (session['user_id'],))
            chat_history = cursor.fetchall()
        return render_template('chat.html', chat_history=chat_history, username=session.get('username', 'User'))
    except Exception as e:
        logging.error(f"Error fetching chat history: {e}")
        return render_template('chat.html', chat_history=[], username=session.get('username', 'User'))

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        with Database() as cursor:
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (session['user_id'],))
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error clearing chat history: {e}")
        return jsonify({'error': 'Failed to clear chat history'}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('models', exist_ok=True)
    
    # Run the app
    app.run(debug=True)
