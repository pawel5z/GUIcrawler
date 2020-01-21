import re
import pickle
import datetime
import json

from crawling import crawl, CrawlResult, searchForSentencesContainingWord

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

def comaSepToList(s: str):
    if s == '':
        return []
    return s.split(',')

class GUIcrawler:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('app-interface.glade')
        self.window = self.builder.get_object('mainWindow')
        self.builder.connect_signals(self)
        self.res = None
    
    def quitApp(self, widget, data=None):
        Gtk.main_quit()

    def invokeWidget(self, widget, data=None):
        widget.show()

    def hideWidget(self, widget, data=None):
        widget.hide()
        return True
    
    def on_c1GoButton_clicked(self, widget, data=None):
        buffer = self.builder.get_object("c1HyplinkAttrSpec_textBuffer")
        hyplnAttrSpec = {}
        for line in buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True).split(sep='\n'):
            if re.match(r'[a-zA-Z0-9\-\_]+:([a-zA-Z0-9\-\_ ]+)(,([a-zA-Z0-9\-\_ ]+))*', line):
                attr, valString = line.split(sep=':')
                hyplnAttrSpec[attr] = comaSepToList(valString)
        if hyplnAttrSpec == {}:
            hyplnAttrSpec = None

        startSite = self.builder.get_object("c1StartAddress_entry").get_text()
        if startSite[len(startSite)-1] != '/':
            startSite += '/'
        self.res = crawl(   startSite,
                            self.builder.get_object("c1MaxDepth_spinButton").get_value_as_int(),
                            hyplnAttrSpec,
                            searchForSentencesContainingWord(   self.builder.get_object("c1WordToSearch_entry").get_text(),
                                                                self.builder.get_object("c1_caseSensitive_checkButton").get_active(),
                                                                comaSepToList(self.builder.get_object("c1TagToSearch_entry").get_text())))

    def on_crawlResultsWindow_show(self, widget, data=None):
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
        fname = widget.get_filename()
        if re.search(r"\.store$", fname):
            with open(fname, 'rb') as f:
                self.res = pickle.load(f)
        elif re.search(r"\.json$", fname):
            with open(fname, 'r') as f:
                self.res = CrawlResult.fromJSON(json.load(f))
