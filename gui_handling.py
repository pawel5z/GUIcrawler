import re
import pickle
import datetime
import json
import threading

from crawling import crawl, CrawlResult, searchForSentencesContainingWord, searchForWord, searchForPattern

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

def comaSepToList(s: str):
    """
    Returns [] if s is empty or list of strings which were originally separated by commas in s.

    :type s: string
    :param s: String to process.
    """

    if s == '':
        return []
    return s.split(',')

def parseAttrSpec(text):
    """
    Creates dictionary from text in this way:

    href:foo,bar
    id:foo

    will be converted to

    {
        'href': ['foo', 'bar'],
        'id': ['foo']
    }
    
    :type text: string
    :param text: Text to process.
    """

    hyplnAttrSpec = {}
    for line in text.split(sep='\n'):
        if re.match(r'[a-zA-Z0-9\-\_]+:([a-zA-Z0-9\-\_ ]+)(,([a-zA-Z0-9\-\_ ]+))*', line):
            attr, valString = line.split(sep=':')
            hyplnAttrSpec[attr] = comaSepToList(valString)
    if hyplnAttrSpec == {}:
        hyplnAttrSpec = None
    return hyplnAttrSpec

def parseStartSiteAddress(address):
    """
    Adds '/' to the end of address if there isn't already.

    :type address: string
    :param address: Url string.
    """
    if len(address) == 0:
        return address
    if address[len(address)-1] != '/':
        address += '/'
    return address

class GUIcrawler:
    """
    Class handling GUI interactions.
    """

    def __init__(self):
        """
        Creates GUIcrawler object and initializes main application window.
        """
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file('app-interface.glade')
        self.window = self.builder.get_object('mainWindow')
        self.builder.connect_signals(self)
        self.res = None

    def quitApp(self, widget, data=None):
        """
        Quits application.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        Gtk.main_quit()

    def invokeWidget(self, widget, data=None):
        """
        Show widget passed as parameter.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        widget.show()

    def hideWidget(self, widget, data=None):
        """
        Hides widget passed as parameter.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        widget.hide()
        return True
    
    def on_c1GoButton_clicked(self, widget, data=None):
        """
        Starts crawling searching for words in sentences.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        buffer = self.builder.get_object("c1HyplinkAttrSpec_textBuffer")
        hyplnAttrSpec = parseAttrSpec(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
        
        startSite = self.builder.get_object("c1StartAddress_entry").get_text()
        startSite = parseStartSiteAddress(startSite)

        def aux():
            self.res = crawl(   startSite,
                            self.builder.get_object("c1MaxDepth_spinButton").get_value_as_int(),
                            hyplnAttrSpec,
                            searchForSentencesContainingWord(   self.builder.get_object("c1WordToSearch_entry").get_text(),
                                                                self.builder.get_object("c1_caseSensitive_checkButton").get_active(),
                                                                comaSepToList(self.builder.get_object("c1TagToSearch_entry").get_text())))
            GLib.idle_add(widget.show_all)

        t = threading.Thread(target=aux)
        t.start()
    
    def on_c2GoButton_clicked(self, widget, data=None):
        """
        Starts crawling searching for words.

        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        buffer = self.builder.get_object("c2HyplinkAttrSpec_textBuffer")
        hyplnAttrSpec = parseAttrSpec(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
        
        startSite = self.builder.get_object("c2StartAddress_entry").get_text()
        startSite = parseStartSiteAddress(startSite)

        def aux():
            self.res = crawl(   startSite,
                            self.builder.get_object("c2MaxDepth_spinButton").get_value_as_int(),
                            hyplnAttrSpec,
                            searchForWord(  self.builder.get_object("c2WordToSearch_entry").get_text(),
                                            self.builder.get_object("c2_caseSensitive_checkButton").get_active(),
                                            comaSepToList(self.builder.get_object("c2TagToSearch_entry").get_text())))
            GLib.idle_add(widget.show_all)

        t = threading.Thread(target=aux)
        t.start()

    def on_c3GoButton_clicked(self, widget, data=None):
        """
        Starts crawling searching for texts matching specified pattern.

        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        buffer = self.builder.get_object("c3HyplinkAttrSpec_textBuffer")
        hyplnAttrSpec = parseAttrSpec(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
        
        startSite = self.builder.get_object("c3StartAddress_entry").get_text()
        startSite = parseStartSiteAddress(startSite)

        def aux():
            self.res = crawl(   startSite,
                            self.builder.get_object("c3MaxDepth_spinButton").get_value_as_int(),
                            hyplnAttrSpec,
                            searchForPattern(   self.builder.get_object("c3PatternToSearch_entry").get_text(),
                                                self.builder.get_object("c3_caseSensitive_checkButton").get_active(),
                                                comaSepToList(self.builder.get_object("c3TagToSearch_entry").get_text())))
            GLib.idle_add(widget.show_all)

        t = threading.Thread(target=aux)
        t.start()

    def on_crawlResultsWindow_show(self, widget, data=None):
        """
        Fills labels with data in results window.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        self.builder.get_object("res_startSite").set_text(self.res.startAddress)
        self.builder.get_object("res_maxDepth").set_text(str(self.res.maxDepth))
        self.builder.get_object("res_startTime").set_text(datetime.datetime.fromtimestamp(self.res.startTime).strftime("%A, %d %B, %Y %I:%M:%S"))
        self.builder.get_object("res_endTime").set_text(datetime.datetime.fromtimestamp(self.res.endTime).strftime("%A, %d %B, %Y %I:%M:%S"))
        self.builder.get_object("res_crawlTime").set_text(str(self.res.crawlTime))

        resultsTreeStore = self.builder.get_object("resultsTreeStore")
        resultsTreeStore.clear()
        for siteAddress, foundOnSite in self.res.results:
            bIter = resultsTreeStore.append(None, [siteAddress])
            for singleResult in foundOnSite:
                resultsTreeStore.append(bIter, [singleResult])
    
    def on_saveButton_clicked(self, widget, data=None):
        """
        Saves crawl results file.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        fileTypeComboBox = self.builder.get_object("fileTypeComboBox")
        model = fileTypeComboBox.get_model()
        curId = fileTypeComboBox.get_active()
        readFileName = widget.get_filename()
        if model[curId][0] == "*.store":
            if re.search(r'\.store$', readFileName):
                savedFileName = readFileName
            else:
                savedFileName = readFileName + '.store'
            with open(savedFileName, 'wb') as f:
                pickle.dump(self.res, f)
        elif model[curId][0] == "*.json":
            if re.search(r'\.json$', readFileName):
                savedFileName = readFileName
            else:
                savedFileName = readFileName + '.json'
            with open(savedFileName, 'w') as f:
                json.dump(self.res.jsonify(), f)
    
    def on_openButton_clicked(self, widget, data=None):
        """
        Opens crawl results file.
        
        :type widget: Gtk.Widget
        :param widget: Widget handling by this method.

        :type data: any
        :param data: Additional data.
        """

        fname = widget.get_filename()
        if re.search(r"\.store$", fname):
            with open(fname, 'rb') as f:
                self.res = pickle.load(f)
        elif re.search(r"\.json$", fname):
            with open(fname, 'r') as f:
                self.res = CrawlResult.fromJSON(json.load(f))
