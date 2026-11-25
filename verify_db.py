import sqlite3

conn = sqlite3.connect('data/telangana_weather.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('Database Tables:')
for t in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {t[0]}')
    count = cursor.fetchone()[0]
    print(f'  - {t[0]}: {count} records')

# Show sample district summary
print('\nDistrict Summary:')
cursor.execute('SELECT district, avg_rainfall, avg_drought_risk_score FROM district_summary')
for row in cursor.fetchall():
    print(f'  {row[0]}: Rainfall={row[1]:.2f}mm, Risk Score={row[2]:.2f}')

# Show anomaly events
print('\nAnomaly Events:')
cursor.execute('SELECT event_type, COUNT(*) as count FROM anomaly_events GROUP BY event_type')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} events')

conn.close()