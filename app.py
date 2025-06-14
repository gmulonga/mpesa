from flask import Flask
from dotenv import load_dotenv
import os
from routes import bp
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)
app.register_blueprint(bp, url_prefix="/api/mpesa")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(debug=True, port=port)
