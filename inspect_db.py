
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# แสดงรายชื่อตารางทั้งหมด
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

tables = cursor.fetchall()

for (table,) in tables:
    print(f"\n=== ตาราง: {table} ===")

    # แสดงชื่อคอลัมน์
    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = cursor.fetchall()

    for column in columns:
        print(f"- {column[1]} ({column[2]})")

conn.close()
