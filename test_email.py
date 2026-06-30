import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.getenv('MAIL_USERNAME'), os.getenv('MAIL_PASSWORD'))
    server.quit()
    print('SUCCESS: Email authentication works!')
except Exception as e:
    print(f'FAILED: {str(e)}')