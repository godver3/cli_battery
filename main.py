from app import app
from settings import Settings
from app.database import Base, engine
from app.metadata_manager import MetadataManager
import threading
import time
import logging
import os

settings = Settings()

def setup_logging():
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file = os.path.join(log_directory, "cli_battery.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def initialize_database():
    Base.metadata.create_all(engine)
    logging.info("Database initialized.")

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
    # Setup logging
    setup_logging()

    # Initialize the database
    initialize_database()

    # Start the backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.start()

    # Run the Flask app (frontend) on port 5001, allowing outside access
    app.run(host='0.0.0.0', debug=True, use_reloader=False, port=5001)