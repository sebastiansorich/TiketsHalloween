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

def generate_invitation_with_qr(token, options=None):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import qrcode, os, io
        from flask import send_file

        # --- Opciones de ajuste (parametrización para móviles y diseño) ---
        opts = options or {}
        # Resolución/ratio objetivo (por defecto 1080x1920, 9:16)
        target_width = int(opts.get('output_width', 1080))
        target_height = int(opts.get('output_height', 1920))
        target_ratio = float(opts.get('target_ratio', target_width / target_height))

        # Archivos/recursos
        base_dir = os.path.abspath(os.path.dirname(__file__))
        background_filename = opts.get('background_filename', 'invitation_background.png')
        image_path = os.path.join(base_dir, '..', '..', 'static', background_filename)

        # QR y texto
        qr_size = tuple(opts.get('qr_size', (400, 400)))
        qr_angle_deg = float(opts.get('qr_angle', 5.5))
        qr_offset_x = int(opts.get('qr_offset_x', 52))
        qr_y_absolute = opts.get('qr_y')
        qr_y_factor = float(opts.get('qr_y_factor', 0.50))

        # Tipografías y posiciones
        title_size = int(opts.get('title_font_size', 120))
        date_size = int(opts.get('date_font_size', 60))
        warning_size = int(opts.get('warning_font_size', 50))
        entry_font_size = int(opts.get('entry_font_size', 110))
        letter_spacing = int(opts.get('letter_spacing', 0))
        title_y_pos = int(opts.get('title_y', 80))
        date_gap_y = int(opts.get('date_gap_y', 140))
        entry_offset_right = int(opts.get('entry_offset_right', 32))
        entry_above_qr_px = int(opts.get('entry_above_qr_px',200))
        pass_gap_px = int(opts.get('pass_gap_px', 100))

        # Warning (aviso)
        warning_margin_bottom = int(opts.get('warning_margin_bottom', 40))
        warning_padding_x = int(opts.get('warning_padding_x', 20))
        warning_padding_y = int(opts.get('warning_padding_y', 14))
        jpeg_quality = int(opts.get('jpeg_quality', 95))

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
        background = Image.open(image_path).convert("RGBA")

        # --- Ajustar proporción para móviles (por defecto 9:16) ---
        mobile_ratio = target_ratio
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

        # --- Redimensionar a la resolución objetivo ---
        background = background.resize((target_width, target_height))

        # --- Tamaño y posición del QR ---
        qr_img = qr_img.resize(qr_size)

        # 🔄 Rotar en dirección opuesta (hacia la izquierda) sin fondo negro
        qr_img = qr_img.rotate(qr_angle_deg, expand=True, fillcolor=(255, 255, 255, 0))

        # 📍 Posicionar más a la derecha
        qr_x = (background.width - qr_img.width) // 2 + qr_offset_x
        qr_y = int(background.height * qr_y_factor) if qr_y_absolute is None else int(qr_y_absolute)

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
            title_font = ImageFont.truetype(dmserif_path, title_size)   # URUBO WEST - DM Serif Display
            date_font = ImageFont.truetype(dmserif_path, date_size)     # 1º DE NOVIEMBRE - DM Serif Display
            font_small = ImageFont.truetype(dmserif_path, warning_size) # Warning - DM Serif Display
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
        
        # Calcular ancho con espaciado de letras
        title_width_with_spacing = 0
        for char in title_text:
            char_bbox = draw.textbbox((0, 0), char, font=title_font)
            char_width = char_bbox[2] - char_bbox[0]
            title_width_with_spacing += char_width + letter_spacing
        title_width_with_spacing -= letter_spacing  # Quitar espaciado extra del último carácter
        
        title_x = (background.width - title_width_with_spacing) // 2
        title_y = title_y_pos
        
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
        date_y = title_y + date_gap_y  # Espaciado vertical configurable
        
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

        # ENTRY PASS deshabilitado a pedido

        # --- Aviso sobre unicidad del ticket ---
        warning_text = "Esta imagen es única y personal. No debe ser compartida."

        # Envoltura robusta: medir ancho por línea con textbbox (sin usar APIs nuevas)
        max_text_width = background.width - 80
        words = warning_text.split(" ")
        lines = []
        current_line = ""
        spacing = 6

        def measure(text):
            bbox = draw.textbbox((0, 0), text, font=font_small)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])

        for word in words:
            candidate = word if current_line == "" else f"{current_line} {word}"
            cand_w, _ = measure(candidate)
            if cand_w <= max_text_width:
                current_line = candidate
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        line_sizes = [measure(line) for line in lines]
        block_width = max((w for w, h in line_sizes), default=0)
        block_height = sum((h for w, h in line_sizes)) + spacing * (len(lines) - 1 if lines else 0)

        warning_x = (background.width - block_width) // 2
        warning_y = background.height - (block_height + warning_margin_bottom)

        # Fondo semi-transparente con padding
        padding_x = warning_padding_x
        padding_y = warning_padding_y
        warning_rect = [
            warning_x - padding_x,
            warning_y - padding_y,
            warning_x + block_width + padding_x,
            warning_y + block_height + padding_y,
        ]
        draw.rectangle(warning_rect, fill=(0, 0, 0, 220))

        # Dibujar líneas centradas
        y_cursor = warning_y
        for (line, (line_w, line_h)) in zip(lines, line_sizes):
            line_x = (background.width - line_w) // 2
            draw.text((line_x, y_cursor), line, font=font_small, fill=(255, 255, 255, 255))
            y_cursor += line_h + spacing

        # --- Convertir a RGB para JPEG (JPEG no soporta transparencia) ---
        # Crear fondo blanco para reemplazar transparencia
        rgb_background = Image.new('RGB', background.size, (255, 255, 255))
        rgb_background.paste(background, mask=background.split()[-1])  # Usar canal alpha como máscara
        
        # --- Guardar en memoria como JPEG con alta calidad ---
        img_io = io.BytesIO()
        rgb_background.save(img_io, "JPEG", quality=jpeg_quality, optimize=True)
        img_io.seek(0)

        return send_file(img_io, mimetype="image/jpeg")

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500