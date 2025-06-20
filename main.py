from flask import Flask
from src.api.routes import init_routes
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/process-document": {"origins": "http://localhost:8080"}})  # Permitir solo localhost:8080

init_routes(app)

if __name__ == '__main__':
    app.run(debug=True, port=5000)