__author__ = 'bryan'
import pocket

from pocket import Pocket
import re, datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)
import json
import os, codecs
from uemail.uemail import UEmailSend

xstr = lambda s: s or ""

DEV_DEBUG = True

class PocketMail(object):

    _all_articles = {}
    _prev_data_articles = {}
    _previous_data_file = None
    _pocket_instance = None
    _tags_to_email = None
    _cfg_filename = "./config-bryan.ini"

    def __init__(self):
        import bsconfig
        self.config = bsconfig.BSConfig()
        self.config.loadConfigFromFile(self._cfg_filename)
        self._loadPreviousData()
        self._initPocket()
        self._initTemplate()

    def saveConfigToFile(self):
        f = open(self._cfg_filename, mode='w')
        self.config.write(f)
        f.close()


    def _loadPreviousData(self):
        import codecs, os
        self._previous_data_file = self.config.get("Input", "previous_data_file", None)
        if self._previous_data_file and os.path.isfile(self._previous_data_file ):
            f = codecs.open(self._previous_data_file, encoding='utf-8', mode='r')
            self._prev_data_articles = json.load( f )
            f.close()

    def _initPocket(self):
        from oauth2client.file import Storage
#        storage = Storage(os.path.join(self.config.output_folder, "oauth.dat"))
#        access_token = storage.get()
        access_token = u'3d50b538-8bfc-d571-1488-fabf77'
        consumer_key = self.config.get("AuthPocket", "consumer_key", None)
        if access_token is None:
            redirect_uri = self.config.get("AuthPocket", "redirect_uri", None)
            access_token = Pocket.auth(consumer_key=consumer_key, redirect_uri=redirect_uri)
