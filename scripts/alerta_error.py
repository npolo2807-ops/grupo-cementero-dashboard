#!/usr/bin/env python3
"""Manda email de alerta cuando el workflow de GitHub Actions falla."""
import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

GMAIL_USER     = os.environ.get('GMAIL_USER', '')
GMAIL_APP_PASS = os.environ.get('GMAIL_APP_PASS', '')
EMAIL_CC       = os.environ.get('EMAIL_CC', 'npolo2807@gmail.com')
RUN_URL        = os.environ.get('GITHUB_RUN_URL', 'https://github.com/npolo2807-ops/grupo-cementero-dashboard/actions')

if not GMAIL_USER or not GMAIL_APP_PASS:
    print('Sin credenciales Gmail — no se puede enviar alerta')
    exit(0)

fecha = date.today().strftime('%d/%m/%Y')
subject = f'🚨 ERROR Dashboard Grupo Cementero — {fecha}'

html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:#b71c1c;padding:16px 20px;border-radius:8px 8px 0 0;">
    <div style="color:white;font-size:18px;font-weight:bold;">🚨 El dashboard falló hoy</div>
    <div style="color:#ffcdd2;font-size:13px;margin-top:4px;">{fecha}</div>
  </div>
  <div style="background:#fff8f8;border:1px solid #ffcdd2;border-top:none;border-radius:0 0 8px 8px;padding:24px;">
    <p style="margin:0 0 16px;font-size:15px;">
      El proceso automático del dashboard <strong>no se completó correctamente</strong> hoy.
      Es posible que el email de resumen no haya llegado y que los datos no estén actualizados.
    </p>
    <div style="text-align:center;margin:20px 0;">
      <a href="{RUN_URL}" target="_blank"
         style="background:#1565C0;color:white;text-decoration:none;padding:12px 28px;
                border-radius:6px;font-weight:bold;font-size:14px;display:inline-block;">
        Ver log de error en GitHub →
      </a>
    </div>
    <p style="margin:16px 0 0;font-size:12px;color:#888;">
      Este mensaje es automático. Revisa el log para ver el error exacto.
    </p>
  </div>
</body></html>"""

msg = MIMEMultipart('alternative')
msg['Subject'] = subject
msg['From']    = GMAIL_USER
msg['To']      = EMAIL_CC
msg.attach(MIMEText(html, 'html'))

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASS)
        smtp.sendmail(GMAIL_USER, [EMAIL_CC], msg.as_string())
    print(f'Alerta enviada a {EMAIL_CC}')
except Exception as e:
    print(f'No se pudo enviar alerta: {e}')
