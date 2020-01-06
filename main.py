import urllib.request
import threading
import re
import queue
import bs4
import time
import pickle
import datetime

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

# convert string of allowed attributes to list of allowed attributes
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
            regEx = re.compile(r'(\b' + word + r'\b|[A-Z][^\.]*?\b' + word + r'\b).*?[\.!?](?:\s|$)')
        else:
            regEx = re.compile(r'(\b' + word + r'\b|[A-Z][^\.]*?\b' + word + r'\b).*?[\.!?](?:\s|$)', re.IGNORECASE)
        bs = bs4.BeautifulSoup(siteHTML, 'html.parser')
        sentencesContainingWord = []
        for tag in bs.body.findAll(tagsListToSearch):
            sentencesContainingWord.extend([sentence.group() for sentence in regEx.finditer(tag.text)])
        return sentencesContainingWord
    return aux

def processSite(toVisit: queue.Queue, downloaded: queue.Queue, visited: set, actionRes: list, maxDepth, aAttrsFilter: dict, action, l: threading.Lock):
    while downloaded.empty() == False:
        siteAddress, dist, siteHTML = downloaded.get()
        visited.add(siteAddress)
        bs = bs4.BeautifulSoup(siteHTML, 'html.parser')
        for tag in bs.body.findAll('a', attrs=aAttrsFilter):
            if re.match(r'.+\..+\..+', tag.get('href')) and (not tag.get('href') in visited):
                if dist < maxDepth:
                    toVisit.put((tag.get('href'), dist+1))

        result = action(siteHTML)
        if len(result) != 0:
            actionRes.append((siteAddress, result))

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
        for i in range(min(toVisit.qsize(), 8)):
            t = threading.Thread(target=downloadSite, args=(toVisit, downloaded, l))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        threads.clear()

        # processing sites
        for i in range(min(downloaded.qsize(), 8)):
            t = threading.Thread(target=processSite, args=(toVisit, downloaded, visited, actionRes, maxDepth, aAttrsFilter, action, l))
            t.start()
            threads.append(t)
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
    
    def on_mainWindow_destroy(self, widget, data=None):
        Gtk.main_quit()

    def invokeWidget(self, widget, data=None):
        widget.show()

    def hideWidget(self, widget, data=None):
        widget.hide()
        return True
    
    def on_c1GoButton_clicked(self, widget, data=None):
        pleasewaitWindow = self.builder.get_object('pleasewaitWindow')
        pleasewaitWindow.show()
        widget.hide()
        self.res = crawl(   self.builder.get_object("c1StartAddress_entry").get_text(),
                            self.builder.get_object("c1MaxDepth_spinButton").get_value_as_int(),
                            {
                                "id": comaSepToList(self.builder.get_object("c1_a_id_entry").get_text()),
                                "name": comaSepToList(self.builder.get_object("c1_a_name_entry").get_text()),
                                "class": comaSepToList(self.builder.get_object("c1_a_class_entry").get_text()),
                                "title": comaSepToList(self.builder.get_object("c1_a_title_entry").get_text())
                            },
                            searchForSentencesContainingWord(   self.builder.get_object("c1WordToSearch_entry").get_text(),
                                                                self.builder.get_object("c1_caseSensitive_checkButton").get_active(),
                                                                comaSepToList(self.builder.get_object("c1TagToSearch_entry").get_text())))
        pleasewaitWindow.hide()
        self.builder.get_object("crawlResultsWindow").show()

    def on_crawlResultsWindow_show(self, widget, data=None):
        self.builder.get_object("res_startSite").set_text(self.res.startAddress)
        self.builder.get_object("res_maxDepth").set_text(str(self.res.maxDepth))
        self.builder.get_object("res_startTime").set_text(datetime.datetime.fromtimestamp(self.res.startTime).strftime("%A, %B %d, %Y %I:%M:%S"))
        self.builder.get_object("res_endTime").set_text(datetime.datetime.fromtimestamp(self.res.endTime).strftime("%A, %B %d, %Y %I:%M:%S"))
        self.builder.get_object("res_crawlTime").set_text(str(self.res.crawlTime))

        resultsListStore = self.builder.get_object("resultsListStore")
        resultsListStore.clear()
        for siteAddress, foundOnSite in self.res.results:
            resultsListStore.append([siteAddress, '\n'.join(foundOnSite)])

    def on_saveResultsButton_clicked(self, widget, data=None):
        widget.show()
    
    def on_saveButton_clicked(self, widget, data=None):
        with open(widget.get_filename() + '.store', 'wb') as f:
            pickle.dump(self.res, f)
    
    def on_openButton_clicked(self, widget, data=None):
        with open(widget.get_filename(), 'rb') as f:
            self.res = pickle.load(f)

# crawlResult = crawl('https://www.python.org/', 1, {'id': [], 'name': [], 'class': [], 'title': []}, searchForSentencesContainingWord('Python', True, []))
# for s, r in crawlResult.results:
#     print(s, r)

app = GUIcrawler()
app.window.show_all()
Gtk.main()
