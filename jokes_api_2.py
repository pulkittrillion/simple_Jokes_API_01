# jokes_api.py

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import random
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Database setup
DATABASE = 'jokes.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize the database with tables and sample data"""
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    
    db = get_db()
    cursor = db.cursor()
    
    # Create jokes table
    cursor.execute('''
        CREATE TABLE jokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setup TEXT NOT NULL,
            punchline TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            rating REAL DEFAULT 0.0,
            votes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create categories table
    cursor.execute('''
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')
    
    # Create favorites table (for tracking user favorites)
    cursor.execute('''
        CREATE TABLE favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            joke_id INTEGER,
            user_ip TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (joke_id) REFERENCES jokes (id)
        )
    ''')
    
    # Insert categories
    categories = [
        ('programming', 'Programming and coding jokes'),
        ('python', 'Python-specific jokes'),
        ('general', 'General tech jokes'),
        ('dad', 'Dad jokes for programmers'),
        ('dark', 'Dark humor for devs')
    ]
    cursor.executemany('INSERT INTO categories (name, description) VALUES (?, ?)', categories)
    
    # Insert sample jokes
    sample_jokes = [
        ("Why do programmers prefer dark mode?", "Because light attracts bugs!", "programming"),
        ("Why do Python programmers prefer snakes?", "Because they don't have to deal with Java!", "python"),
        ("How many programmers does it take to change a light bulb?", "None, that's a hardware problem!", "general"),
        ("Why did the programmer quit his job?", "Because he didn't get arrays!", "dad"),
        ("What's a programmer's favorite hangout place?", "Foo Bar!", "programming"),
        ("Why do programmers always mix up Halloween and Christmas?", "Because Oct 31 equals Dec 25!", "programming"),
        ("What do you call a programmer from Finland?", "Nerdic!", "general"),
        ("Why did the Python data scientist get arrested?", "She was caught trying to import pandas into the country!", "python"),
        ("What's the object-oriented way to become wealthy?", "Inheritance!", "programming"),
        ("Why did the developer go broke?", "Because he used up all his cache!", "dad"),
        ("How do you comfort a JavaScript bug?", "You console it!", "programming"),
        ("Why do Java developers wear glasses?", "Because they don't C#!", "programming"),
        ("What's a programmer's favorite snack?", "Microchips!", "dad"),
        ("Why was the JavaScript developer sad?", "Because he didn't Node how to Express himself!", "programming"),
        ("What do you call 8 hobbits?", "A hobbyte!", "dad"),
        ("Why do programmers hate nature?", "It has too many bugs!", "programming"),
        ("How do you tell HTML from HTML5?", "Try it out in Internet Explorer. Did it work? No? It's HTML5!", "programming"),
        ("What's the best thing about a Boolean?", "Even if you're wrong, you're only off by a bit!", "programming"),
        ("Why did the function quit its job?", "It didn't get a callback!", "programming"),
        ("What's a pirate's favorite programming language?", "You'd think it's R, but it's actually the C!", "dad")
    ]
    
    cursor.executemany(
        'INSERT INTO jokes (setup, punchline, category) VALUES (?, ?, ?)',
        sample_jokes
    )
    
    db.commit()
    db.close()
    print("Database initialized successfully!")

# Initialize database on first run
if not os.path.exists(DATABASE):
    init_db()

# Helper functions

def dict_from_row(row):
    """Convert database row to dictionary"""
    return dict(zip(row.keys(), row))

# Routes

@app.route('/')
def home():
    """API documentation"""
    return jsonify({
        "name": "Jokes API",
        "version": "2.0",
        "description": "A comprehensive jokes API for developers",
        "endpoints": {
            "GET /": "API documentation",
            "GET /jokes": "Get all jokes (supports pagination, filtering, sorting)",
            "GET /jokes/random": "Get a random joke",
            "GET /jokes/<id>": "Get a specific joke by ID",
            "GET /jokes/category/<category>": "Get jokes by category",
            "GET /categories": "Get all categories",
            "GET /stats": "Get API statistics",
            "POST /jokes": "Add a new joke",
            "PUT /jokes/<id>": "Update a joke",
            "DELETE /jokes/<id>": "Delete a joke",
            "POST /jokes/<id>/rate": "Rate a joke (1-5)",
            "POST /jokes/<id>/favorite": "Mark joke as favorite",
            "GET /favorites": "Get user's favorite jokes"
        },
        "query_parameters": {
            "page": "Page number (default: 1)",
            "per_page": "Items per page (default: 10, max: 100)",
            "category": "Filter by category",
            "sort": "Sort by: rating, votes, created_at (default: created_at)",
            "order": "Order: asc, desc (default: desc)"
        }
    })

@app.route('/jokes', methods=['GET'])
@limiter.limit("100 per minute")
def get_all_jokes():
    """Get all jokes with pagination, filtering, and sorting"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    category = request.args.get('category', type=str)
    sort_by = request.args.get('sort', 'created_at', type=str)
    order = request.args.get('order', 'desc', type=str).upper()
    
    # Validate sort and order
    allowed_sorts = ['rating', 'votes', 'created_at', 'id']
    if sort_by not in allowed_sorts:
        sort_by = 'created_at'
    
    if order not in ['ASC', 'DESC']:
        order = 'DESC'
    
    db = get_db()
    cursor = db.cursor()
    
    # Build query
    query = 'SELECT * FROM jokes'
    params = []
    
    if category:
        query += ' WHERE category = ?'
        params.append(category)
    
    query += f' ORDER BY {sort_by} {order}'
    
    # Get total count
    count_query = 'SELECT COUNT(*) as count FROM jokes'
    if category:
        count_query += ' WHERE category = ?'
        total = cursor.execute(count_query, params).fetchone()['count']
    else:
        total = cursor.execute(count_query).fetchone()['count']
    
    # Add pagination
    offset = (page - 1) * per_page
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    jokes = [dict_from_row(row) for row in cursor.fetchall()]
    db.close()
    
    return jsonify({
        "jokes": jokes,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    })

@app.route('/jokes/random', methods=['GET'])
@limiter.limit("50 per minute")
def get_random_joke():
    """Get a random joke"""
    category = request.args.get('category', type=str)
    
    db = get_db()
    cursor = db.cursor()
    
    if category:
        cursor.execute('SELECT * FROM jokes WHERE category = ? ORDER BY RANDOM() LIMIT 1', (category,))
    else:
        cursor.execute('SELECT * FROM jokes ORDER BY RANDOM() LIMIT 1')
    
    joke = cursor.fetchone()
    db.close()
    
    if joke:
        return jsonify(dict_from_row(joke))
    else:
        return jsonify({"error": "No jokes found"}), 404

@app.route('/jokes/<int:joke_id>', methods=['GET'])
def get_joke_by_id(joke_id):
    """Get a specific joke by ID"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    joke = cursor.fetchone()
    db.close()
    
    if joke:
        return jsonify(dict_from_row(joke))
    else:
        return jsonify({"error": "Joke not found"}), 404

@app.route('/jokes/category/<category>', methods=['GET'])
def get_jokes_by_category(category):
    """Get jokes by category"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM jokes WHERE category = ?', (category,))
    jokes = [dict_from_row(row) for row in cursor.fetchall()]
    db.close()
    
    return jsonify({
        "category": category,
        "count": len(jokes),
        "jokes": jokes
    })

@app.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM categories')
    categories = [dict_from_row(row) for row in cursor.fetchall()]
    
    # Get joke count for each category
    for cat in categories:
        cursor.execute('SELECT COUNT(*) as count FROM jokes WHERE category = ?', (cat['name'],))
        cat['joke_count'] = cursor.fetchone()['count']
    
    db.close()
    return jsonify(categories)

@app.route('/jokes', methods=['POST'])
@limiter.limit("10 per hour")
def add_joke():
    """Add a new joke"""
    data = request.get_json()
    
    if not data or 'setup' not in data or 'punchline' not in data:
        return jsonify({"error": "Setup and punchline are required"}), 400
    
    setup = data['setup']
    punchline = data['punchline']
    category = data.get('category', 'general')
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify category exists
    cursor.execute('SELECT * FROM categories WHERE name = ?', (category,))
    if not cursor.fetchone():
        db.close()
        return jsonify({"error": f"Category '{category}' does not exist"}), 400
    
    cursor.execute(
        'INSERT INTO jokes (setup, punchline, category) VALUES (?, ?, ?)',
        (setup, punchline, category)
    )
    db.commit()
    
    joke_id = cursor.lastrowid
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    new_joke = dict_from_row(cursor.fetchone())
    db.close()
    
    return jsonify(new_joke), 201

@app.route('/jokes/<int:joke_id>', methods=['PUT'])
@limiter.limit("20 per hour")
def update_joke(joke_id):
    """Update a joke"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if joke exists
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    if not cursor.fetchone():
        db.close()
        return jsonify({"error": "Joke not found"}), 404
    
    # Build update query
    updates = []
    params = []
    
    if 'setup' in data:
        updates.append('setup = ?')
        params.append(data['setup'])
    
    if 'punchline' in data:
        updates.append('punchline = ?')
        params.append(data['punchline'])
    
    if 'category' in data:
        # Verify category exists
        cursor.execute('SELECT * FROM categories WHERE name = ?', (data['category'],))
        if not cursor.fetchone():
            db.close()
            return jsonify({"error": f"Category '{data['category']}' does not exist"}), 400
        updates.append('category = ?')
        params.append(data['category'])
    
    if not updates:
        db.close()
        return jsonify({"error": "No valid fields to update"}), 400
    
    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(joke_id)
    
    query = f"UPDATE jokes SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    db.commit()
    
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    updated_joke = dict_from_row(cursor.fetchone())
    db.close()
    
    return jsonify(updated_joke)

@app.route('/jokes/<int:joke_id>', methods=['DELETE'])
@limiter.limit("10 per hour")
def delete_joke(joke_id):
    """Delete a joke"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    if not cursor.fetchone():
        db.close()
        return jsonify({"error": "Joke not found"}), 404
    
    cursor.execute('DELETE FROM jokes WHERE id = ?', (joke_id,))
    db.commit()
    db.close()
    
    return jsonify({"message": "Joke deleted successfully"}), 200

@app.route('/jokes/<int:joke_id>/rate', methods=['POST'])
@limiter.limit("30 per hour")
def rate_joke(joke_id):
    """Rate a joke (1-5 stars)"""
    data = request.get_json()
    
    if not data or 'rating' not in data:
        return jsonify({"error": "Rating is required"}), 400
    
    rating = data['rating']
    
    if not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    joke = cursor.fetchone()
    
    if not joke:
        db.close()
        return jsonify({"error": "Joke not found"}), 404
    
    # Calculate new rating
    current_rating = joke['rating']
    current_votes = joke['votes']
    
    new_votes = current_votes + 1
    new_rating = ((current_rating * current_votes) + rating) / new_votes
    
    cursor.execute(
        'UPDATE jokes SET rating = ?, votes = ? WHERE id = ?',
        (new_rating, new_votes, joke_id)
    )
    db.commit()
    
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    updated_joke = dict_from_row(cursor.fetchone())
    db.close()
    
    return jsonify(updated_joke)

@app.route('/jokes/<int:joke_id>/favorite', methods=['POST'])
@limiter.limit("50 per hour")
def favorite_joke(joke_id):
    """Mark a joke as favorite"""
    user_ip = get_remote_address()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM jokes WHERE id = ?', (joke_id,))
    if not cursor.fetchone():
        db.close()
        return jsonify({"error": "Joke not found"}), 404
    
    # Check if already favorited
    cursor.execute(
        'SELECT * FROM favorites WHERE joke_id = ? AND user_ip = ?',
        (joke_id, user_ip)
    )
    
    if cursor.fetchone():
        db.close()
        return jsonify({"message": "Joke already in favorites"}), 200
    
    cursor.execute(
        'INSERT INTO favorites (joke_id, user_ip) VALUES (?, ?)',
        (joke_id, user_ip)
    )
    db.commit()
    db.close()
    
    return jsonify({"message": "Joke added to favorites"}), 201

@app.route('/favorites', methods=['GET'])
def get_favorites():
    """Get user's favorite jokes"""
    user_ip = get_remote_address()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT j.* FROM jokes j
        INNER JOIN favorites f ON j.id = f.joke_id
        WHERE f.user_ip = ?
        ORDER BY f.created_at DESC
    ''', (user_ip,))
    
    favorites = [dict_from_row(row) for row in cursor.fetchall()]
    db.close()
    
    return jsonify({
        "count": len(favorites),
        "favorites": favorites
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get API statistics"""
    db = get_db()
    cursor = db.cursor()
    
    # Total jokes
    cursor.execute('SELECT COUNT(*) as count FROM jokes')
    total_jokes = cursor.fetchone()['count']
    
    # Total categories
    cursor.execute('SELECT COUNT(*) as count FROM categories')
    total_categories = cursor.fetchone()['count']
    
    # Top rated jokes
    cursor.execute('SELECT * FROM jokes ORDER BY rating DESC LIMIT 5')
    top_rated = [dict_from_row(row) for row in cursor.fetchall()]
    
    # Most voted jokes
    cursor.execute('SELECT * FROM jokes ORDER BY votes DESC LIMIT 5')
    most_voted = [dict_from_row(row) for row in cursor.fetchall()]
    
    # Category distribution
    cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM jokes 
        GROUP BY category 
        ORDER BY count DESC
    ''')
    category_dist = [dict_from_row(row) for row in cursor.fetchall()]
    
    db.close()
    
    return jsonify({
        "total_jokes": total_jokes,
        "total_categories": total_categories,
        "top_rated_jokes": top_rated,
        "most_voted_jokes": most_voted,
        "category_distribution": category_dist
    })

@app.route('/search', methods=['GET'])
def search_jokes():
    """Search jokes by keyword"""
    query = request.args.get('q', '', type=str)
    
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    search_pattern = f'%{query}%'
    cursor.execute('''
        SELECT * FROM jokes 
        WHERE setup LIKE ? OR punchline LIKE ?
    ''', (search_pattern, search_pattern))
    
    results = [dict_from_row(row) for row in cursor.fetchall()]
    db.close()
    
    return jsonify({
        "query": query,
        "count": len(results),
        "results": results
    })

# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
