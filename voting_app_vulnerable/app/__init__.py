from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    # Явно указываем пути к templates и static
    template_dir = os.path.abspath('templates')
    static_dir = os.path.abspath('static')
    
    print(f"Template directory: {template_dir}")
    print(f"Static directory: {static_dir}")
    print(f"Templates exist: {os.path.exists(template_dir)}")
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    app.config.from_object('app.config.Config')
    
    db.init_app(app)
    
    return app