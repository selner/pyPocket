__author__ = 'bryan'
import pocket

from pocket import Pocket
import datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)
import os, codecs
import collections
import operator

DAYSBACK=14

class PocketMail():
    config = None
    _all_articles = {}
    _prev_data_articles = {}
    _tag_processing_data = None
    _pocket_instance = None
    _tags_to_email = None

    def __init__(self):
        import bsconfig
        self.config = bsconfig.BSConfig()
        self.config.loadConfigFromFile("./config-bryan.ini")
        self._initPocket()
        self._initTemplate()

    def _initPocket(self):
        access_token = u'3d50b538-8bfc-d571-1488-fabf77'
        consumer_key = self.config.get("AuthPocket", "consumer_key", None)
        if access_token is None:
            redirect_uri = self.config.get("AuthPocket", "redirect_uri", None)
            access_token = Pocket.auth(consumer_key=consumer_key, redirect_uri=redirect_uri)

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
            if len(option) > 1:
                dictTags[tag]['email'] = option[1]
            if len(option) > 2:
                dictTags[tag]['last_processed'] = option[2]
        return dictTags

                #
                # dtNow = datetime.datetime.now()
                # dictTagList[tag]['date_last_sent'] = dtNow.strftime('%m/%d/%Y-%H:%M:%S')
                # self.config.logger.info("Updating date last checked to " + dictTagList[tag]['date_last_sent'] + " for " + tag)
                # strCfgValue = dictTagList[tag]['email'] + " " + dictTagList[tag]['date_last_sent']
                # self.config.set(section="TagsToEmail", option=dictTagList[tag]['tag'], value=strCfgValue)
                # self.saveConfigToFile()

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

    def getHTMLforArticleList(self, data):
        self.config.logger.info("Generating html for article list...")

        if not (data and len(data)>0):
            self.config.logger.error("No articles found to export to html")

        self.config.logger.info("Enumerating template and articles...")
        data_for_template = {
                'articles' : data
            }

        outHTML = self.email_html_template(data_for_template)

        return outHTML

    def export_html_to_file(self, basename, html=None, articles=None):
        if not html:
            if articles:
                html = self.getHTMLforArticleList(articles)

        if not html:
            raise ValueError("Error: no html or articles to output to file")

        strtoday = datetime.date.today().strftime("%m-%d-%Y")
        filename = strtoday+"_"+basename+".html"
        filename = filename.replace(os.sep, "_")
        fileout = os.path.join(self.config.output_folder, filename)

        self.config.logger.info("Exporting test results to file '" + fileout + "'...")

        f = codecs.open(fileout, encoding='utf-8', mode='w+')
        f.write(html)
        f.close()

        return fileout



    def getArticlesSinceDate(self, numDays=30, tag=""):


        articles = None

        from datetime import datetime, timedelta
        dtsince = timedelta(days=-numDays) + datetime.today()
        sincetimestamp = (dtsince - datetime(1970, 1, 1)).total_seconds()

        self.config.logger.info("Getting pocketed items from the last " + str(numDays) + " days [since " + str(datetime.utcfromtimestamp(sincetimestamp)) + " with tag '" + tag + "'...")

        if tag == "_ALL_ARTICLES_":
            tag = ""

        data = self.instance.get(detailType="complete", contentType="article", state="all", tag=tag, sort="newest", since=sincetimestamp)
        if data and len(data) > 0:
            articles = data[0]['list']


        articles_by_date = dict((i, articles[i]['time_added']) for i in articles if 'time_added' in articles[i])

        results_content = collections.OrderedDict()
        for a in articles_by_date:


            if float(articles[a]['time_added']) >= sincetimestamp:
                item = {}
                item['href'] = articles[a]['resolved_url']
                item['title'] = articles[a]['resolved_title']
                item['excerpt'] = articles[a]['excerpt']
                authors_line = ""
                if 'authors' in articles[a]:
                    authorlist = []
                    for i in articles[a]['authors']:
                        authorlist.append(articles[a]['authors'][i]['name'])
                    authors_line = ", ".join(authorlist)
                item['authors'] = "-- " + authors_line
                if 'tags' in articles[a]:
                    item['tags'] = [articles[a]['tags'][i]['tag'] for i in articles[a]['tags']]
                item['added_date'] = datetime.fromtimestamp(float(articles[a]['time_added'])).strftime("%m/%d/%Y")
                item['time_added'] = float(articles[a]['time_added'])
                if articles[a]['has_image'] == "1" and 'image' in articles[a]:
                    item['thumbnail'] = {}
                    item['thumbnail']['src'] = articles[a]['image']['src']
                    item['thumbnail']['href'] = item['href']

                results_content[item['added_date']] = item

        # sorted(results_content)

        skeys = sorted(results_content.keys())
        orderedArticles = collections.OrderedDict()
        for k in skeys:
            orderedArticles[k] =results_content[k].copy()

        self.config.logger.log_pretty(level="INFO", data=orderedArticles, prefixtext="Articles returned: ")
        return orderedArticles


    def sendArticleListViaEmail(self, emailto=None, subject=None, html=None):
        """
        If the user specified email recipients on the command line for this run,
        then compose and send an email with the passed in content
        :return: None
        """

        if emailto:
            try:
                import uemail
                emailob = uemail.UEmailSend()
                emailob.setConnectionFromConfig(config=self.config)

                self.config.logger.info("Sending report email to " + unicode(emailto))
                emailob.sendEmail(sender=emailob._sender, recipient_list=emailto, subject=subject, html=html)
                self.config.logger.info("Report sent.")
            except (Exception, ValueError) as ex:
                msg = "Unable to send report email: " + ex.message
                self.config.logger.error(msg)
                raise ValueError(msg)


if __name__ == '__main__':

    pck = PocketMail()

    dictTagList = pck.tags_to_email


    items = pck.config.items("TagsToEmail")

    tagsToMatch = dictTagList.keys()

    if tagsToMatch:
        for tag in tagsToMatch:

            orderedArticles = pck.getArticlesSinceDate(numDays=30, tag=tag)
            if len(orderedArticles) > 0:
                html = pck.getHTMLforArticleList(data=orderedArticles)
                htmlfile = pck.export_html_to_file(basename=tag+"_articles", html=html)
                emailaddr = dictTagList[tag]['email']
                pck.sendArticleListViaEmail(emailto=emailaddr, subject="New Saved Articles Tagged '" + tag + "'", html=html)
            else:
                pck.config.logger.info("No articles found to export for tag '" + tag + "'.")

