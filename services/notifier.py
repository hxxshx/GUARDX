"""
GuardX — External Notification Service (Layer 8)

Handles dispatching critical alerts to external systems:
- Email (smtplib)
- SMS & WhatsApp (Twilio)
- Hardware Buzzer (MQTT + Winsound)
"""

import os
import smtplib
from email.mime.text import MIMEText
import logging
from config import (
    NOTIFICATIONS_ENABLED, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS,
    ALERT_EMAIL_RECIPIENT, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, 
    TWILIO_PHONE_NUMBER, ALERT_PHONE_RECIPIENT, MQTT_BUZZER_TOPIC
)

logger = logging.getLogger("Notifier")

def trigger_alert(alert_type: str, severity: str, message: str, health_score: float):
    """
    Central dispatch for external notifications.
    Called by health_engine.py whenever a critical database alert is generated.
    """
    if not NOTIFICATIONS_ENABLED:
        return
        
    print(f"\n[NOTIFIER] Dispatching {severity.upper()} external alerts...")
    
    # 1. Hardware Buzzer Trigger
    _trigger_buzzer()
    
    # 2. Email Alert
    _send_email(alert_type, severity, message, health_score)
    
    # 3. SMS/WhatsApp Alert
    _send_twilio_alert(severity, message)


def _trigger_buzzer():
    """Trigger the physical Windows motherboard speaker and publish to MQTT."""
    try:
        # Local Windows Buzzer (for demonstration without an Arduino)
        import winsound
        # High-pitch beep pattern: frequency, duration(ms)
        winsound.Beep(2500, 200)
        winsound.Beep(2500, 200)
        winsound.Beep(2500, 600)
        print("[NOTIFIER] -> Winsound Buzzer Triggered")
        
        # MQTT Factory Buzzer (for real edge deployments)
        import paho.mqtt.publish as publish
        publish.single(MQTT_BUZZER_TOPIC, payload="BEEP", hostname="localhost")
        print("[NOTIFIER] -> MQTT Buzzer command published")
    except Exception as e:
        print(f"[NOTIFIER ERROR] Failed to trigger buzzer: {e}")


def _send_email(alert_type: str, severity: str, message: str, health_score: float):
    """Send an SMTP email alert."""
    if not SMTP_USER or not SMTP_PASS:
        print("[NOTIFIER] -> Email skipped (SMTP Auth not configured in .env)")
        return
        
    try:
        msg = MIMEText(f"GuardX Automated Alert\n\nAlert Type: {alert_type}\nSeverity: {severity}\nHealth: {health_score}%\n\nDetails: {message}")
        msg['Subject'] = f"[GuardX {severity.upper()}] Machine Degredation Detected"
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL_RECIPIENT

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            
        print(f"[NOTIFIER] -> Email sent to {ALERT_EMAIL_RECIPIENT}")
    except Exception as e:
        print(f"[NOTIFIER ERROR] Failed to send email: {e}")


def _send_twilio_alert(severity: str, message: str):
    """Send SMS and WhatsApp using Twilio API."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not ALERT_PHONE_RECIPIENT:
        print("[NOTIFIER] -> Twilio SMS/WhatsApp skipped (Keys not configured in .env)")
        return
        
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        body = f"GuardX [{severity.upper()}]: {message}"
        
        # Dispatch SMS
        message_sms = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=ALERT_PHONE_RECIPIENT
        )
        print(f"[NOTIFIER] -> SMS sent (SID: {message_sms.sid})")
        
        # Dispatch WhatsApp
        message_wa = client.messages.create(
            body=body,
            from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
            to=f"whatsapp:{ALERT_PHONE_RECIPIENT}"
        )
        print(f"[NOTIFIER] -> WhatsApp sent (SID: {message_wa.sid})")
        
    except Exception as e:
        print(f"[NOTIFIER ERROR] Twilio dispatch failed: {e}")
