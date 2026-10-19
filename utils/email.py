# utils/email.py
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr
from flask import url_for
from html import escape
from urllib.parse import urlsplit
from flask import current_app

# --- PLANTILLA BASE HTML PARA CORREOS (DISEÑO UNIFICADO) ---
def get_email_template(titulo, contenido):
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; max-width: 600px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; margin: 0 auto;">
        <div style="background-color: #275c80; padding: 20px; text-align: center;">
            <h2 style="color: white; margin: 0; font-size: 20px;">{titulo}</h2>
        </div>
        <div style="padding: 20px; background-color: #ffffff;">
            {contenido}
        </div>
        <div style="background-color: #f1f1f1; padding: 15px; text-align: center; font-size: 11px; color: #888; border-top: 1px solid #eee;">
            <p style="margin: 0;">Red de Atención Primaria de Salud Municipal - Alto Hospicio</p>
            <p style="margin: 5px 0 0;">Este es un mensaje automático, por favor no responder.</p>
        </div>
    </div>
    """

def enviar_correo_generico(destinatarios, asunto, cuerpo_html, adjunto_path=None, bcc=None):
    """
    Envía un correo utilizando SMTP (Gmail) de forma segura y consistente.
    """
    remitente = os.getenv("EMAIL_USUARIO")
    contrasena = os.getenv("EMAIL_CONTRASENA")

    # Validación mínima de credenciales
    if not remitente or not contrasena:
        print("ERROR: Faltan credenciales EMAIL_USUARIO / EMAIL_CONTRASENA en .env")
        return False

    # 1) Normalizar inputs a listas
    if destinatarios is None:
        destinatarios = []
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]

    if bcc is None:
        bcc = []
    if isinstance(bcc, str):
        bcc = [bcc]

    # 2) Limpiar vacíos/None y quitar duplicados (orden)
    destinatarios = [d.strip() for d in destinatarios if d and str(d).strip()]
    bcc = [d.strip() for d in bcc if d and str(d).strip()]

    # Deduplicar manteniendo el orden
    destinatarios = list(dict.fromkeys(destinatarios))
    bcc = list(dict.fromkeys(bcc))

    # 3) Construir el mensaje (headers visibles)
    if not destinatarios and not bcc:
        print("ERROR: Faltan destinatarios (To/Bcc).")
        return False

    msg = MIMEMultipart()
    msg["Subject"] = asunto
    msg["From"] = formataddr(("Portal de Acceso", remitente))
    msg["To"] = ", ".join(destinatarios) if destinatarios else remitente

    # Cuerpo HTML
    msg.attach(MIMEText(cuerpo_html, "html"))

    # Adjuntar archivo si corresponde
    if adjunto_path and os.path.exists(adjunto_path):
        try:
            with open(adjunto_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(adjunto_path))
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(adjunto_path)}"'
                msg.attach(part)
        except Exception as e:
            print(f"Error adjuntando archivo: {e}")

    # 4) Enviar: definimos explícitamente el "sobre" (envelope SMTP)
    recipients = []
    if destinatarios:
        recipients.extend(destinatarios)
    else:
        recipients.append(remitente)

    if bcc:
        recipients.extend(bcc)

    # Deduplicar recipients por si se repiten
    recipients = list(dict.fromkeys([r for r in recipients if r]))

    try:
        import ssl
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(remitente, contrasena)
            server.send_message(
                msg,
                from_addr=remitente,
                to_addrs=recipients
            )
        return True

    except Exception as e:
        print(f"Error enviando correo '{asunto}': {e}")
        return False

# --- FUNCIONES ESPECÍFICAS DE NOTIFICACIÓN ---

def _url_publica(endpoint, **values):
    """Usa un origen configurado, nunca Host proporcionado por la solicitud."""
    base = os.getenv('PORTAL_BASE_URL', '').rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError('Configura PORTAL_BASE_URL (origen HTTP(S) confiable) en .env')
    if not current_app.debug and parsed.scheme != 'https':
        raise RuntimeError('Se requiere HTTPS para enviar enlaces fuera de desarrollo')
    return base + url_for(endpoint, **values)


def enviar_correo_reseteo(usuario, token):
    try:
        url = _url_publica('auth.resetear_clave', token=token)
    except RuntimeError as exc:
        current_app.logger.error('Configuración correo: %s', exc)
        return False
    nombre = escape(usuario.nombre_completo)
    contenido = f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Recibimos una solicitud de recuperación de contraseña del Portal de Acceso.</p>
        <p><a href="{escape(url, quote=True)}">Restablecer contraseña</a></p>
        <p>Este enlace expira en una hora y puede utilizarse una sola vez.</p>
    """
    return enviar_correo_generico(usuario.email, 'Recuperación de contraseña - Portal de Acceso',
                                 get_email_template('Recuperación de contraseña', contenido))


def enviar_activacion_usuario(usuario, token):
    try:
        url = _url_publica('auth.activar_cuenta', token=token)
    except RuntimeError as exc:
        current_app.logger.error('Configuración correo: %s', exc)
        return False
    nombre = escape(usuario.nombre_completo)
    contenido = f"""
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Se creó tu cuenta en el Portal de Acceso Institucional.</p>
        <p><a href="{escape(url, quote=True)}">Establecer mi contraseña</a></p>
        <p>El enlace expira en 24 horas y solo puede utilizarse una vez.</p>
    """
    return enviar_correo_generico(usuario.email, 'Activa tu cuenta - Portal de Acceso',
                                 get_email_template('Activa tu cuenta', contenido))
