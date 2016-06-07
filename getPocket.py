__author__ = 'bryan'
import pocket

from pocket import Pocket
import datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)
import os, codecs
import collections
from pscommon import psreport

ARTICLE_IMAGE_PLACEHOLDER = "https://confluence.underpaid.com/download/attachments/15436430/external_article_placeholder.jpg"

DAYSBACK=21

class PocketMail(psreport.PSReportBase):
    config = None
    _all_articles = {}
    _prev_data_articles = {}
    _tag_processing_data = None
    _pocket_instance = None
    _tags_to_email = None
    _email_html_template = None
    _confluence_xml_template = None

    def __init__(self):
        psreport.PSReportBase.__init__(self, name="pyPocket")
        self._initPocket()
        self._email_html_template = self._initTemplate("email_html_template.mustache")
        self._confluence_xml_template = self._initTemplate("confluence_template.mustache")

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


        # if len(dictTags) == 0:
        #     dictTags = { 'tag' : "_ALL_ARTICLES_", 'email' : 'bryan@bryanselner.com' }
        return dictTags

                #
                # dtNow = datetime.datetime.now()
                # dictTagList[tag]['date_last_sent'] = dtNow.strftime('%m/%d/%Y-%H:%M:%S')
                # self.config.logger.info("Updating date last checked to " + dictTagList[tag]['date_last_sent'] + " for " + tag)
                # strCfgValue = dictTagList[tag]['email'] + " " + dictTagList[tag]['date_last_sent']
                # self.config.set(section="TagsToEmail", option=dictTagList[tag]['tag'], value=strCfgValue)
                # self.saveConfigToFile()

    def _initTemplate(self, filepath):

        #
        #  Load the template
        #
        self.config.logger.info("Reading template file '" + filepath + "'...")
        f = codecs.open(filepath, encoding='utf-8', mode='rb')
        strtempl = f.read()
        f.close()

        #
        #  Compile the template
        #
        from pybars import Compiler
        compiler = Compiler()
        return compiler.compile(strtempl)

    def getXMLforArticleList(self, data, mustacheTemplate):
        self.config.logger.info("Generating html for article list...")

        if not (data and len(data)>0):
            self.config.logger.error("No articles found to export to html")

        self.config.logger.info("Enumerating template and articles...")
        data_for_template = {
                'articles' : data
            }

        outHTML = mustacheTemplate(data_for_template)

        return outHTML

    def export_xml_to_file(self, basename, template, articles=None):
        xml = self.getXMLforArticleList(articles, template)

        strtoday = datetime.date.today().strftime("%m-%d-%Y")
        filename = strtoday+"_"+basename
        filename = filename.replace(os.sep, "_")
        fileout = os.path.join(self.config.output_folder, filename)

        self.config.logger.info("Exporting test results to file '" + fileout + "'...")

        f = codecs.open(fileout, encoding='utf-8', mode='w+')
        f.write(xml)
        f.close()

        return fileout

    def export_html_to_file(self, basename, html=None, articles=None):
        if not html:
            if articles:
                html = self.getXMLforArticleList(articles, self._email_html_template)

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

    def export_to_files(self, basename, articles=None):

        self.config.logger.info("Exporting tag results to email and web html file...")
        basefilename = "web_and_email_" + basename + ".html"
        self.export_xml_to_file(basename=basefilename, template=self._email_html_template, articles=articles)

        self.config.logger.info("Exporting tag results to confluence XML file...")
        basefilename = "confluence_" + basename + ".xml"
        self.export_xml_to_file(basename=basefilename, template=self._confluence_xml_template, articles=articles)




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
            from datetime import datetime
            datetime.fromtimestamp(int(articles[a]['time_added'])).strftime('%Y-%m-%d %H:%M:%S')

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
#                item['datetime_added'] = datetime.fromtimestamp(int(articles[a]['time_added'])).strftime('%Y-%m-%d %H:%M:%S')
                item['datetime_added'] = datetime.fromtimestamp(int(articles[a]['time_added'])).strftime('%Y-%m-%d')
                item['time_added'] = float(articles[a]['time_added'])
                if articles[a]['has_image'] == "1" and 'image' in articles[a]:
                    item['thumbnail'] = {}
                    item['thumbnail']['src'] = articles[a]['image']['src']
                    item['thumbnail']['href'] = item['href']
                else:
                    item['thumbnail'] = {}
                    item['thumbnail']['src'] = ARTICLE_IMAGE_PLACEHOLDER
                    item['thumbnail']['href'] = item['href']

                results_content[item['time_added']] = item

        # sorted(results_content)

        skeys = sorted(results_content.keys(), reverse=True)
        orderedArticles = collections.OrderedDict()
        for k in skeys:
            orderedArticles[k] = results_content[k].copy()

        self.config.logger.log_pretty(level="INFO", data=orderedArticles, prefixtext="Articles returned: ")
        return orderedArticles


    def sendArticleListViaEmail(self, emailto=None, subject=None, html=None):
        """
        If the user specified email recipients on the command line for this run,
        then compose and send an email with the passed in content
        :return: None
        """

        self._sendReportViaEmail(emailto, subject, html)


if __name__ == '__main__':

    pck = PocketMail()

    # dictTagList = pck.tags_to_email
    #
    # items = pck.config.items("TagsToEmail")
    #
    # tagsToMatch = dictTagList.keys()
    #
    # if tagsToMatch:
    #     for tag in tagsToMatch:
    #
    #         orderedArticles = pck.getArticlesSinceDate(numDays=180, tag=tag)
    #         if len(orderedArticles) > 0:
    #             html = pck.getHTMLforArticleList(data=orderedArticles)
    #             htmlfile = pck.export_html_to_file(basename=tag + "_articles", html=html)
    #             emailaddr = dictTagList[tag]['email']
    #             pck.sendArticleListViaEmail(emailto=emailaddr, subject="New Saved Articles Tagged '" + tag + "'",
    #                                         html=html)
    #         else:
    #             pck.config.logger.info("No articles found to export for tag '" + tag + "'.")


    tagsToExport = ("powershell", "design", "dev")

    for tag in tagsToExport:
        orderedArticles = pck.getArticlesSinceDate(numDays=180, tag=tag )
        if len(orderedArticles) > 0:
            pck.export_to_files(basename=tag + "_articles", articles=orderedArticles)

            # html = pck.getXMLforArticleList(data=orderedArticles)
            # htmlfile = pck.export_html_to_file(basename=tag + "_articles", html=html)
            # emailaddr = "bryan@bryanselner.com"
            # pck.sendArticleListViaEmail(emailto=emailaddr, subject="New Saved Articles Tagged '" + tag + "'", html=html)
        else:
            pck.config.logger.info("No articles found to export for tag '" + tag + "'.")

