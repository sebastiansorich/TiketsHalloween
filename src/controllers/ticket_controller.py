import io
import os
from PIL import Image 
from flask import request, jsonify, send_file
from datetime import datetime
import pytz
import qrcode
from ..models.ticket import Ticket
from .. import db
from ..schemas.ticket_schema import ticket_schema, tickets_schema
import secrets
from sqlalchemy.exc import SQLAlchemyError

def generate_token():
    """Genera un token único y aleatorio en formato URL-safe base64."""
    return secrets.token_urlsafe(32)  # 32 bytes = 256 bits

def create_ticket():
    try:
        # Generar un token único
        token = generate_token()

        # Crear un nuevo ticket
        new_ticket = Ticket(
            token=token,
            is_used=False,
            date_of_issue=datetime.utcnow()
        )

        db.session.add(new_ticket)
        db.session.commit()
        return ticket_schema.jsonify(new_ticket), 201
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()

from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError

def verify_ticket(token):
    try:
        ticket = Ticket.query.filter_by(token=token).first()
        if not ticket:
            # Si el ticket no existe, respondemos con un error 404
            return jsonify({"error": "La entrada no valida"}), 404
        if ticket.is_used:
            # Si el ticket ya ha sido usado, respondemos con un error 400
            return jsonify({"error": "La entrada es valida pero ya fue usada"}), 200
        
        # Si el ticket es válido y no ha sido usado, respondemos con un mensaje de éxito
        return jsonify({"message": "La entrada es valida y aun no ha sido usada"}), 200
    except SQLAlchemyError:
        # En caso de error en la base de datos, respondemos con un error 500
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        # En caso de cualquier otro error, respondemos con un error 500
        return jsonify({"error": str(e)}), 500

def use_ticket(token):
    try:
        # Buscar el ticket por token
        ticket = Ticket.query.filter_by(token=token).first()
        
        if not ticket:
            # Si el ticket no existe, respondemos con un error 404
            return jsonify({"error": "La entrada no es válida"}), 404
            
        if ticket.is_used:
            # Si el ticket ya ha sido usado, respondemos con un error 400
            return jsonify({"error": "La entrada ya ha sido usada"}), 400

        # Marcar el ticket como utilizado
        ticket.is_used = True
        
        # Verificar que el cambio se aplicó antes del commit
        print(f"DEBUG: Antes del commit - is_used: {ticket.is_used}")
        
        # Hacer commit de los cambios
        db.session.commit()
        
        # Verificar que el cambio se guardó después del commit
        print(f"DEBUG: Después del commit - is_used: {ticket.is_used}")
        
        # Refrescar el objeto desde la base de datos para asegurar que tenemos los datos más recientes
        db.session.refresh(ticket)
        
        return ticket_schema.jsonify(ticket), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"DEBUG: Error de SQLAlchemy: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error general: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()

def get_tickets():
    try:
        all_tickets = Ticket.query.all()
        # Obtener la zona horaria de Santa Cruz, Bolivia
        bolivia_tz = pytz.timezone('America/La_Paz')

        # Convertir las fechas de emisión a la zona horaria de Santa Cruz
        for ticket in all_tickets:
            if ticket.date_of_issue:
                # Asegúrate de que date_of_issue esté en formato UTC
                if ticket.date_of_issue.tzinfo is None:
                    ticket.date_of_issue = pytz.utc.localize(ticket.date_of_issue)
                # Convertir la fecha de emisión de UTC a la zona horaria local
                ticket.date_of_issue = ticket.date_of_issue.astimezone(bolivia_tz)
        
        result = tickets_schema.dump(all_tickets)
        return jsonify(result), 200
    except SQLAlchemyError as e:
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500    
    
def delete_ticket_by_token(token):
    try:
        ticket = Ticket.query.filter_by(token=token).first()
        if not ticket:
            # Si el ticket no existe, respondemos con un error 404
            return jsonify({"error": "La entrada no valida"}), 404
        if ticket.is_used:
            # Si el ticket ya ha sido usado, respondemos con un error 400
            return jsonify({"error": "La entrada ya ha usada"}), 400
        
        # Eliminar el ticket de la base de datos
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({"message": "Ticket successfully deleted"}), 200
    except SQLAlchemyError:
        # En caso de error en la base de datos, respondemos con un error 500
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        # En caso de cualquier otro error, respondemos con un error 500
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()


def delete_ticket(id):
    try:
        ticket = Ticket.query.get(id)
        if not ticket:
            # Si el ticket no existe, respondemos con un error 404
            return jsonify({"error": "Ticket not found"}), 404
        if ticket.is_used:
            # Si el ticket ya ha sido usado, respondemos con un error 400
            return jsonify({"error": "Ticket has already been used, cannot delete"}), 400
        
        # Eliminar el ticket de la base de datos
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({"message": "Ticket successfully deleted"}), 200
    except SQLAlchemyError:
        # En caso de error en la base de datos, respondemos con un error 500
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        # En caso de cualquier otro error, respondemos con un error 500
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()

def generate_qr(token):
    try:
        # Generar el código QR a partir del token
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)

        # Crear la imagen QR
        img = qr.make_image(fill="black", back_color="white")

        # Guardar la imagen en un objeto de memoria para enviarla como respuesta
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        # Retornar la imagen como archivo adjunto
        return send_file(img_io, mimetype='image/png')

    except SQLAlchemyError as e:
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    
def generate_invitation_with_qr(token):
    try:
        # Crear el código QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Cargar la imagen base
        base_dir = os.path.abspath(os.path.dirname(__file__))
        image_path = os.path.join(base_dir, '..', '..', 'static', 'invitation_background.png')
        background = Image.open(image_path)

        # --- 🔧 Ajustar proporción de fondo automáticamente ---
        desired_ratio = 3 / 4  # Relación vertical recomendada
        bg_width, bg_height = background.size
        current_ratio = bg_width / bg_height

        if current_ratio > desired_ratio:
            # Recortar los lados
            new_width = int(bg_height * desired_ratio)
            left = (bg_width - new_width) // 2
            background = background.crop((left, 0, left + new_width, bg_height))
        else:
            # Recortar arriba y abajo
            new_height = int(bg_width / desired_ratio)
            top = (bg_height - new_height) // 2
            background = background.crop((0, top, bg_width, top + new_height))

        # --- 📏 Redimensionar a tamaño ideal (A6 a 300 dpi ≈ 1240x1754 px) ---
        background = background.resize((1240, 1754))

        # --- 📱 Tamaño y posición del QR ---
        qr_size = (400, 400)
        qr_img = qr_img.resize(qr_size)

        qr_x = (background.width - qr_size[0]) // 2
        qr_y = int(background.height * 0.45)  # Centrado ligeramente hacia arriba

        # --- 🧩 Combinar QR con fondo ---
        background.paste(qr_img, (qr_x, qr_y))

        # --- 💾 Guardar en memoria y devolver ---
        img_io = io.BytesIO()
        background.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}, 500
