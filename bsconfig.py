# -*- coding: utf-8 -*-

import ConfigParser
import os
import logging
import logging.handlers
import pprint

class PrettyLogger(logging.Logger):
    """ Simple Logger class extension that adds a method log_pretty() to record an
        entry for the data in an object in a pretty printed format
    """

    def log_pretty(self, level, prefixtext, data, *args, **kwargs):
        try:
            import json
            str = json.dumps(data, indent=8, encoding="utf-8")
        except:
            str = pprint.pformat(data, indent=1, depth=4, width=20)
        if prefixtext:
            prefixtext = prefixtext + "\n"
        self.log(logging._checkLevel(level), prefixtext + " " + str, *args, **kwargs)

class BSConfig(ConfigParser.RawConfigParser):
    _output_folder = None
    __cfgfile__ = None
    _nameprefix = ""
    _logginglevel = None
    _logfilename = None

    def __init__(self, defaults=None, dict_type=ConfigParser._default_dict,
                 allow_no_value=False, level=logging.INFO, name=""):

        self._nameprefix  = name
        if not self._nameprefix:
            self._nameprefix  = "bsconfig"

        self._logginglevel = level

        ConfigParser.RawConfigParser.__init__(self, defaults=defaults, dict_type=dict_type,
                 allow_no_value=allow_no_value)

    def loadConfigFromFile(self, path):
        if not path:
            raise AttributeError("Error: no configuration file specified to load.")

        # get an absolute path for the file

        self.__cfgfile__ = os.path.abspath(os.path.expanduser(path))

        # Load the configuration file
        self.read(self.__cfgfile__)

        # if we had a file path, but didn't load any option items, then something
        # went wrong
        if len(self.as_dict) <= 0:
            raise IOError("Error: could not read any configuration options from file '" + path + "'.")

        self._initializeConfig()


    def default_get(self, section, option, default):
        """ If the config file does not contain the option requested or even the section
            that setting is in, return <default> back to the caller instead of raising an
            exception.
        """

        try:
            return ConfigParser.RawConfigParser.get(self, section, option)
        except ConfigParser.NoOptionError:
            return default
        except ConfigParser.NoSectionError:
            return default

    def get(self, section, option, defaultNone=True):
        """ Override the get method to default to return none in the case
            where we don't actually have that config setting or section.  Caller
            can still use the standard .get() behavior by specifying defaultNone=False
        """
        if defaultNone or defaultNone == None:
            return self.default_get(section, option, None)
        else:
            return ConfigParser.RawConfigParser.get(self, section, option)

    def _initializeConfig(self):
        """ Sets up all the base properties including output logging.  Must be
            called after a config file has been loaded
        """
        #
        # Set up the output folder property
        #
        outpath = self.get("Output", "output_folder")
        if outpath:
            self._output_folder = outpath
        elif self.__cfgfile__:
            self._output_folder = os.path.dirname(self.__cfgfile__)
        self._output_folder = os.path.expanduser(self._output_folder)

        #
        #
        # Set up output logging
        #
        #
        self._logger = PrettyLogger(self._nameprefix, level=self._logginglevel)

        # set the log line entry display format
        fmt = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')

        # set the logging level based on the config file value or
        # default to INFO level if not set
        level = self.default_get("Output", "logging_level", logging.INFO)
        self._logger.setLevel(level)

        #
        # Set logging to go to both a file rotated at midnight each day
        # and to stdout
        #
        stdouthandler = logging.StreamHandler()
        stdouthandler.setFormatter(fmt)
        self._logger.addHandler(stdouthandler)

#
        self._logfilename = os.path.expanduser(os.path.join(self.output_folder, "pocket_report.log"))
#         self._logfilename = os.path.join(self.output_folder, "logs", "pocket_report.log")
#        self.setupOutputFolder(os.path.dirname(self._logfilename))


        filehandler = logging.handlers.TimedRotatingFileHandler(self._logfilename, when='midnight')
        filehandler.setFormatter(fmt)
        self._logger.addHandler(filehandler)

        self._logger.info("Logging output to file: '" + self._logfilename +"'")

    def debugprint(self):
        self._logger.log_pretty("INFO", "Configuration File Settings: ", self.as_dict)


    def setupOutputFolder(self, folderpath):
        """ Creates the necessary folders in the path specified,
            including the actual folder we care about and any parents
            it needs.   Also handles expanding user paths ("~") and
            relative paths to their full absolute values.

            Returns the absolute path to the folder.
        """
        if not folderpath:
            raise AttributeError("Error: cannot setup output folder path.  No path specified.")

        if str(folderpath).__contains__("~"):
            folderpath = os.path.expanduser(folderpath)

        folderpath = os.path.abspath(folderpath)

        outputfolder = os.path.abspath(folderpath + "/")
        if not os.path.exists(outputfolder):
            os.makedirs(outputfolder)

        return outputfolder

    @property
    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d

    @property
    def as_json(self):
        import json
        config = ConfigParser
        config.__class__ = self
        strjs = '{} {}\n'.format(json.dumps(config, sort_keys=True, indent=4, separators=(',', ': ')), config)
        return strjs

    @property
    def logger(self):
        return self._logger

    @property
    def configfile(self):
        return self.__cfgfile__

    @configfile.setter
    def configfile(self, value):
        if not value:
            raise AttributeError("Configuration file path is required.")

        path = value
        if str(path).__contains__("~"):
            path = os.path.expanduser(path)

        self.__configfile__ = os.path.abspath(path)

    @property
    def name(self):
        return self._nameprefix

    @property
    def output_folder(self):
        return self._output_folder

