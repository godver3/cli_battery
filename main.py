from app import create_app
from app.database import init_db, Session, Base
import logging
import time
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
import threading
from app.grpc_service import serve as grpc_serve
import logging

def initialize_database(app):
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            print(f"Attempting to initialize database (attempt {attempt + 1}/{max_retries})")
            
            # Initialize the database
            engine = init_db(app)
            
            # Test connection
            with engine.connect() as connection:
                print("Testing database connection...")
                connection.execute(text("SELECT 1"))
                print("Database connection successful")
            
            # Verify tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"Tables in the database after creation attempt: {tables}")
            
            if "items" not in tables:
                print("The 'items' table was not created.")
                raise Exception("The 'items' table was not created.")
            
            print("Database initialization successful.")
            return engine
        except OperationalError as e:
            print(f"OperationalError during database initialization: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Failed to connect to the database after multiple attempts.")
                raise
        except Exception as e:
            print(f"Unexpected error during database initialization: {str(e)}")
            raise

    print("Database initialization failed after all attempts")
    return None

def run_grpc_server():
    grpc_serve()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging = logging.getLogger(__name__)
    logging.info("Starting application")
    
    app = create_app()
    engine = initialize_database(app)
    if engine is None:
        print("Failed to initialize the database. Exiting.")
        import sys
        sys.exit(1)

    logging.info("Database initialized successfully")

    # Start gRPC server in a separate thread
    grpc_thread = threading.Thread(target=run_grpc_server, daemon=True)
    grpc_thread.start()

    # Run Flask server
    app.run(host='0.0.0.0', port=5001, debug=True)