from flask import Flask, redirect, url_for, session, jsonify, request
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

oauth = OAuth(app)
nonce = generate_token()

oauth.register(
    name=os.getenv('OIDC_CLIENT_NAME'),
    client_id=os.getenv('OIDC_CLIENT_ID'),
    client_secret=os.getenv('OIDC_CLIENT_SECRET'),
    authorization_endpoint="http://localhost:5556/auth",
    token_endpoint="http://dex:5556/token",
    jwks_uri="http://dex:5556/keys",
    userinfo_endpoint="http://dex:5556/userinfo",
    device_authorization_endpoint="http://dex:5556/device/code",
    client_kwargs={'scope': 'openid email profile'}
)

mongo = MongoClient("mongodb://root:example@mongo:27017/")
db = mongo["nyt"]
comments = db["comments"]

MODERATOR_EMAILS = os.getenv("MODERATOR_EMAILS", "").split(",")

@app.route('/')
def home():
    user = session.get('user')
    if user:
        return f"<h2>Logged in as {user['email']}</h2><a href='/logout'>Logout</a>"
    return '<a href="/login">Login with Dex</a>'

@app.route('/login')
def login():
    session['nonce'] = nonce
    redirect_uri = 'http://localhost:8000/authorize'
    return oauth.flask_app.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/authorize')
def authorize():
    token = oauth.flask_app.authorize_access_token()
    nonce = session.get('nonce')
    user_info = oauth.flask_app.parse_id_token(token, nonce=nonce)
    session['user'] = user_info
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/key')
def get_key():
    return jsonify({'apiKey': os.getenv('NYT_API_KEY')})

@app.route('/api/user')
def get_user():
    if 'user' in session:
        return jsonify(session['user'])
    return jsonify(None), 401

@app.route('/api/comments', methods=['POST'])
def post_comment():
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    article_url = data.get('article_url')
    text = data.get('text')

    if not article_url or not text:
        return jsonify({'error': 'Missing data'}), 400

    comment = {
        "article_url": article_url,
        "author_email": user["email"],
        "text": text,
        "timestamp": datetime.utcnow(),
        "moderated": False
    }

    comments.insert_one(comment)
    return jsonify({'status': 'ok'}), 201

@app.route('/api/comments', methods=['GET'])
def get_comments():
    url = request.args.get('url')
    if not url:
        return jsonify([])

    result = comments.find({"article_url": url}).sort("timestamp", -1)
    return jsonify([
        {
            "id": str(c["_id"]),
            "author_email": c["author_email"],
            "text": "COMMENT REMOVED BY MODERATOR!" if c.get("moderated") else c["text"],
            "timestamp": c["timestamp"].isoformat()
        } for c in result
    ])

@app.route('/api/moderate', methods=['POST'])
def moderate_comment():
    user = session.get('user')
    if not user or user["email"] not in MODERATOR_EMAILS:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    comment_id = data.get("id")

    if not comment_id:
        return jsonify({"error": "Missing comment ID"}), 400

    from bson.objectid import ObjectId
    comments.update_one({"_id": ObjectId(comment_id)}, {"$set": {"moderated": True}})
    return jsonify({"status": "moderated"})
