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
        from PIL import Image, ImageDraw, ImageFont
        import qrcode, os, io
        from flask import send_file

        # --- Crear el código QR con estilo terrorífico 🎃 ---
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(token)
        qr.make(fit=True)
        
        # QR con colores de terror: rojo oscuro sobre negro
        qr_img = qr.make_image(
            fill_color="#8B0000",      # Rojo sangre oscuro
            back_color="#1a1a1a"       # Gris muy oscuro (casi negro)
        ).convert("RGBA")

        # --- Cargar imagen base ---
        base_dir = os.path.abspath(os.path.dirname(__file__))
        image_path = os.path.join(base_dir, '..', '..', 'static', 'invitation_background.png')
        background = Image.open(image_path).convert("RGBA")

        # --- Ajustar proporción ---
        desired_ratio = 3 / 4
        bg_width, bg_height = background.size
        current_ratio = bg_width / bg_height

        if current_ratio > desired_ratio:
            new_width = int(bg_height * desired_ratio)
            left = (bg_width - new_width) // 2
            background = background.crop((left, 0, left + new_width, bg_height))
        else:
            new_height = int(bg_width / desired_ratio)
            top = (bg_height - new_height) // 2
            background = background.crop((0, top, bg_width, top + new_height))

        # --- Redimensionar ---
        background = background.resize((1240, 1754))

        # --- Preparar el QR con efectos terroríficos 🩸 ---
        import random
        
        # Tamaño del QR
        qr_size = (380, 380)
        qr_img = qr_img.resize(qr_size)
        
        # Crear una capa más grande para el marco y efectos
        frame_size = (int(qr_size[0] * 1.25), int(qr_size[1] * 1.25))
        qr_with_effects = Image.new('RGBA', frame_size, (0, 0, 0, 0))
        effects_draw = ImageDraw.Draw(qr_with_effects)
        
        # --- 1. Fondo con textura de papel viejo/quemado ---
        paper_color = (40, 35, 30, 230)  # Marrón oscuro envejecido
        effects_draw.rectangle([0, 0, frame_size[0], frame_size[1]], fill=paper_color)
        
        # Agregar manchas de "quemado" y envejecimiento
        for _ in range(15):
            x = random.randint(0, frame_size[0])
            y = random.randint(0, frame_size[1])
            size = random.randint(20, 60)
            burn_color = (25, 20, 15, random.randint(80, 150))
            effects_draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], fill=burn_color)
        
        # --- 2. Marco terrorífico con borde ---
        border_thickness = 8
        border_color = (100, 0, 0, 255)  # Rojo oscuro
        effects_draw.rectangle(
            [border_thickness, border_thickness, 
             frame_size[0]-border_thickness, frame_size[1]-border_thickness],
            outline=border_color, width=border_thickness
        )
        
        # --- 3. Manchas de sangre alrededor del marco 🩸 ---
        blood_positions = [
            # Esquinas y bordes
            (frame_size[0]//4, border_thickness),  # Arriba izquierda
            (frame_size[0]*3//4, border_thickness),  # Arriba derecha
            (border_thickness, frame_size[1]//2),  # Izquierda medio
            (frame_size[0]-border_thickness-10, frame_size[1]//3),  # Derecha
        ]
        
        for x, y in blood_positions:
            # Mancha principal
            blood_size = random.randint(30, 50)
            blood_color = (139, 0, 0, random.randint(180, 220))
            effects_draw.ellipse([x-blood_size//2, y-blood_size//2, 
                                 x+blood_size//2, y+blood_size//2], fill=blood_color)
            
            # Gotas goteando
            for i in range(random.randint(2, 4)):
                drip_x = x + random.randint(-15, 15)
                drip_y = y + random.randint(20, 80)
                drip_size = random.randint(8, 15)
                effects_draw.ellipse([drip_x-drip_size//2, drip_y, 
                                     drip_x+drip_size//2, drip_y+drip_size*2], fill=blood_color)
        
        # --- 4. Agregar salpicaduras de sangre aleatorias ---
        for _ in range(10):
            x = random.randint(0, frame_size[0])
            y = random.randint(0, frame_size[1])
            splatter_size = random.randint(5, 15)
            splatter_color = (120, 0, 0, random.randint(100, 180))
            effects_draw.ellipse([x-splatter_size//2, y-splatter_size//2,
                                 x+splatter_size//2, y+splatter_size//2], fill=splatter_color)
        
        # --- 5. Agregar grietas/rasgaduras ---
        for _ in range(5):
            start_x = random.randint(0, frame_size[0])
            start_y = random.randint(0, frame_size[1])
            end_x = start_x + random.randint(-30, 30)
            end_y = start_y + random.randint(-30, 30)
            crack_color = (15, 10, 10, 200)
            effects_draw.line([start_x, start_y, end_x, end_y], fill=crack_color, width=2)
        
        # --- 6. Colocar el QR en el centro del marco ---
        qr_position = ((frame_size[0] - qr_size[0]) // 2, (frame_size[1] - qr_size[1]) // 2)
        qr_with_effects.paste(qr_img, qr_position)
        
        # --- 7. Rotar todo el conjunto ligeramente ---
        qr_with_effects = qr_with_effects.rotate(4, expand=True, fillcolor=(0, 0, 0, 0))
        
        # --- 8. Posicionar en la imagen final ---
        qr_x = (background.width - qr_with_effects.width) // 2 + 31
        qr_y = int(background.height * 0.50)
        
        # 🧩 Combinar el QR con efectos en el fondo
        background.alpha_composite(qr_with_effects, (qr_x, qr_y))

        # --- Agregar texto ---
        draw = ImageDraw.Draw(background)
        
        # Cargar fuentes - probamos múltiples ubicaciones
        font_large = None
        font_medium = None
        font_small = None
        
        # Obtener directorio del proyecto
        project_dir = os.path.abspath(os.path.join(base_dir, '..', '..'))
        
        # Lista de fuentes a probar (incluye ruta del proyecto)
        # Primero intenta cargar fuentes personalizadas de terror/horror
        font_paths = [
            os.path.join(project_dir, 'static', 'fonts', 'Horror.ttf'),
            os.path.join(project_dir, 'static', 'fonts', 'Creepster.ttf'),
            os.path.join(project_dir, 'static', 'fonts', 'Arial-Bold.ttf'),
            os.path.join(project_dir, 'static', 'fonts', 'Arial.ttf'),
            "C:/Windows/Fonts/ariblk.ttf",  # Arial Black (más gruesa)
            "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "arial.ttf"
        ]
        
        for font_path in font_paths:
            try:
                # Tamaños más grandes
                font_large = ImageFont.truetype(font_path, 90)
                font_medium = ImageFont.truetype(font_path, 55)
                font_small = ImageFont.truetype(font_path, 32)
                print(f"✓ Fuente cargada: {font_path}")  # Debug
                break  # Si funciona, salir del bucle
            except Exception as e:
                continue
        
        # Si no se encontró ninguna fuente, usar load_default
        if font_large is None:
            print("⚠ No se encontró fuente TrueType, usando fuente por defecto")  # Debug
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # --- Texto "URUBO WEST" ---
        title_text = "URUBO WEST"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (background.width - title_width) // 2
        title_y = 80
        
        # Dibujar texto con efecto de sombra para simular el estilo del arte
        shadow_offset = 4
        draw.text((title_x + shadow_offset, title_y + shadow_offset), title_text, 
                 font=font_large, fill=(0, 0, 0, 200))  # Sombra más oscura
        draw.text((title_x, title_y), title_text, 
                 font=font_large, fill=(255, 255, 255, 255))  # Texto blanco

        # --- Fecha de la fiesta ---
        date_text = "1º de noviembre"
        date_bbox = draw.textbbox((0, 0), date_text, font=font_medium)
        date_width = date_bbox[2] - date_bbox[0]
        date_x = (background.width - date_width) // 2
        date_y = title_y + 120
        
        draw.text((date_x + shadow_offset, date_y + shadow_offset), date_text, 
                 font=font_medium, fill=(0, 0, 0, 200))  # Sombra más oscura
        draw.text((date_x, date_y), date_text, 
                 font=font_medium, fill=(255, 255, 255, 255))  # Texto blanco

        # --- Aviso sobre unicidad del ticket ---
        warning_text = "Este ticket es único y personal. Debe cuidarse y no compartirse."
        warning_bbox = draw.textbbox((0, 0), warning_text, font=font_small)
        warning_width = warning_bbox[2] - warning_bbox[0]
        warning_x = (background.width - warning_width) // 2
        warning_y = background.height - 120
        
        # Fondo semi-transparente para el aviso
        padding = 15
        warning_rect = [
            warning_x - padding, 
            warning_y - padding, 
            warning_x + warning_width + padding, 
            warning_y + 45 + padding
        ]
        draw.rectangle(warning_rect, fill=(0, 0, 0, 180))
        
        draw.text((warning_x, warning_y), warning_text, 
                 font=font_small, fill=(255, 255, 255, 255))

        # --- Guardar en memoria ---
        img_io = io.BytesIO()
        background.save(img_io, "PNG")
        img_io.seek(0)

        return send_file(img_io, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500