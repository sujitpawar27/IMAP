from flask import Flask, render_template, request, redirect, url_for, flash
import imaplib
import email
import smtplib
import time
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Email credentials
EMAIL = "pembhare69@gmail.com"
PASSWORD = "pnis drft jass gmup"  # Use your App Password
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
LAST_EMAIL_FILE = "last_email_id.txt"

# Fetch the last processed email ID from file
def get_last_email_id():
    try:
        with open(LAST_EMAIL_FILE, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Save the last processed email ID
def save_last_email_id(email_id):
    with open(LAST_EMAIL_FILE, "w") as file:
        file.write(email_id)

# Fetch emails
def fetch_emails(page=1, per_page=5):
    emails = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()

        total_emails = len(email_ids)
        start = (page - 1) * per_page
        end = start + per_page

        for email_id in reversed(email_ids[start:end]):  # Get paginated emails
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    sender = msg.get("From")

                    emails.append({"id": email_id.decode(), "sender": sender, "subject": subject})

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"Error: {e}")

    return emails, total_emails



# Send Email
def send_email(to_email, subject, message):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to_email, msg.as_string())
        server.quit()
        return True

    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Auto-reply function
def auto_reply():
    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, PASSWORD)
            mail.select("inbox")

            status, messages = mail.search(None, 'ALL')
            email_ids = messages[0].split()

            last_email_id = get_last_email_id()

            if email_ids:
                latest_email_id = email_ids[-1].decode()

                if last_email_id != latest_email_id:  # New email detected
                    status, msg_data = mail.fetch(latest_email_id, '(RFC822)')

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])

                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or "utf-8")

                            sender = msg.get("From")
                            sender_email = sender.split("<")[-1].strip(">")

                            # Extract email body
                            email_body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    if content_type == "text/plain":
                                        email_body = part.get_payload(decode=True).decode()
                                        break
                            else:
                                email_body = msg.get_payload(decode=True).decode()

                            # Prepare reply message
                            reply_message = f"Hi, replying to: \n{email_body}"

                            # Send auto-reply
                            send_email(sender_email, "Re: " + subject, reply_message)

                            # Update last processed email ID
                            save_last_email_id(latest_email_id)

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"Auto-reply error: {e}")

        time.sleep(60)  # Check every 60 seconds


@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 10  # Adjust as needed

    emails, total_emails = fetch_emails(page, per_page)
    total_pages = (total_emails + per_page - 1) // per_page  # Calculate total pages

    return render_template("index.html", emails=emails, page=page, total_pages=total_pages)



@app.route("/compose", methods=["GET", "POST"])
def compose_email():
    if request.method == "POST":
        to_email = request.form.get("to_email")
        subject = request.form.get("subject")
        message = request.form.get("message")

        if send_email(to_email, subject, message):
            flash("Email sent successfully!", "success")
        else:
            flash("Failed to send email.", "danger")

        return redirect(url_for("index"))

    return render_template("compose.html")

@app.route("/email/<email_id>")
def view_email(email_id):
    email_data = fetch_emails(email_id)
    if email_data:
        return render_template("emailView.html", email=email_data)
    else:
        return "Email not found or error retrieving content."

@app.route("/reply", methods=["POST"])
def reply_email():
    to_email = request.form.get("to_email")
    subject = request.form.get("subject")
    message = request.form.get("message")

    if send_email(to_email, "Re: " + subject, message):
        flash("Reply sent successfully!", "success")
    else:
        flash("Failed to send reply.", "danger")

    return redirect(url_for("index"))
if __name__ == "__main__":
    threading.Thread(target=auto_reply, daemon=True).start()
    app.run(debug=True)
