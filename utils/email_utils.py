import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from base_logger import logger

FROM_EMAIL = os.getenv("FROM_EMAIL")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_system_email(subject, message, to_email) -> bool:
    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject

    # 邮件正文
    msg.attach(MIMEText(message, 'plain'))

    # 连接到SMTP服务器
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # 发送邮件
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        # 关闭连接
        server.quit()

        logger.info(f"邮件发送成功: {subject}")
        return True
    except Exception as e:
        logger.exception(f"邮件发送失败: {e}")
        return False
