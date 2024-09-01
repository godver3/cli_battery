from flask import Flask
from settings import Settings
import logging

app = Flask(__name__)
settings = Settings()

# Configure Flask to use our logger
app.logger.handlers = logging.getLogger().handlers
app.logger.setLevel(logging.getLogger().level)

from app import routes