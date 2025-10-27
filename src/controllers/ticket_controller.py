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

        # --- Ajustar proporción para móviles (9:16 es ideal para pantallas móviles) ---
        mobile_ratio = 9 / 16  # Proporción vertical para móviles
        bg_width, bg_height = background.size
        current_ratio = bg_width / bg_height

        if current_ratio > mobile_ratio:
            # Si es más ancho que móvil, recortar los lados
            new_width = int(bg_height * mobile_ratio)
            left = (bg_width - new_width) // 2
            background = background.crop((left, 0, left + new_width, bg_height))
        elif current_ratio < mobile_ratio:
            # Si es más alto que móvil, recortar arriba y abajo
            new_height = int(bg_width / mobile_ratio)
            top = (bg_height - new_height) // 2
            background = background.crop((0, top, bg_width, top + new_height))

        # --- Redimensionar para móviles (1080x1920 es Full HD móvil) ---
        background = background.resize((1080, 1920))

        # --- Tamaño y posición del QR ---
        qr_size = (400, 400)
        qr_img = qr_img.resize(qr_size)

        # 🔄 Rotar en dirección opuesta (hacia la izquierda) sin fondo negro
        qr_img = qr_img.rotate(5.5, expand=True, fillcolor=(255, 255, 255, 0))

        # 📍 Posicionar más a la derecha
        qr_x = (background.width - qr_img.width) // 2 + 43
        qr_y = int(background.height * 0.60)

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
        
        # 📚 Cargar fuente DM Serif Display para título, subtítulo y warning
        # IMPORTANTE: En Vercel (serverless), las fuentes DEBEN estar en el repositorio
        fonts_dir = os.path.join(project_dir, 'static', 'fonts')
        dmserif_path = os.path.join(fonts_dir, 'DMSerifDisplay-Regular.ttf')

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
        
        # Buscar fuente DM Serif Display
        dmserif_path = find_font('DMSerifDisplay-Regular.ttf', dmserif_path)

        # Cargar fuentes con tamaños específicos
        # Título: DM Serif Display 160pt | Subtítulo: DM Serif Display 60pt | Warning: DM Serif Display 32pt
        try:
            title_font = ImageFont.truetype(dmserif_path, 120)   # URUBO WEST - DM Serif Display
            date_font = ImageFont.truetype(dmserif_path, 60)     # 1º DE NOVIEMBRE - DM Serif Display
            font_small = ImageFont.truetype(dmserif_path, 50)    # Warning - DM Serif Display
            print(f"✓ Fuentes cargadas:")
            print(f"  - Título: DM Serif Display 160pt (elegante, serif)")
            print(f"  - Subtítulo: DM Serif Display 60pt (elegante, serif)")
            print(f"  - Warning: DM Serif Display 32pt (elegante, serif)")
        except Exception as e:
            print(f"❌ ERROR: No se pudieron cargar las fuentes: {e}")
            raise Exception(f"Error cargando fuentes: {e}")

        # --- Texto "URUBO WEST" con DM Serif Display 160pt y espaciado ---
        title_text = "URUBO WEST"
        
        # Crear capa temporal para aplicar desenfoque a la sombra
        temp_layer = Image.new('RGBA', background.size, (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_layer)
        
        # Calcular ancho con espaciado de letras (+5px según especificaciones)
        letter_spacing = 0
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

        # --- Subtítulo "1º DE NOVIEMBRE" con DM Serif Display 60pt ---
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
        date_y = title_y + 140  # Espaciado vertical aumentado para dar más espacio entre título y subtítulo
        
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

        # --- Texto "ENTRY PASS" en rojo arriba del QR (dividido en dos líneas) ---
        entry_text = "ENTRY"
        pass_text = " PASS"
        
        # Crear fuente más grande para ENTRY PASS (usando date_font que es más grande)
        entry_font = ImageFont.truetype(dmserif_path, 70)     # Más grande que font_small (40)
        
        # Calcular ancho de cada línea con espaciado de letras (+5px, igual que otros textos)
        entry_width_with_spacing = 0
        for char in entry_text:
            char_bbox = draw.textbbox((0, 0), char, font=entry_font)
            char_width = char_bbox[2] - char_bbox[0]
            entry_width_with_spacing += char_width + letter_spacing
        entry_width_with_spacing -= letter_spacing
        
        pass_width_with_spacing = 0
        for char in pass_text:
            char_bbox = draw.textbbox((0, 0), char, font=entry_font)
            char_width = char_bbox[2] - char_bbox[0]
            pass_width_with_spacing += char_width + letter_spacing
        pass_width_with_spacing -= letter_spacing
        
        # Usar el ancho mayor para centrar ambas líneas
        max_width = max(entry_width_with_spacing, pass_width_with_spacing)
        
        entry_x = (background.width - max_width) // 2 + 8  # +8px hacia la derecha
        entry_y = qr_y - 50  # +60px hacia arriba
        pass_y = entry_y + 30  # 70px debajo de ENTRY
        
        # Calcular el espacio necesario para el texto rotado
        # Con rotación de 5.5 grados, necesitamos más espacio horizontal
        import math
        rotation_angle = math.radians(5.5)
        
        # Calcular el ancho total del texto (ENTRY + PASS)
        total_text_width = max(entry_width_with_spacing, pass_width_with_spacing)
        total_text_height = 100  # Espacio aproximado para ambas líneas
        
        # Calcular las dimensiones después de la rotación
        rotated_width = int(abs(total_text_width * math.cos(rotation_angle)) + abs(total_text_height * math.sin(rotation_angle)))
        rotated_height = int(abs(total_text_width * math.sin(rotation_angle)) + abs(total_text_height * math.cos(rotation_angle)))
        
        # Crear imagen temporal con espacio suficiente para la rotación
        temp_size = (background.width + rotated_width + 100, background.height + rotated_height + 100)
        temp_layer_entry = Image.new('RGBA', temp_size, (0, 0, 0, 0))
        temp_draw_entry = ImageDraw.Draw(temp_layer_entry)
        
        # Centrar el texto en la imagen temporal
        temp_entry_x = (temp_size[0] - total_text_width) // 2
        temp_entry_y = (temp_size[1] - total_text_height) // 2
        
        # Dibujar sombra suave para ENTRY (primera línea)
        current_x_shadow_entry = temp_entry_x
        for char in entry_text:
            temp_draw_entry.text((current_x_shadow_entry + shadow_offset, temp_entry_y + shadow_offset), char, 
                               font=entry_font, fill=(0, 0, 0, 153))  # Opacidad 60%
            char_bbox = draw.textbbox((0, 0), char, font=entry_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_shadow_entry += char_width + letter_spacing
        
        # Dibujar sombra suave para PASS (segunda línea)
        temp_pass_y = temp_entry_y + 30  # 30px debajo de ENTRY (ajustado según tus cambios)
        current_x_shadow_pass = temp_entry_x
        for char in pass_text:
            temp_draw_entry.text((current_x_shadow_pass + shadow_offset, temp_pass_y + shadow_offset), char, 
                               font=entry_font, fill=(0, 0, 0, 153))  # Opacidad 60%
            char_bbox = draw.textbbox((0, 0), char, font=entry_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_shadow_pass += char_width + letter_spacing
        
        # Aplicar desenfoque gaussiano a la sombra del ENTRY PASS
        temp_layer_entry = temp_layer_entry.filter(ImageFilter.GaussianBlur(4))
        
        # Rotar la capa de sombra con la misma inclinación que el QR (5.5 grados)
        temp_layer_entry = temp_layer_entry.rotate(5.5, expand=True, fillcolor=(255, 255, 255, 0))
        
        # Recortar la imagen rotada al tamaño original y pegar en la posición correcta
        final_width, final_height = temp_layer_entry.size
        crop_x = (final_width - background.width) // 2
        crop_y = (final_height - background.height) // 2
        temp_layer_entry = temp_layer_entry.crop((crop_x, crop_y, crop_x + background.width, crop_y + background.height))
        
        # Componer la sombra rotada
        background = Image.alpha_composite(background, temp_layer_entry)
        draw = ImageDraw.Draw(background)
        
        # Crear capa temporal para el texto principal (mismo tamaño que la sombra)
        temp_layer_text = Image.new('RGBA', temp_size, (0, 0, 0, 0))
        temp_draw_text = ImageDraw.Draw(temp_layer_text)
        
        # Dibujar ENTRY con espaciado (rojo #FF0000) - primera línea
        current_x_entry = temp_entry_x
        for char in entry_text:
            temp_draw_text.text((current_x_entry, temp_entry_y), char, 
                              font=entry_font, fill=(255, 0, 0, 255))  # Rojo puro
            char_bbox = draw.textbbox((0, 0), char, font=entry_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_entry += char_width + letter_spacing
        
        # Dibujar PASS con espaciado (rojo #FF0000) - segunda línea
        temp_pass_y = temp_entry_y + 30  # 30px debajo de ENTRY (ajustado según tus cambios)
        current_x_pass = temp_entry_x
        for char in pass_text:
            temp_draw_text.text((current_x_pass, temp_pass_y), char, 
                              font=entry_font, fill=(255, 0, 0, 255))  # Rojo puro
            char_bbox = draw.textbbox((0, 0), char, font=entry_font)
            char_width = char_bbox[2] - char_bbox[0]
            current_x_pass += char_width + letter_spacing
        
        # Rotar el texto principal con la misma inclinación que el QR (5.5 grados)
        temp_layer_text = temp_layer_text.rotate(5.5, expand=True, fillcolor=(255, 255, 255, 0))
        
        # Recortar la imagen rotada al tamaño original y pegar en la posición correcta
        final_width, final_height = temp_layer_text.size
        crop_x = (final_width - background.width) // 2
        crop_y = (final_height - background.height) // 2
        temp_layer_text = temp_layer_text.crop((crop_x, crop_y, crop_x + background.width, crop_y + background.height))
        
        # Componer el texto rotado
        background = Image.alpha_composite(background, temp_layer_text)
        draw = ImageDraw.Draw(background)

        # --- Aviso sobre unicidad del ticket ---
        warning_text = "Esta imagen es única y personal, no debe ser compartida."
        warning_bbox = draw.textbbox((0, 0), warning_text, font=font_small)
        warning_width = warning_bbox[2] - warning_bbox[0]
        warning_x = (background.width - warning_width) // 2
        warning_y = background.height - 80  # Ajustado para móviles (menos margen)
        
        # Fondo semi-transparente para el aviso
        padding = 15
        warning_rect = [
            warning_x - padding, 
            warning_y - padding, 
            warning_x + warning_width + padding, 
            warning_y + 45 + padding
        ]
        draw.rectangle(warning_rect, fill=(0, 0, 0, 220))
        
        draw.text((warning_x, warning_y), warning_text, 
                 font=font_small, fill=(255, 255, 255, 255))

        # --- Convertir a RGB para JPEG (JPEG no soporta transparencia) ---
        # Crear fondo blanco para reemplazar transparencia
        rgb_background = Image.new('RGB', background.size, (255, 255, 255))
        rgb_background.paste(background, mask=background.split()[-1])  # Usar canal alpha como máscara
        
        # --- Guardar en memoria como JPEG con alta calidad ---
        img_io = io.BytesIO()
        rgb_background.save(img_io, "JPEG", quality=95, optimize=True)
        img_io.seek(0)

        return send_file(img_io, mimetype="image/jpeg")

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500