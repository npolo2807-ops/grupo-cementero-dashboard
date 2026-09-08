#!/usr/bin/env python3
"""Envía el email diario de resumen del dashboard."""
import json, os, sys, smtplib, traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

GMAIL_USER     = os.environ['GMAIL_USER']
GMAIL_APP_PASS = os.environ['GMAIL_APP_PASS']
EMAIL_TO       = os.environ.get('EMAIL_TO', 'manuelpolo@npgservices.com')
EMAIL_CC       = os.environ.get('EMAIL_CC', 'npolo2807@gmail.com')

def enviar_alerta_error(paso, error_msg):
    """Manda email de alerta si falla algo crítico."""
    try:
        if not GMAIL_USER or not GMAIL_APP_PASS:
            return
        fecha_hoy = date.today().isoformat()
        subject = f'🚨 ERROR Dashboard Grupo Cementero — {fecha_hoy}'
        html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:#b71c1c;padding:16px 20px;border-radius:8px 8px 0 0;">
    <div style="color:white;font-size:17px;font-weight:bold;">🚨 Error en el dashboard diario</div>
    <div style="color:#ffcdd2;font-size:12px;margin-top:4px;">{fecha_hoy}</div>
  </div>
  <div style="background:#fff3f3;border:1px solid #ffcdd2;border-top:none;border-radius:0 0 8px 8px;padding:20px;">
    <p style="margin:0 0 12px;"><strong>Paso donde falló:</strong> {paso}</p>
    <pre style="background:#f5f5f5;border:1px solid #ddd;border-radius:4px;padding:12px;
                font-size:12px;overflow:auto;white-space:pre-wrap;">{error_msg}</pre>
    <p style="margin:16px 0 0;font-size:13px;color:#666;">
      Es posible que el email de resumen no haya llegado hoy.<br>
      Revisa el log completo en:
      <a href="https://github.com/npolo2807-ops/grupo-cementero-dashboard/actions">GitHub Actions</a>
    </p>
  </div>
</body></html>"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = GMAIL_USER
        msg['To']      = EMAIL_CC
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASS)
            smtp.sendmail(GMAIL_USER, [EMAIL_CC], msg.as_string())
        print(f'📧 Alerta de error enviada a {EMAIL_CC}')
    except Exception as e2:
        print(f'⚠ No se pudo enviar alerta: {e2}')

try:
    # Leer datos generados
    with open('datos.json', encoding='utf-8') as f:
        d = json.load(f)

    kpi = d['kpi']
    TOTAL    = kpi['total']
    DONE     = kpi['done']
    DELAYED  = kpi['delayed']
    PCT      = kpi['pct']
    FECHA    = d['fecha']
    PERIODO  = d['periodo']

    subject = f"Informe diario — {FECHA} | Grupo Cementero"

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:#1a237e;padding:20px 24px;border-radius:8px 8px 0 0;">
    <div style="color:#90caf9;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Informe diario · Grupo Cementero</div>
    <div style="color:white;font-size:18px;font-weight:500;">{FECHA}</div>
  </div>
  <div style="background:#f9f9f9;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;padding:24px;">
    <p style="font-size:15px;line-height:1.7;margin:0 0 1.2rem;">Buenos días, equipo.</p>
    <p style="font-size:15px;line-height:1.7;margin:0 0 1.2rem;">
      Resumen operativo del día de hoy, <strong>{FECHA}</strong>, período <strong>{PERIODO}</strong>.
    </p>
    <div style="background:#f0f0f0;border-radius:10px;padding:16px;margin:1.2rem 0;">
      <div style="font-size:11px;color:#888;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">Puntos clave</div>
      <div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:10px;">
        <span style="color:#4caf50;font-size:18px;">✓</span>
        <span style="font-size:14px;line-height:1.5;">
          La flota completó <strong>{DONE} de {TOTAL} entregas</strong> — cumplimiento del <strong>{PCT}%</strong>.
        </span>
      </div>
      <div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:10px;">
        <span style="color:#ff9800;font-size:18px;">⚠</span>
        <span style="font-size:14px;line-height:1.5;">
          <strong>{DELAYED} tareas registraron retraso.</strong> Revisa el dashboard para el detalle por zona.
        </span>
      </div>
      <div style="display:flex;gap:8px;align-items:flex-start;">
        <span style="color:#2196f3;font-size:18px;">→</span>
        <span style="font-size:14px;line-height:1.5;">Datos actualizados a las <strong>7:00 AM</strong>.</span>
      </div>
    </div>
    <div style="text-align:center;margin:1.5rem 0;">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center"><tr>
        <td bgcolor="#0288D1" style="background-color:#0288D1;border-radius:8px;padding:14px 32px;">
          <a href="https://grupocementero.npgservices.com" target="_blank"
             style="color:#ffffff;text-decoration:none;font-size:15px;font-weight:bold;font-family:Arial,sans-serif;display:inline-block;color:#ffffff;">
            🔗 Ver dashboard completo →
          </a>
        </td>
      </tr></table>
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = GMAIL_USER
    msg['To']      = EMAIL_TO
    msg['Cc']      = EMAIL_CC
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASS)
        smtp.sendmail(GMAIL_USER, [EMAIL_TO, EMAIL_CC], msg.as_string())

    print(f'✅ Email enviado a {EMAIL_TO}, CC {EMAIL_CC}')

except Exception as e:
    tb = traceback.format_exc()
    print(f'❌ ERROR al enviar email: {e}\n{tb}')
    enviar_alerta_error('Envío de email diario (enviar_email.py)', tb)
    sys.exit(1)
