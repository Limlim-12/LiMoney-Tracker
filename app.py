import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- DATABASE CONFIGURATION ---
# 1. Get the URL from the environment variable (Render sets this)
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Fix for SQLAlchemy: It requires 'postgresql://', but Supabase might give 'postgres://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    print("☁️ Using Supabase (Production Database)")
else:
    # Fallback: Use local SQLite if no URL is found (for local testing)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///limoney.db"
    print("💻 Using Local SQLite Database")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the Database
db = SQLAlchemy(app)

# ⚠️ FAIL-SAFE FIX: Check if we are specifically on Render
# Render automatically sets the 'RENDER' environment variable to 'true'
if os.environ.get("RENDER"):
    print("☁️ Running on Render (Production) - Applying ProxyFix")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
else:
    print("💻 Running Locally - ProxyFix Skipped")

# Import routes and models after db initialization to avoid circular imports
import models
import routes

# Create tables automatically (This replaces models.init_db)
with app.app_context():
    db.create_all()
    print("✅ Database tables created/verified")

# Initialize routes
routes.init_routes(app)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
