# ==============================================================================
# บริการส่งอีเมลและรหัส OTP กู้คืนรหัสผ่าน (Email Service via SMTP)
# ==============================================================================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, SMTP_SENDER_NAME

def is_smtp_configured() -> bool:
    """ตรวจสอบว่ามีการตั้งค่าบัญชีอีเมล SMTP สำหรับส่งเมลจริงหรือไม่"""
    return bool(SMTP_EMAIL.strip() and SMTP_PASSWORD.strip())

def send_otp_email(to_email: str, otp_code: str, user_name: str = "ผู้ดูแลระบบ") -> tuple[bool, str]:
    """
    ส่งอีเมลรหัส OTP 6 หลักสำหรับกู้คืนรหัสผ่าน
    คืนค่า: (สถานะความสำเร็จ: bool, ข้อความตอบกลับ: str)
    """
    # 1. ตรวจสอบว่าได้ตั้งค่า SMTP จริงแล้วหรือไม่
    if not is_smtp_configured():
        # โหมดทดสอบ (ยังไม่ได้ระบุ Gmail จริง): จำลองการส่งสำเร็จ เพื่อให้ระบบทำงานได้ทันที
        return True, "DEV_MODE"

    try:
        # 2. จัดเตรียมเนื้อหาอีเมลแบบ HTML สวยงาม
        msg = MIMEMultipart('alternative')
        subject = f"[ฟ้าใสตำนัว] รหัส OTP กู้คืนรหัสผ่านของคุณคือ: {otp_code}"
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = f"{SMTP_SENDER_NAME} <{SMTP_EMAIL}>"
        msg['To'] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Sarabun', 'Segoe UI', Tahoma, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
                .email-card {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 14px; border: 1.5px solid #fed7aa; padding: 28px; box-shadow: 0 4px 14px rgba(234, 88, 12, 0.08); }}
                .header {{ text-align: center; margin-bottom: 20px; }}
                .title {{ color: #c2410c; font-size: 22px; font-weight: bold; margin: 6px 0; }}
                .subtitle {{ color: #78716c; font-size: 14px; }}
                .otp-box {{ background: linear-gradient(135deg, #fff7ed, #ffedd5); border: 2px dashed #ea580c; border-radius: 12px; padding: 18px; text-align: center; margin: 24px 0; }}
                .otp-code {{ font-size: 36px; font-weight: 800; color: #ea580c; letter-spacing: 8px; font-family: monospace; }}
                .warning {{ font-size: 13px; color: #dc2626; background: #fef2f2; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #ef4444; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 24px; font-size: 12px; color: #a8a29e; }}
            </style>
        </head>
        <body>
            <div class="email-card">
                <div class="header">
                    <div style="font-size: 22px; font-weight: bold; color: #ea580c;">ฟ้าใสตำนัว</div>
                    <div class="title">ฟ้าใสตำนัว (Fahsai Tumnua)</div>
                    <div class="subtitle">ระบบจัดการร้านอาหาร • รหัสยืนยันกู้คืนรหัสผ่าน</div>
                </div>
                
                <p style="color: #334155; font-size: 15px;">เรียนคุณ <b>{user_name}</b>,</p>
                <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                    ระบบได้รับคำขอกู้คืนรหัสผ่านสำหรับเข้าใช้งานระบบจัดการหลังร้าน กรุณาใช้รหัส <b>OTP 6 หลัก</b> ด้านล่างนี้เพื่อตั้งรหัสผ่านใหม่:
                </p>
                
                <div class="otp-box">
                    <div style="font-size: 13px; color: #9a3412; font-weight: 600; margin-bottom: 6px;">รหัสยืนยัน OTP ของคุณ</div>
                    <div class="otp-code">{otp_code}</div>
                    <div style="font-size: 12px; color: #78716c; margin-top: 6px;">รหัสมีอายุการใช้งาน 10 นาที</div>
                </div>
                
                <div class="warning">
                    <b>คำเตือนด้านความปลอดภัย:</b> หากท่านไม่ได้เป็นผู้ส่งคำขอนี้ โปรดเพิกเฉยต่ออีเมลฉบับนี้ และห้ามเปิดเผยรหัส OTP นี้แก่ผู้อื่นเด็ดขาด
                </div>
                
                <div class="footer">
                    อีเมลฉบับนี้ถูกส่งโดยระบบอัตโนมัติของร้านฟ้าใสตำนัว<br>
                    © 2026 Fahsai Tumnua Restaurant System. All rights reserved.
                </div>
            </div>
        </body>
        </html>
        """

        part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part)

        # 3. ส่งอีเมลผ่านเซิร์ฟเวอร์ SMTP พร้อมเข้ารหัส TLS
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()

        return True, "ส่งรหัส OTP สำเร็จเรียบร้อยแล้ว"

    except smtplib.SMTPAuthenticationError:
        return False, "เข้าสู่ระบบส่งอีเมลไม่สำเร็จ กรุณาตรวจสอบ Gmail และ App Password 16 หลัก"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการส่งอีเมล: {str(e)}"