#            storage.put(access_token)

        self._pocket_instance = pocket.Pocket(consumer_key, access_token)

    @property
    def instance(self):
        return self._pocket_instance

    @property
    def tags_to_email(self):
        if not self._tags_to_email:
            self._tags_to_email = self._load_tags_to_email()
        return self._tags_to_email

    def _load_tags_to_email(self):
        dictTags = {}
        items = self.config.items("TagsToEmail")
        for option in items:
            tag = option[0]
            dictTags[tag] = {}
            dictTags[tag]['tag'] = tag
            dictTags[tag]['date_last_sent'] = None
            values = option[1].split()
            if len(values) > 0:
                dictTags[tag]['email'] = values[0]
            if len(values) > 1:
                dictTags[tag]['date_last_sent'] = values[1]
            if DEV_DEBUG:
                dictTags[tag]['date_last_sent'] = None
            dictTags[tag]['new_articles'] = {}
        return dictTags

    def _initTemplate(self):

        #
        #  Load the template
        #
        self.config.logger.info("Reading template file 'email_html_template.mustache'...")
        f = codecs.open("email_html_template.mustache", encoding='utf-8', mode='rb')
        strtempl = f.read()
        f.close()

        #
        #  Compile the template
        #
        from pybars import Compiler
        compiler = Compiler()
        self.html_full_results_template = compiler.compile(strtempl)

        self.email_html_template = compiler.compile(strtempl)

    def getHTMLforArticleList(self, articles):
        self.config.logger.info("Generating html for article list...")

        if not (articles and len(articles)>0):
            self.config.logger.error("No articles found to export to html")
            return None

        self.config.logger.info("Enumerating template and articles...")
        data_for_template = {
                'articles' : articles
            }

        outHTML = self.email_html_template(data_for_template)

        return outHTML

    def export_html_to_file(self, basename, html=None, articles=None):
        if not html:
            if articles:
                html = self.getHTMLforArticleList(articles)

        if not html:
            self.config.logger.warning("Error: no html or articles to output for keyword " + basename)
            return

        strtoday = datetime.date.today().strftime("%m-%d-%Y")
        filename = strtoday+"_"+basename+".html"
        fileout = os.path.join(self.config.output_folder, filename)

        self.config.logger.info("Exporting test results to file '" + fileout + "'...")

        f = codecs.open(fileout, encoding='utf-8', mode='w+')
        f.write(html)
        f.close()

        return fileout

    def sendNewarticlesToEmail(self):
        dictTagList = self.tags_to_email
        tagsToMatch = dictTagList.keys()

        if tagsToMatch:
            for tag in tagsToMatch:
                articles = None

                self.config.logger.info(">>>>>>>>   Processing tag: '" + tag + "'   <<<<<<<<<<")
                self.config.logger.info("Checking for articles tagged " + tag + " since " + xstr(dictTagList[tag]['date_last_sent']))
                pattern = '%m/%d/%Y-%H:%M:%S'
                import time
                eplastdate = None
                if dictTagList[tag]['date_last_sent']:
                    eplastdate = int(time.mktime(time.strptime(dictTagList[tag]['date_last_sent'], pattern)))


                data = pck.instance.get(detailType="complete", contentType="article", sort="oldest", tag=tag, since=eplastdate)

                first_title = ""
                if not( data and len(data) > 0 and 'list' in data[0] and len(data[0]['list']) >0):
                    self.config.logger.info("No new articles found for " + tag)
                else:
                    articles = data[0]['list']
                    self.config.logger.info(str(len(articles)) + " new articles found tagged " + tag)

                    dictTagList[tag]['new_articles'] = articles
                    emailArticles = []
                    for a in articles:
                        item = {}
                        item['href'] = articles[a]['resolved_url']
                        item['title'] = articles[a]['resolved_title']
                        if not first_title:
                            first_title = item['title']
                        item['excerpt'] = articles[a]['excerpt']
                        authors_line = ""
                        item['authors'] = None
                        if 'authors' in articles[a]:
                            authorlist = []
                            for i in articles[a]['authors']:
                                authorlist.append(articles[a]['authors'][i]['name'])
                            authors_line = ", ".join(authorlist)
                            item['authors'] = "-- " + authors_line
            #            import time
            #            item['added_date'] = time.strftime('%m-%d-%Y', time.localtime(float(articles[a]['time_added'])))

                        item['added_date'] = datetime.datetime.fromtimestamp(float(articles[a]['time_added'])).strftime("%m/%d/%Y")
                        if articles[a]['has_image'] == "1" and 'image' in articles[a]:
                            item['thumbnail'] = {}
                            item['thumbnail']['src'] = articles[a]['image']['src']
                            item['thumbnail']['href'] = item['href']

                        emailArticles.append(item)

                    html = self.getHTMLforArticleList(articles=emailArticles)
                    if html:
                        if first_title:
                            subject = "'" + first_title + "'"
                        if len(emailArticles) > 1:
                            subject = subject + " and " + str(len(emailArticles)) + " other " + tag + " recent articles"
                        htmlfile = self.export_html_to_file(basename=tag, html=subject + "\n\n"+ html)
                        if htmlfile:
                            self.config.logger.info("Article list HTML written to " + htmlfile)
                        self.sendEmail(html=html, text=None, toaddr=dictTagList[tag]['email'], subject=subject)

                dtNow = datetime.datetime.now()
                dictTagList[tag]['date_last_sent'] = dtNow.strftime('%m/%d/%Y-%H:%M:%S')
                self.config.logger.info("Updating date last checked to " + dictTagList[tag]['date_last_sent'] + " for " + tag)
                strCfgValue = dictTagList[tag]['email'] + " " + dictTagList[tag]['date_last_sent']
                self.config.set(section="TagsToEmail", option=dictTagList[tag]['tag'], value=strCfgValue)
                self.saveConfigToFile()

    def getEmailSetup(self):
        email_setup = dict(self.config.items("AuthEmail"))

        if 'from_address' not in email_setup and 'smtp_server' not in email_setup:
            self.config.logger.error("Required email parameters 'from_address' and 'smtp_server' not found in config file.  Cannot send email.")
            raise ValueError("Required email parameters 'from_address' and 'smtp_server' not found in config file.  Cannot send email.")

        return email_setup

    def sendEmail(self, html=None, text=None, toaddr=None, subject=None):
        """With this function we send out our html email"""

        email = UEmailSend()
        email_setup = self.getEmailSetup()
        self.config.logger.info("Sending email to " + toaddr + " from " + email_setup['sender'])

        email.setConnection(sender=email_setup['sender'], user_login=email_setup['email_login'], user_password=email_setup['email_password'], smtp_server=email_setup['smtp_server'], smtp_port=email_setup['smtp_port'])
        fSent = email.sendEmail(recipient_list=toaddr, subject=subject, html=html)
        if not fSent:
            self.config.logger.error("Email failed to send.")
        else:
            self.config.logger.info("Email sent successfully.")

        return fSent

    def sendRunLog(self):
        email_setup = self.getEmailSetup()
        self.config.logger.info("Sending run log to " + email_setup['sender'])

        email = UEmailSend()
        dtNow = datetime.datetime.now()
        subject = "pyPocket Run log for " + dtNow.strftime('%m/%d/%Y %H:%M:%S')

        with codecs.open(self.config._logfilename, encoding='utf-8', mode='rb') as fp:

            # Create a text/plain message
            text = fp.read()
        fp.close()
        email.setConnection(sender=email_setup['sender'], user_login=email_setup['email_login'], user_password=email_setup['email_password'], smtp_server=email_setup['smtp_server'], smtp_port=email_setup['smtp_port'])

        email.sendEmail(recipient_list=email_setup['sender'], subject=subject, html=None, text=text, files=[self.config._logfilename])


pck = PocketMail()
pck.sendNewarticlesToEmail()
pck.sendRunLog()


