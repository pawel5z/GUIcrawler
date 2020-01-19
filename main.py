import urllib.request
import threading
import re
import queue
import bs4
import time
import pickle
import datetime
import json

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class CrawlResult:
    def __init__(self, startAddress, maxDepth, startTime, endTime, results):
        self.startAddress = startAddress
        self.maxDepth = maxDepth
        self.startTime = startTime
        self.endTime = endTime
        self.crawlTime = endTime - startTime
        self.results = results
    
    def jsonify(self):
        return {
            "startAddress": self.startAddress,
            "maxDepth": self.maxDepth,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "crawlTime": self.crawlTime,
            "results": self.results
        }

    @classmethod
    def fromJSON(cls, fJSON):
        return cls(fJSON["startAddress"], fJSON["maxDepth"], fJSON["startTime"], fJSON["endTime"], fJSON["results"])

def comaSepToList(s: str):
    if s == '':
        return []
    return s.split(',')

def downloadSite(toVisit: queue.Queue, downloaded: queue.Queue, l: threading.Lock):
    while toVisit.empty() == False:
        siteAddress, dist = toVisit.get()
        try:
            req = urllib.request.urlopen(siteAddress, timeout=10)
            siteHTML = req.read().decode('ascii', 'ignore')
            downloaded.put((siteAddress, dist, siteHTML))
        except EnvironmentError as e:
            l.acquire()
            print('\n', siteAddress, e)
            l.release()

def searchForSentencesContainingWord(word: str, caseSensitive: bool, tagsListToSearch: list):
    def aux(siteHTML):
        if caseSensitive:
            regEx = re.compile(r'((?:(?:\b' + word + r'\b)|(?:[A-Z](?:[a-zA-Z0-9, \'])*?\b' + word + r'\b))(?:[a-zA-Z0-9, \'])*?(?:(?:\.\.\.)|[\.\!\?]){1})')
        else:
            regEx = re.compile(r'((?:(?:\b' + word + r'\b)|(?:[A-Z](?:[a-zA-Z0-9, \'])*?\b' + word + r'\b))(?:[a-zA-Z0-9, \'])*?(?:(?:\.\.\.)|[\.\!\?]){1})', re.IGNORECASE)
        bs = bs4.BeautifulSoup(siteHTML, 'lxml')
        sentencesContainingWord = []
        for tag in bs.body.findAll(tagsListToSearch):
            for sentence in regEx.finditer(tag.text):
                if not sentence.group() in sentencesContainingWord:
                    sentencesContainingWord.append(sentence.group())
        return sentencesContainingWord
    return aux

def processSite(toVisit: queue.Queue, downloaded: queue.Queue, visited: set, actionRes: list, maxDepth, aAttrsFilter: dict, action, l: threading.Lock):
    while downloaded.empty() == False:
        siteAddress, dist, siteHTML = downloaded.get()
        visited.add(siteAddress)
        if dist < maxDepth or maxDepth == -1:
            bs = bs4.BeautifulSoup(siteHTML, 'lxml')
            for tag in bs.body.findAll('a', attrs=aAttrsFilter):
                if re.match(r'.+\..+\..+', tag.get('href')) and (not tag.get('href') in visited):
                        toVisit.put((tag.get('href'), dist+1))

        result = action(siteHTML)
        if len(result) != 0:
            l.acquire()
            actionRes.append((siteAddress, result))
            l.release()

def crawl(startPage, maxDepth, aAttrsFilter, action):
    toVisit = queue.Queue()
    downloaded = queue.Queue()
    visited = set()
    actionRes = []
    l = threading.Lock()
    startTime = time.time()

    toVisit.put((startPage, 0))
    while toVisit.empty() == False:
        threads = []
        # downloading sites
        for _ in range(max(1, min(toVisit.qsize(), 8))):
            t = threading.Thread(target=downloadSite, args=(toVisit, downloaded, l))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        threads.clear()

        # processing sites
        for _ in range(max(1, min(downloaded.qsize(), 8))):
            t = threading.Thread(target=processSite, args=(toVisit, downloaded, visited, actionRes, maxDepth, aAttrsFilter, action, l))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        threads.clear()
    
    return CrawlResult(startPage, maxDepth, startTime, time.time(), actionRes)

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
        self.res = crawl(   self.builder.get_object("c1StartAddress_entry").get_text(),
                            self.builder.get_object("c1MaxDepth_spinButton").get_value_as_int(),
                            hyplnAttrSpec,
                            searchForSentencesContainingWord(   self.builder.get_object("c1WordToSearch_entry").get_text(),
                                                                self.builder.get_object("c1_caseSensitive_checkButton").get_active(),
                                                                comaSepToList(self.builder.get_object("c1TagToSearch_entry").get_text())))

    def on_crawlResultsWindow_show(self, widget, data=None):
        self.builder.get_object("res_startSite").set_text(self.res.startAddress)
        self.builder.get_object("res_maxDepth").set_text(str(self.res.maxDepth))
        self.builder.get_object("res_startTime").set_text(datetime.datetime.fromtimestamp(self.res.startTime).strftime("%A, %B %d, %Y %I:%M:%S"))
        self.builder.get_object("res_endTime").set_text(datetime.datetime.fromtimestamp(self.res.endTime).strftime("%A, %B %d, %Y %I:%M:%S"))
        self.builder.get_object("res_crawlTime").set_text(str(self.res.crawlTime))

        resultsTreeStore = self.builder.get_object("resultsTreeStore")
        resultsTreeStore.clear()
        for siteAddress, foundOnSite in self.res.results:
            bIter = resultsTreeStore.append(None, [siteAddress])
            for singleResult in foundOnSite:
                resultsTreeStore.append(bIter, [singleResult])

    def on_saveResultsButton_clicked(self, widget, data=None):
        widget.show()
    
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

app = GUIcrawler()
app.window.show_all()
Gtk.main()
# /╲/( ͡° ͡° ͜ʖ ͡° ͡°)/\╱\