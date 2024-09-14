from flask import Flask
from app.database import init_db

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://cli_debrid:cli_debrid@db:5432/cli_battery_database'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        init_db(app)

    # Import and register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app