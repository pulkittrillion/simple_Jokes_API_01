# jokes_api.py

from flask import Flask, jsonify, request
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Jokes database
JOKES = [
    {
        "id": 1,
        "setup": "Why do programmers prefer dark mode?",
        "punchline": "Because light attracts bugs!"
    },
    {
        "id": 2,
        "setup": "Why do Python programmers prefer snakes?",
        "punchline": "Because they don't have to deal with Java!"
    },
    {
        "id": 3,
        "setup": "How many programmers does it take to change a light bulb?",
        "punchline": "None, that's a hardware problem!"
    },
    {
        "id": 4,
        "setup": "Why did the programmer quit his job?",
        "punchline": "Because he didn't get arrays!"
    },
    {
        "id": 5,
        "setup": "What's a programmer's favorite hangout place?",
        "punchline": "Foo Bar!"
    },
    {
        "id": 6,
        "setup": "Why do programmers always mix up Halloween and Christmas?",
        "punchline": "Because Oct 31 equals Dec 25!"
    },
    {
        "id": 7,
        "setup": "What do you call a programmer from Finland?",
        "punchline": "Nerdic!"
    },
    {
        "id": 8,
        "setup": "Why did the Python data scientist get arrested?",
        "punchline": "She was caught trying to import pandas into the country!"
    }
]

# Routes

@app.route('/')
def home():
    """Welcome endpoint with API documentation"""
    return jsonify({
        "message": "Welcome to the Jokes API!",
        "endpoints": {
            "/": "API documentation",
            "/jokes": "Get all jokes",
            "/jokes/random": "Get a random joke",
            "/jokes/<id>": "Get a specific joke by ID",
            "/jokes/count": "Get total number of jokes"
        }
    })

@app.route('/jokes', methods=['GET'])
def get_all_jokes():
    """Get all jokes"""
    return jsonify({
        "count": len(JOKES),
        "jokes": JOKES
    })

@app.route('/jokes/random', methods=['GET'])
def get_random_joke():
    """Get a random joke"""
    joke = random.choice(JOKES)
    return jsonify(joke)

@app.route('/jokes/<int:joke_id>', methods=['GET'])
def get_joke_by_id(joke_id):
    """Get a specific joke by ID"""
    joke = next((joke for joke in JOKES if joke['id'] == joke_id), None)
    
    if joke:
        return jsonify(joke)
    else:
        return jsonify({"error": "Joke not found"}), 404

@app.route('/jokes/count', methods=['GET'])
def get_joke_count():
    """Get the total number of jokes"""
    return jsonify({"count": len(JOKES)})

@app.route('/jokes', methods=['POST'])
def add_joke():
    """Add a new joke"""
    data = request.get_json()
    
    if not data or 'setup' not in data or 'punchline' not in data:
        return jsonify({"error": "Setup and punchline are required"}), 400
    
    new_joke = {
        "id": max(joke['id'] for joke in JOKES) + 1,
        "setup": data['setup'],
        "punchline": data['punchline']
    }
    
    JOKES.append(new_joke)
    return jsonify(new_joke), 201

# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
