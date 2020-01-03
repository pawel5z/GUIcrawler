import urllib.request
import threading
import re
import queue
import bs4
import time
import pickle

class CrawlResult:
    def __init__(self, startAddress, maxDepth, startTime, endTime, results):
        self.startAddress = startAddress
        self.maxDepth = maxDepth
        self.startTime = startTime
        self.endTime = endTime
        self.results = results

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

def searchForSentencesContainingWord(word, tagsListToSearch):
    def aux(siteHTML):
        regEx = re.compile(r'(\b' + word + r'\b|[A-Z][^\.]*?\b' + word + r'\b).*?[\.!?](?:\s|$)')
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

crawlResult = crawl('https://www.python.org/', 1, {}, searchForSentencesContainingWord('Python', []))
for e in crawlResult.results:
    print(e)