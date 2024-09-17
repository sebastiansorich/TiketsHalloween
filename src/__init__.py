# src/__init__.py

import os
from flask import jsonify, Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate


db = SQLAlchemy()
ma = Marshmallow()
migrate = Migrate()
 


def create_app():
    app = Flask(__name__)
    app.config.from_object('src.config.Config')
    
    # Inicializar extensiones
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)

     # Configuración de CORS
    CORS(app, resources={r"/*": {"origins": "https://tickets-scanner.vercel.app"}})  # Permitir solicitudes desde tu dominio

    # Importar modelos dentro del contexto de la aplicación
    with app.app_context():
        from src.models.ticket import Ticket

        db.create_all()


    # Importar y registrar blueprints
 
    from src.routes.ticket_routes import ticket_bp
  
    app.register_blueprint(ticket_bp)


    return app
