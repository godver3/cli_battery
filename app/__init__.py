from flask import Flask
from app.settings import Settings
import os
import logging

app = Flask(__name__)
settings = Settings()

# Set a secret key for the application
app.secret_key = os.environ.get('SECRET_KEY') or '123456789'

# Configure Flask to use our logger
app.logger.handlers = logging.getLogger().handlers
app.logger.setLevel(logging.getLogger().level)

from app import routes