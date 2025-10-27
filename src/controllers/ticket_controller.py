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
        import requests
        from flask import send_file

        # --- Crear el código QR ---
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

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

        # --- Tamaño y posición del QR ---
        qr_size = (400, 400)
        qr_img = qr_img.resize(qr_size)

        # 🔄 Rotar en dirección opuesta (hacia la izquierda) sin fondo negro
        qr_img = qr_img.rotate(5.5, expand=True, fillcolor=(255, 255, 255, 0))

        # 📍 Posicionar más a la derecha
        qr_x = (background.width - qr_img.width) // 2 + 43
        qr_y = int(background.height * 0.49)

        # 🧩 Integración realista del QR con el fondo
        #    - Muestrea color promedio del área
        #    - Tinta el QR hacia los colores del fondo
        #    - Usa máscara para aplicar solo los módulos negros
        #    - Desenfoque suave para evitar bordes artificiales
        from PIL import ImageOps, ImageStat, ImageFilter

        # Región donde irá el QR
        region_box = (qr_x, qr_y, qr_x + qr_img.width, qr_y + qr_img.height)
        region = background.crop(region_box)

        # Color promedio del fondo en esa zona
        avg = tuple(int(v) for v in ImageStat.Stat(region.convert("RGB")).mean)

        def darker(color, factor=0.25):
            return tuple(max(0, min(255, int(c * factor))) for c in color)

        def slightly_lighter(color, factor=1.03):
            return tuple(max(0, min(255, int(c * factor))) for c in color)

        ink_color = darker(avg, 0.20)              # tinta (oscuro del fondo)
        paper_color = slightly_lighter(avg, 1.03)  # papel ligeramente más claro

        # Tinte del QR hacia los colores del fondo
        qr_gray = qr_img.convert("L")
        qr_tinted = ImageOps.colorize(qr_gray, black=ink_color, white=paper_color).convert("RGBA")

        # Borde y enfoque más natural
        qr_tinted = qr_tinted.filter(ImageFilter.GaussianBlur(0.6))

        # Máscara solo para módulos negros (evita pegar un rectángulo blanco)
        qr_mask = ImageOps.invert(qr_gray)
        qr_mask = qr_mask.filter(ImageFilter.GaussianBlur(0.4))

        # Componer sobre la región manteniendo textura y color del fondo
        region_with_qr = Image.composite(qr_tinted, region.convert("RGBA"), qr_mask)

        # Volver a colocar la región resultante en el fondo
        background.paste(region_with_qr, (qr_x, qr_y))

        # --- Agregar texto ---
        draw = ImageDraw.Draw(background)
        
        # Cargar fuentes - probamos múltiples ubicaciones
        font_large = None
        font_medium = None
        font_small = None
        
        # Obtener directorio del proyecto
        project_dir = os.path.abspath(os.path.join(base_dir, '..', '..'))
        
        # 💪 Cargar fuentes Anton (título bold) y Creepster (subtítulo)
        # IMPORTANTE: En Vercel (serverless), las fuentes DEBEN estar en el repositorio
        fonts_dir = os.path.join(project_dir, 'static', 'fonts')
        anton_path = os.path.join(fonts_dir, 'Anton-Regular.ttf')
        creepster_path = os.path.join(fonts_dir, 'Creepster-Regular.ttf')

        def find_font(font_name, primary_path):
            """Buscar fuente en múltiples rutas para compatibilidad"""
            if os.path.isfile(primary_path):
                return primary_path
            
            alternative_paths = [
                os.path.join('/var/task/static/fonts', font_name),
                os.path.join(base_dir, '..', '..', 'static', 'fonts', font_name),
                f'static/fonts/{font_name}',
            ]
            
            for alt_path in alternative_paths:
                if os.path.isfile(alt_path):
                    print(f"✓ {font_name} encontrada: {alt_path}")
                    return alt_path
            
            raise Exception(f"Fuente {font_name} no encontrada en static/fonts/")
        
        # Buscar ambas fuentes
        anton_path = find_font('Anton-Regular.ttf', anton_path)
        creepster_path = find_font('Creepster-Regular.ttf', creepster_path)

        # Cargar fuentes con tamaños específicos
        # Título: Anton 160pt | Subtítulo: Anton 60pt | Warning: Creepster 32pt
        try:
            title_font = ImageFont.truetype(anton_path, 160)      # URUBO WEST - Anton
            date_font = ImageFont.truetype(anton_path, 60)        # 1º DE NOVIEMBRE - Anton
            font_small = ImageFont.truetype(creepster_path, 32)   # Warning - Creepster
            print(f"✓ Fuentes cargadas:")
            print(f"  - Título: Anton 160pt (bold, condensed)")
            print(f"  - Subtítulo: Anton 60pt (bold, condensed)")
            print(f"  - Warning: Creepster 32pt")
        except Exception as e:
            print(f"❌ ERROR: No se pudieron cargar las fuentes: {e}")
            raise Exception(f"Error cargando fuentes: {e}")

        # --- Texto "URUBO WEST" con Anton 160pt (bold, condensed) y espaciado ---
        title_text = "URUBO WEST"
        
        # Crear capa temporal para aplicar desenfoque a la sombra
        temp_layer = Image.new('RGBA', background.size, (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_layer)
        
        # Calcular ancho con espaciado de letras (+5px según especificaciones)
        letter_spacing = 5
        title_width_with_spacing = 0
        for char in title_text:
            char_bbox = draw.textbbox((0, 0), char, font=title_font)
            char_width = char_bbox[2] - char_bbox[0]
            title_width_with_spacing += char_width + letter_spacing
        title_width_with_spacing -= letter_spacing  # Quitar espaciado extra del último carácter
        
        title_x = (background.width - title_width_with_spacing) // 2
        title_y = 80
        
        # Dibujar sombra suave con desenfoque (especificaciones: desplazamiento 2px, desenfoque 4px, opacidad 60%)
        shadow_offset = 2
        current_x_shadow = title_x
        for char in title_text:
            temp_draw.text((current_x_shadow + shadow_offset, title_y + shadow_offset), char, 
                         font=title_font, fill=(0, 0, 0, 153))  # Opacidad 60% = 153
            char_bbox = draw.textbbox((0, 0), char, font=title_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_shadow += char_width + letter_spacing
        
        # Aplicar desenfoque gaussiano a la sombra
        temp_layer = temp_layer.filter(ImageFilter.GaussianBlur(4))
        background = Image.alpha_composite(background, temp_layer)
        draw = ImageDraw.Draw(background)
        
        # Dibujar texto principal con espaciado (blanco puro #FFFFFF)
        current_x = title_x
        for char in title_text:
            draw.text((current_x, title_y), char, 
                     font=title_font, fill=(255, 255, 255, 255))  # Blanco puro
            char_bbox = draw.textbbox((0, 0), char, font=title_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x += char_width + letter_spacing

        # --- Subtítulo "1º DE NOVIEMBRE" con Anton 60pt ---
        date_text = "1º DE NOVIEMBRE"
        
        # Crear capa temporal para sombra del subtítulo
        temp_layer_date = Image.new('RGBA', background.size, (0, 0, 0, 0))
        temp_draw_date = ImageDraw.Draw(temp_layer_date)
        
        # Calcular ancho con espaciado de letras (+5px, igual que el título)
        date_width_with_spacing = 0
        for char in date_text:
            char_bbox = draw.textbbox((0, 0), char, font=date_font)
            char_width = char_bbox[2] - char_bbox[0]
            date_width_with_spacing += char_width + letter_spacing
        date_width_with_spacing -= letter_spacing
        
        date_x = (background.width - date_width_with_spacing) // 2
        date_y = title_y + 180  # Espaciado vertical aumentado para dar más espacio entre título y subtítulo
        
        # Dibujar sombra suave para subtítulo (mismo estilo que título)
        current_x_shadow_date = date_x
        for char in date_text:
            temp_draw_date.text((current_x_shadow_date + shadow_offset, date_y + shadow_offset), char, 
                               font=date_font, fill=(0, 0, 0, 153))  # Opacidad 60%
            char_bbox = draw.textbbox((0, 0), char, font=date_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_shadow_date += char_width + letter_spacing
        
        # Aplicar desenfoque gaussiano a la sombra del subtítulo
        temp_layer_date = temp_layer_date.filter(ImageFilter.GaussianBlur(4))
        background = Image.alpha_composite(background, temp_layer_date)
        draw = ImageDraw.Draw(background)
        
        # Dibujar subtítulo con espaciado (blanco puro #FFFFFF)
        current_x_date = date_x
        for char in date_text:
            draw.text((current_x_date, date_y), char, 
                     font=date_font, fill=(255, 255, 255, 255))  # Blanco puro
            char_bbox = draw.textbbox((0, 0), char, font=date_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_date += char_width + letter_spacing

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