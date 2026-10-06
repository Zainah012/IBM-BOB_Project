import os
os.makedirs("uploads", exist_ok=True)
from app import app
app.run(debug=False, port=5001, use_reloader=False, threaded=True)
