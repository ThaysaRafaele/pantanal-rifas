import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / 'db.sqlite3'
if not db.exists():
    print('db not found at', db)
    raise SystemExit(1)

conn = sqlite3.connect(str(db))
cur = conn.cursor()

query = '''
SELECT u.id, u.username, u.email, p.nome_social, p.cpf
FROM auth_user u
LEFT JOIN rifa_userprofile p ON p.user_id = u.id
ORDER BY u.id DESC
LIMIT 20
'''
for row in cur.execute(query):
    print(row)
conn.close()
