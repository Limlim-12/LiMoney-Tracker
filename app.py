import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
import models
import routes

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ⚠️ FAIL-SAFE FIX: Check if we are specifically on Render
# Render automatically sets the 'RENDER' environment variable to 'true'
if os.environ.get("RENDER"):
    print("☁️ Running on Render (Production) - Applying ProxyFix")
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )
else:
    print("💻 Running Locally - ProxyFix Skipped")

models.init_db()
routes.init_routes(app)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
