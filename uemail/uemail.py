#coding: utf-8
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import Charset
import smtplib
from email.utils import parseaddr, formataddr
# https://gist.github.com/ymirpl/1052094

class UEmailSend():

    def sendEmail(self, sender=None, user_login=None, user_password=None, recipient=None, subject=None, html=None, text=None, smtp_server=None, smtp_port=None, files=[]):
        # Default encoding mode set to Quoted Printable. Acts globally!
        Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')

        # Split real name (which is optional) and email address parts
        sender_name, sender_addr = parseaddr(sender)
        recipient_name, recipient_addr = parseaddr(recipient)
        if not recipient_name:
            recipient_name = recipient_addr
            recipient = formataddr((recipient_name, recipient_addr))

        # 'alternative’ MIME type – HTML and plain text bundled in one e-mail message
        msg = MIMEMultipart()
        msg['From'] = formataddr((sender_name, sender_addr))
        msg['To'] = formataddr((recipient_name, recipient_addr))
        msg['Subject'] = "%s" % Header(subject, 'utf-8')

        if files:
            for f in files:
                from email.mime.base import MIMEBase
                from email import encoders
                import os
                part = MIMEBase('application', "octet-stream")
                part.set_payload( open(f,"rb").read() )
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(f)))
                msg.attach(part)

        # Attach both parts
        if html:
            htmlpart = MIMEText(html, 'html', 'UTF-8')
            msg.attach(htmlpart)

        if text:
            textpart = MIMEText(u'\n' + text.encode('UTF-8'), 'plain', 'UTF-8')
            msg.attach(textpart)


        # Create a generator and flatten message object to 'file’
        # str_io = StringIO()
        # g = Generator(str_io, False)
        # g.flatten(msg)
        # str_io.getvalue() contains ready to sent message

        # Optionally - send it – using python's smtplib
        # or just use Django's
        try:
            s = smtplib.SMTP(smtp_server, smtp_port)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user_login, user_password)
            ret = s.sendmail(sender, recipient, msg.as_string())
            if ret:
                print "Sendmail returned: " + str(ret)

        except Exception, exc:
            print "Error occurred while sending: " + exc.message
            raise

        return True