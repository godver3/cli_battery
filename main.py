from app import app
from app.settings import Settings
from app.database import Base, engine
from app.metadata_manager import MetadataManager
import threading
import time
import logging
import os
from sqlalchemy import inspect
import colorlog
from flask.logging import default_handler
import sys

class ExternalCallFilter(logging.Filter):
    def filter(self, record):
        if 'api.trakt.tv' in record.getMessage() or 'urllib3.connectionpool' in record.name:
            record.levelname = 'EXTERNAL'
            return True
        return False

settings = Settings()


def setup_logging():
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file = os.path.join(log_directory, "cli_battery.log")

    # Create a basic formatter for debugging
    basic_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler(log_file, mode='w')  # 'w' mode to overwrite the file each run

    console_handler.setFormatter(basic_formatter)
    file_handler.setFormatter(basic_formatter)

    # Create a logger and add the handlers
    logger = logging.getLogger()
    logger.handlers = []  # Clear existing handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    # Test logging
    logger.debug("Debug message from setup_logging")
    logger.info("Info message from setup_logging")

    return logger

def initialize_database():
    inspector = inspect(engine)
    if not inspector.has_table("episodes"):
        Base.metadata.create_all(engine)
        logging.info("Database initialized with all tables.")
    else:
        # Check if the 'overview' column exists in the 'episodes' table
        columns = inspector.get_columns("episodes")
        column_names = [column['name'] for column in columns]
        if 'overview' not in column_names:
            # Add the 'overview' column to the 'episodes' table
            with engine.connect() as connection:
                connection.execute("ALTER TABLE episodes ADD COLUMN overview TEXT")
            logging.info("Added 'overview' column to 'episodes' table.")
        else:
            logging.info("Database schema is up-to-date.")

def refresh_metadata_task():
    while True:
        # Refresh metadata for all items
        items = MetadataManager.get_all_items()
        for item in items:
            if MetadataManager.is_metadata_stale(item):
                MetadataManager.refresh_metadata(item.imdb_id)
        
        # Sleep for the specified update frequency
        time.sleep(settings.update_frequency * 60)

def run_backend():
    logging.info("Backend is running...")
    refresh_metadata_task()

if __name__ == '__main__':
    logging.info("Script started")  # Basic print to ensure output is working

    # Setup logging
    logger = setup_logging()

    logging.info("Logging setup complete")  # Another print to check execution flow

    # Initialize the database
    initialize_database()

    # Start the backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.start()
    # Run the Flask app (frontend) on port 5001, allowing outside access
    app.run(host='0.0.0.0', debug=False, use_reloader=False, port=5001)