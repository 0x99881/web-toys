from pathlib import Path

from flask import Flask

from bm2.store import ExcelStore
from bm2.web import register_routes

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.secret_key = "bm2-local-secret"
store = ExcelStore(BASE_DIR)
register_routes(app, store)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
