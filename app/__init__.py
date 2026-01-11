from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from redis import Redis
from rq import Queue
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
    
    # Database config
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///media_organizer.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Redis Queue config
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    app.redis = Redis.from_url(redis_url)
    app.task_queue = Queue('default', connection=app.redis)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints
    from app.routes import main
    app.register_blueprint(main)

    return app
