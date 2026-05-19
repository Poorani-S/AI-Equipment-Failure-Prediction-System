"""Email Notification Module - Alert and notification delivery system"""

from flask_mail import Mail, Message
from datetime import datetime
from flask import current_app
import os
import traceback
from functools import wraps

# Initialize Flask-Mail
mail = Mail()

class EmailNotifier:
    """Handle email notifications for equipment alerts and recommendations"""

    @staticmethod
    def _smtp_ready() -> bool:
        try:
            config = current_app.config
            required = [
                config.get('MAIL_SERVER'),
                config.get('MAIL_PORT'),
                config.get('MAIL_USERNAME'),
                config.get('MAIL_PASSWORD'),
            ]
            return all(required)
        except Exception:
            # Fallback to env if app context is not available
            required = [
                os.environ.get('MAIL_SERVER'),
                os.environ.get('MAIL_PORT'),
                os.environ.get('MAIL_USERNAME'),
                os.environ.get('MAIL_PASSWORD'),
            ]
            return all(required)

    # Email templates
    ALERT_TEMPLATE = """
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #0f1419; color: #e8eaf6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px;">
                    ⚠️ Equipment Alert
                </h2>
                
                <div style="background-color: #242b48; padding: 15px; border-left: 4px solid {severity_color}; margin: 20px 0;">
                    <p><strong>Equipment ID:</strong> {equipment_id}</p>
                    <p><strong>Severity:</strong> <span style="color: {severity_color};">{severity}</span></p>
                    <p><strong>Alert Type:</strong> {alert_type}</p>
                    <p><strong>Message:</strong> {message}</p>
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                </div>

                <div style="background-color: #1a1f3a; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #00ff88;">Recommended Actions:</h3>
                    <ul>
                        {recommendations_html}
                    </ul>
                </div>

                <p style="color: #b0b9d4; font-size: 12px; margin-top: 20px;">
                    This is an automated notification from the AI Equipment Failure Prediction System.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """

    PREDICTION_TEMPLATE = """
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #0f1419; color: #e8eaf6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px;">
                    🎯 Prediction Report
                </h2>
                
                <div style="background-color: #242b48; padding: 15px; margin: 20px 0;">
                    <p><strong>Equipment ID:</strong> {equipment_id}</p>
                    <p><strong>Prediction:</strong> <span style="color: {prediction_color};">{prediction}</span></p>
                    <p><strong>Confidence:</strong> {confidence}%</p>
                    <p><strong>Risk Level:</strong> {risk_level}</p>
                    <p><strong>Health Score:</strong> {health_score}%</p>
                </div>

                <div style="background-color: #1a1f3a; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #00ff88;">Sensor Readings:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #00d4ff;">Temperature:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #00d4ff; text-align: right;"><strong>{temperature}°C</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #00d4ff;">Vibration:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #00d4ff; text-align: right;"><strong>{vibration} Hz</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #00d4ff;">Pressure:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #00d4ff; text-align: right;"><strong>{pressure} bar</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;">Humidity:</td>
                            <td style="padding: 8px; text-align: right;"><strong>{humidity}%</strong></td>
                        </tr>
                    </table>
                </div>

                <p style="color: #b0b9d4; font-size: 12px; margin-top: 20px;">
                    This is an automated notification from the AI Equipment Failure Prediction System.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """

    MAINTENANCE_TEMPLATE = """
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #0f1419; color: #e8eaf6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px;">
                    📅 Maintenance Schedule
                </h2>
                
                <p>The following equipment require scheduled maintenance:</p>

                <div style="background-color: #242b48; padding: 15px; margin: 20px 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #1a1f3a;">
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #00d4ff;">Equipment</th>
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #00d4ff;">Type</th>
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #00d4ff;">Due Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {maintenance_items_html}
                        </tbody>
                    </table>
                </div>

                <p style="color: #b0b9d4; font-size: 12px; margin-top: 20px;">
                    This is an automated notification from the AI Equipment Failure Prediction System.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """

    @staticmethod
    def send_alert_email(recipient, equipment_id, alert_type, message, severity, recommendations=None):
        """Send equipment alert email"""
        try:
            if not EmailNotifier._smtp_ready():
                print("SMTP is not configured. Skipping alert email send.")
                return False

            severity_color = {
                'info': '#00d4ff',
                'warning': '#ffaa00',
                'critical': '#ff3333'
            }.get(severity.lower(), '#00d4ff')

            recommendations_html = ''
            if recommendations:
                for rec in recommendations:
                    recommendations_html += f"<li>{rec}</li>"

            html_body = EmailNotifier.ALERT_TEMPLATE.format(
                equipment_id=equipment_id,
                alert_type=alert_type,
                message=message,
                severity=severity,
                severity_color=severity_color,
                recommendations_html=recommendations_html,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

            msg = Message(
                subject=f'⚠️ Alert: {equipment_id} - {alert_type}',
                recipients=[recipient],
                html=html_body
            )

            mail.send(msg)
            return True

        except Exception as e:
            print(f"Error sending alert email: {str(e)}")
            traceback.print_exc()
            return False

    @staticmethod
    def send_prediction_email(recipient, equipment_id, prediction, confidence, 
                            risk_level, health_score, sensors):
        """Send prediction report email"""
        try:
            if not EmailNotifier._smtp_ready():
                print("SMTP is not configured. Skipping prediction email send.")
                return False

            prediction_color = '#00ff88' if prediction == 'Normal' else '#ff3333'

            html_body = EmailNotifier.PREDICTION_TEMPLATE.format(
                equipment_id=equipment_id,
                prediction=prediction,
                prediction_color=prediction_color,
                confidence=f"{confidence:.2f}",
                risk_level=risk_level,
                health_score=f"{health_score:.2f}",
                temperature=f"{sensors.get('Temperature', 0):.2f}",
                vibration=f"{sensors.get('Vibration', 0):.2f}",
                pressure=f"{sensors.get('Pressure', 0):.2f}",
                humidity=f"{sensors.get('Humidity', 0):.2f}"
            )

            msg = Message(
                subject=f'🎯 Prediction Report: {equipment_id}',
                recipients=[recipient],
                html=html_body
            )

            mail.send(msg)
            return True

        except Exception as e:
            print(f"Error sending prediction email: {str(e)}")
            traceback.print_exc()
            return False

    @staticmethod
    def send_maintenance_email(recipients, maintenance_schedule):
        """Send maintenance schedule email"""
        try:
            if not EmailNotifier._smtp_ready():
                print("SMTP is not configured. Skipping maintenance email send.")
                return False

            maintenance_items_html = ''
            for item in maintenance_schedule:
                maintenance_items_html += f"""
                    <tr style="border-bottom: 1px solid #00d4ff;">
                        <td style="padding: 10px;">{item.get('equipment_id', 'N/A')}</td>
                        <td style="padding: 10px;">{item.get('maintenance_type', 'N/A')}</td>
                        <td style="padding: 10px;">{item.get('due_date', 'N/A')}</td>
                    </tr>
                """

            html_body = EmailNotifier.MAINTENANCE_TEMPLATE.format(
                maintenance_items_html=maintenance_items_html
            )

            msg = Message(
                subject='📅 Maintenance Schedule Notification',
                recipients=recipients if isinstance(recipients, list) else [recipients],
                html=html_body
            )

            mail.send(msg)
            return True

        except Exception as e:
            print(f"Error sending maintenance email: {str(e)}")
            return False

    @staticmethod
    def send_daily_report_email(recipient, report_data):
        """Send daily system report email"""
        try:
            if not EmailNotifier._smtp_ready():
                print("SMTP is not configured. Skipping daily report email send.")
                return False

            total_equipment = report_data.get('total_equipment', 0)
            total_predictions = report_data.get('total_predictions', 0)
            total_alerts = report_data.get('total_alerts', 0)
            uptime = report_data.get('uptime', '99.9%')
            report_date = datetime.now().strftime('%Y-%m-%d')

            html_body = f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="font-family: Arial, sans-serif; background-color: #0f1419; color: #e8eaf6;">
                    <div style="max-width: 680px; margin: 0 auto; padding: 28px 18px 40px;">
                        <div style="background: linear-gradient(135deg, #10213a 0%, #13294d 45%, #0f172a 100%); border: 1px solid rgba(96, 165, 250, 0.18); border-radius: 20px; overflow: hidden; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.28);">
                            <div style="padding: 28px 28px 20px; border-bottom: 1px solid rgba(148, 163, 184, 0.14);">
                                <div style="font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase; color: #8fb6ff; margin-bottom: 10px;">AI Equipment Monitoring</div>
                                <h2 style="margin: 0; font-size: 30px; line-height: 1.1; color: #eaf2ff;">Daily System Report</h2>
                                <p style="margin: 10px 0 0; font-size: 14px; color: #a9b9d6;">A concise operations summary for {report_date}.</p>
                            </div>

                            <div style="padding: 24px 28px 10px;">
                                <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: separate; border-spacing: 0;">
                                    <tr>
                                        <td style="width: 50%; padding: 0 8px 16px 0;">
                                            <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 16px; padding: 18px;">
                                                <div style="font-size: 12px; color: #8fb6ff; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 8px;">Total Equipment</div>
                                                <div style="font-size: 28px; font-weight: 700; color: #ffffff;">{total_equipment}</div>
                                            </div>
                                        </td>
                                        <td style="width: 50%; padding: 0 0 16px 8px;">
                                            <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 16px; padding: 18px;">
                                                <div style="font-size: 12px; color: #8fb6ff; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 8px;">Predictions Made</div>
                                                <div style="font-size: 28px; font-weight: 700; color: #ffffff;">{total_predictions}</div>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="width: 50%; padding: 0 8px 16px 0;">
                                            <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 16px; padding: 18px;">
                                                <div style="font-size: 12px; color: #8fb6ff; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 8px;">Alerts Triggered</div>
                                                <div style="font-size: 28px; font-weight: 700; color: #ffffff;">{total_alerts}</div>
                                            </div>
                                        </td>
                                        <td style="width: 50%; padding: 0 0 16px 8px;">
                                            <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 16px; padding: 18px;">
                                                <div style="font-size: 12px; color: #8fb6ff; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 8px;">System Uptime</div>
                                                <div style="font-size: 28px; font-weight: 700; color: #ffffff;">{uptime}</div>
                                            </div>
                                        </td>
                                    </tr>
                                </table>

                                <div style="margin-top: 8px; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.18); border-radius: 14px; padding: 16px 18px; color: #cde9ff; font-size: 14px; line-height: 1.6;">
                                    This report highlights the current equipment count, AI prediction activity, active alert volume, and availability trend for the day.
                                </div>
                            </div>

                            <div style="padding: 0 28px 28px;">
                                <div style="border-top: 1px solid rgba(148, 163, 184, 0.14); padding-top: 18px; font-size: 12px; color: #93a4c7; line-height: 1.6;">
                                    Sent automatically by the AI Equipment Failure Prediction System.<br>
                                    Please do not reply to this message.
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """

            msg = Message(
                subject='Daily System Report - AI Equipment Monitoring',
                recipients=[recipient],
                html=html_body
            )

            mail.send(msg)
            return True

        except Exception as e:
            err_msg = str(e)
            print(f"CRITICAL: Error sending daily report email: {err_msg}")
            traceback.print_exc()
            if "authentication failed" in err_msg.lower() or "5.7.8" in err_msg:
                print("HINT: Gmail authentication failed. You MUST use an App Password, not your account password.")
                print("Check your .env file for instructions on generating an App Password.")
            return False


def send_email_async(func):
    """Decorator to send emails asynchronously"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in email operation: {str(e)}")
            return False
    return wrapper
