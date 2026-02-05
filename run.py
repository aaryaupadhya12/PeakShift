import os
import sys
import uvicorn
from src.backend.init_db import init_database

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Starting server...")
    uvicorn.run("backend.main:app", 
                host="127.0.0.1", 
                port=8000, 
                reload=True,
                reload_dirs=[os.path.join(src_path, 'backend')])