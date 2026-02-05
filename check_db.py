import os
import sys
from pathlib import Path

# Ensure project `src` directory is on sys.path so `backend` package can be imported
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Set TEST_MODE from within the script just in case the environment isn't set by the shell
os.environ['TEST_MODE'] = '1'

from backend.main import init_db
from backend.config import get_db_path, get_connection

print('DB path:', get_db_path())
print('--- manual create test ---')
conn = get_connection()
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS manual_test(id INTEGER PRIMARY KEY, name TEXT)")
conn.commit()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('tables after manual create:', cur.fetchall())

print('\n--- run init_db() now ---')
init_db()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('tables after init_db():', cur.fetchall())

# Query columns of users table if exists
cur.execute("SELECT name FROM sqlite_master WHERE name='users'")
if cur.fetchone():
	cur.execute("PRAGMA table_info(users);")
	print('users columns:', cur.fetchall())
	cur.execute("INSERT OR IGNORE INTO users(username, password, role) VALUES (?, ?, ?)", ('ci_user', 'pw', 'volunteer'))
	conn.commit()
	cur.execute("SELECT username, role FROM users WHERE username=?", ('ci_user',))
	print('ci_user row:', cur.fetchone())
else:
	print('users table still not present')

print('\nDone')
