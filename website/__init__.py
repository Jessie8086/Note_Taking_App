from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "dayabase.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'li4931 CS348 project'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)
    
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/') 

    from . import models

    with app.app_context():
         db.create_all()
         add_indexes()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return models.User.query.get(int(id))
    
    return app

def create_database(app):
        if not path.exists('website/' + DB_NAME):
            db.create_all(app=app)
            print('Created Database!')

def add_indexes():
    from sqlalchemy import text

    index_sqls = [
        "CREATE INDEX IF NOT EXISTS idx_note_user_id ON note(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_note_user_date ON note(user_id, date);",
        "CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id);",
        "CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id);"
    ]
    for sql in index_sqls:
        db.session.execute(text(sql))
    db.session.commit()
