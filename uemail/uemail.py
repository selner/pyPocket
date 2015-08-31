#coding: utf-8
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import Charset
import smtplib
from email.utils import parseaddr, formataddr
# https://gist.github.com/ymirpl/1052094



#coding: utf-8
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import Charset
import smtplib
from email.utils import parseaddr, formataddr
# https://gist.github.com/ymirpl/1052094
from email.mime.base import MIMEBase
from email import encoders
import os

class UEmailSend():

    _sender = None
    _user_login = None
    _user_password = None
    _smtp_server = None
    _smtp_port = None
    _logger = None

    def setConnectionFromConfig(self, config=None):
        if not config:
            raise ValueError("Could not set email configuration; invalid config object passed to method.")
        email_setup = dict(config.items("AuthEmail"))

        if 'from_address' not in email_setup and 'smtp_server' not in email_setup:
            config.logger.error("Required email parameters 'from_address' and 'smtp_server' not found in config file.  Cannot send email.")
            raise ValueError("Required email parameters 'from_address' and 'smtp_server' not found in config file.  Cannot send email.")

        self._sender = email_setup['sender']
        self._user_login = email_setup['email_login']
        self._user_password = email_setup['email_password']
        self._smtp_server = email_setup['smtp_server']
        self._smtp_port = email_setup['smtp_port']
        self._logger = config.logger


    def sendEmail(self, sender=None, recipient_list=None, subject=None, html=None, text=None, files=[]):
        # Default encoding mode set to Quoted Printable. Acts globally!
        Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')

        if not sender:
            sender = self._sender
        sender_name, sender_addr = parseaddr(sender)

        if isinstance(recipient_list, basestring):
            rlist = recipient_list.split(",")
            if rlist and len(rlist) > 1:
                recipient_list = rlist
            else:
                recipient_list = [recipient_list]

        # 'alternative’ MIME type – HTML and plain text bundled in one e-mail message
        msg = MIMEMultipart()
        msg['From'] = formataddr((sender_name, sender_addr))
        # msg['To'] = formataddr((recipient_name, recipient_addr))
        msg['Subject'] = "%s" % Header(subject, 'utf-8')

        # Attach both parts
        if html:
            htmlpart = MIMEText(html, 'html', 'UTF-8')
            msg.attach(htmlpart)

        if text:
            textpart = MIMEText(u'\n' + text.encode('UTF-8'), 'plain', 'UTF-8')
            msg.attach(textpart)

        if files:
            for f in files:
                if f:
                    part = MIMEBase('application', "octet-stream")
                    part.set_payload( open(f,"rb").read() )
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(f)))
                    msg.attach(part)


        try:
            s = smtplib.SMTP(self._smtp_server, self._smtp_port)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(self._user_login, self._user_password)
            ret = s.sendmail(sender, recipient_list, msg.as_string())
            if ret:
                print "Sendmail returned: " + str(ret)

        except Exception, exc:
            print "Error occurred while sending: " + exc.message
            raise

        return True

    def setConnection(self, sender=None, user_login=None, user_password=None, smtp_server=None, smtp_port=None):

        self._sender = sender
        self._user_login = user_login
        self._user_password = user_password
        self._smtp_server = smtp_server
        self._smtp_port = smtp_port


