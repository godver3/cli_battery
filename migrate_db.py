import sqlite3
from sqlalchemy import create_engine, inspect

def upgrade():
    # Connect directly to the SQLite database
    conn = sqlite3.connect('metadata.db')
    cursor = conn.cursor()

    # Check if the 'type' column exists
    cursor.execute("PRAGMA table_info(items)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'type' not in columns:
        # Add the 'type' column
        cursor.execute("ALTER TABLE items ADD COLUMN type TEXT")
        print("Added 'type' column to items table.")
    else:
        print("'type' column already exists in items table.")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Verify the change using SQLAlchemy
    engine = create_engine('sqlite:///metadata.db')
    inspector = inspect(engine)
    columns = inspector.get_columns('items')
    column_names = [column['name'] for column in columns]
    
    if 'type' in column_names:
        print("Verified: 'type' column exists in items table.")
    else:
        print("Warning: 'type' column was not added successfully.")

if __name__ == "__main__":
    upgrade()
    print("Database migration completed.")