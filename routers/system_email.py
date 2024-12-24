import os
from fastapi import APIRouter, Depends, Response, Request
from utils.stats import record_email_requested, add_email_failed_count, add_email_sent_count
from utils.authentication import verify_api_token
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from mysql_app.schemas import StandardResponse
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

admin_router = APIRouter(tags=["Email System"], prefix="/email")
API_IMAGE_NAME = os.getenv("IMAGE_NAME", "dev")
if "dev" in API_IMAGE_NAME.lower():
    thread_size = 1
else:
    thread_size = 5


class EmailRequest(BaseModel):
    subject: str
    content: str
    recipient: str


class SMTPConnectionPool:
    def __init__(self, pool_size: int = 5):
        self.smtp_server = os.getenv("EMAIL_SERVER")
        self.smtp_port = int(os.getenv("EMAIL_PORT"))
        self.username = os.getenv("EMAIL_USERNAME")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.pool_size = pool_size
        self.pool = []
        self.lock = threading.Lock()
        self._create_pool()

    def _create_pool(self):
        for _ in range(self.pool_size):
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.username, self.password)
            print(f'Created SMTP connection: {self.smtp_server}')
            self.pool.append(server)

    def _create_connection(self):
        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
        server.login(self.username, self.password)
        return server

    def get_connection(self):
        with self.lock:
            if self.pool:
                connection = self.pool.pop()
                try:
                    connection.noop()   # Check if connection is still active
                    return connection
                except smtplib.SMTPServerDisconnected:
                    return self._create_connection()
            else:
                return self._create_connection()

    def release_connection(self, connection):
        with self.lock:
            self.pool.append(connection)

    def send_email(self, subject: str, content: str, recipient: str):
        connection = self.get_connection()
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))

        try:
            connection.sendmail(self.username, recipient, msg.as_string())
            print('Email sent successfully')
        except Exception as e:
            print(f'Failed to send email: {e}')
        finally:
            self.release_connection(connection)


smtp_pool = SMTPConnectionPool(pool_size=thread_size)

executor = ThreadPoolExecutor(max_workers=10)


@admin_router.post("/send", dependencies=[Depends(record_email_requested), Depends(verify_api_token)])
async def send_email(email_request: EmailRequest, response: Response, request: Request) -> StandardResponse:
    try:
        smtp_pool.send_email(email_request.subject, email_request.content, email_request.recipient)
        add_email_sent_count(request)
        return StandardResponse(data={
            "code": 0,
            "message": "Email sent successfully"
        })
    except Exception as e:
        add_email_failed_count(request)
        response.status_code = 500
        return StandardResponse(retcode=500, message=f"Failed to send email: {e}",
                                data={
                                    "code": 500,
                                    "message": f"Failed to send email: {e}"
                                })
