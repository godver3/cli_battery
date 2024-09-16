from app import create_app
from app.database import init_db, Session, Base
import logging
import time
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
import threading
from app.grpc_service import serve as grpc_serve
import logging
from logging.handlers import RotatingFileHandler
import os

def initialize_database(app):
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            
            # Initialize the database
            engine = init_db(app)
            
            # Test connection
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            
            # Verify tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if "items" not in tables:
                raise Exception("The 'items' table was not created.")
            
            return engine
        except OperationalError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            raise

    return None

def run_grpc_server():
    grpc_serve()

if __name__ == '__main__':
    # Create the log directory if it doesn't exist
    log_dir = '/user/logs'
    os.makedirs(log_dir, exist_ok=True)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    file_handler = RotatingFileHandler('/user/logs/debug.log', maxBytes=1024 * 1024, backupCount=10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Get the root logger and add the file handler
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    # Get the logger for this module
    logging = logging.getLogger(__name__)
    logging.info("Starting application")
    
    app = create_app()
    engine = initialize_database(app)
    if engine is None:
        import sys
        sys.exit(1)

    logging.info("Database initialized successfully")

    # Start gRPC server in a separate thread
    grpc_thread = threading.Thread(target=run_grpc_server, daemon=True)
    grpc_thread.start()

    # Run Flask server
    app.run(host='0.0.0.0', port=5001, debug=True)