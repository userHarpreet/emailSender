import logging
import smtplib
import socket
import ssl
import configparser
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='email_sender.log',
        filemode='a'
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


configure_logging()
logger = logging.getLogger(__name__)


def read_config(config_path='files/config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        logger.error(f"Configuration file {config_path} not found!")
        raise FileNotFoundError(f"Configuration file {config_path} not found!")
    config.read(config_path)
    return config


def send_email_with_attachment(config):
    sender_email = config.get('Email', 'SENDER_EMAIL')
    to_emails = config.get('Email', 'TO_EMAILS').split(',')
    cc_emails = config.get('Email', 'CC_EMAILS').split(',') if config.get('Email', 'cc_emails') else []
    password = config.get('Email', 'PASSWORD')
    subject = config.get('Email', 'SUBJECT')
    body = config.get('Email', 'BODY')
    filename = config.get('File', 'FILENAME')
    smtp_server = config.get('SMTP', 'HOST')
    smtp_port = config.getint('SMTP', 'PORT')

    logger.info('Preparing to send email...')
    logger.info('Sender: %s', sender_email)
    logger.info('To: %s', ', '.join(to_emails))
    logger.info('Cc: %s', ', '.join(cc_emails))
    logger.info('Subject: %s', subject)
    logger.info('Attachment: %s', filename)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = ", ".join(to_emails)
    message["Cc"] = ", ".join(cc_emails)
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))
    logger.debug('Email body attached')

    try:
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        logger.debug('File %s read successfully', filename)
    except IOError as e:
        logger.error('Failed to read attachment file: %s', e)
        raise

    encoders.encode_base64(part)
    logger.debug('File encoded successfully')

    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )

    message.attach(part)
    logger.debug('Attachment added to message')

    text = message.as_string()
    all_recipients = to_emails + cc_emails

    context = ssl.create_default_context()
    try:
        logger.info(f'Attempting to connect to SMTP server: {smtp_server}')
        # Try to resolve the hostname first
        try:
            server_ip = socket.gethostbyname(smtp_server)
            logger.info(f'Successfully resolved server to {server_ip}')
        except socket.gaierror as e:
            logger.error(f'Failed to resolve server: {e}')
            raise

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.info('Connected to SMTP server')
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            logger.info('Logged in successfully')
            server.sendmail(sender_email, all_recipients, text)
            logger.info('Email sent successfully!')
    except (smtplib.SMTPException, socket.gaierror) as e:
        logger.error(f'An error occurred while sending the email: {e}')
        raise

    logger.info('Email sending process completed')


if __name__ == "__main__":
    try:
        config = read_config()
        send_email_with_attachment(config)
    except Exception as e:
        logger.exception("An error occurred while sending the email:")
