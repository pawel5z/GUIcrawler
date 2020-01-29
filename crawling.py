import queue
import urllib.request
import threading
import re
import bs4
import time

class CrawlResult:
    """ 
    This class stores crawl data.
    """
    def __init__(self, startAddress, maxDepth, startTime, endTime, results):
        """
        Creates CrawlResult object.

        :type startAddress: string
        :param startAddress: Address of site from which crawl began.

        :type maxDepth: int
        :param maxDepth: The biggest distance from start site crawler can reach.

        :type startTime: float
        :param startTime: Time at which crawl started.
        
        :type endTime: float
        :param endTimeL Time at which crawl ended.

        :type results: dict
        :param results: Dictionary containing crawl results for each of visited sites.
        """

        self.startAddress = startAddress
        self.maxDepth = maxDepth
        self.startTime = startTime
        self.endTime = endTime
        self.crawlTime = endTime - startTime
        self.results = results
    
    def jsonify(self):
        """
        Returns CrawlResult object in JSON format.
        """

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
        """
        Creates CrawlResult object from JSON file.

        :type fJSON: dict
        :param fJSON: JSON object to load the data from.
        """

        return cls(fJSON["startAddress"], fJSON["maxDepth"], fJSON["startTime"], fJSON["endTime"], fJSON["results"])

def downloadSite(toVisit: queue.Queue, downloaded: queue.Queue, l: threading.Lock):
    """
    Downloads sites.

    :type toVisit: queue.Queue
    :param toVisit: Stores unvisited sites.

    :type downloaded: queue.Queue
    :param downloaded: Stores downloaded sites.

    :type l: threading.Lock
    :param l: Thread lock used to secure thread-unsafe operations.
    """

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
    """
    Returns function that searches HTML document for sentences containing specified word.

    :type word: string
    :param word: Word to search for in sentences.

    :type caseSensitive: bool
    :param caseSensitive: Flag specifying whether capital and lowercase letters should be treated as the same.

    :type tagsListToSearch: list
    :param tagsListToSearch: List of tags inside of which searching should be performed.
    """
    
    def aux(siteHTML):
        if caseSensitive:
            regEx = re.compile(r'((?:(?:\b' + word + r'\b)|(?:[A-Z](?:[a-zA-Z0-9, \'])*?\b' + word + r'\b))(?:[a-zA-Z0-9, \'])*?(?:(?:\.\.\.)|[\.\!\?]){1})')
        else:
            regEx = re.compile(r'((?:(?:\b' + word + r'\b)|(?:[A-Z](?:[a-zA-Z0-9, \'])*?\b' + word + r'\b))(?:[a-zA-Z0-9, \'])*?(?:(?:\.\.\.)|[\.\!\?]){1})', re.IGNORECASE)
        bs = bs4.BeautifulSoup(siteHTML, 'lxml')
        sentencesContainingWord = []
        for tag in bs.body.findAll(tagsListToSearch):
            for match in regEx.finditer(tag.text):
                if not match.group() in sentencesContainingWord:
                    sentencesContainingWord.append(match.group())
        return sentencesContainingWord
    return aux

def searchForWord(word: str, caseSensitive: bool, tagsListToSearch: list):
    """
    Returns function that searches HTML document for specified word.

    :type word: string
    :param word: Word to search for in HTML tags.

    :type caseSensitive: bool
    :param caseSensitive: Flag specifying whether capital and lowercase letters should be treated as the same.

    :type tagsListToSearch: list
    :param tagsListToSearch: List of tags inside of which searching should be performed.
    """

    def aux(siteHTML):
        if caseSensitive:
            regEx = re.compile(r'\b' + word + r'\b')
        else:
            regEx = re.compile(r'\b' + word + r'\b', re.IGNORECASE)
        bs = bs4.BeautifulSoup(siteHTML, 'lxml')
        tagsContainingWord = []
        for tag in bs.findAll(tagsListToSearch):
            for match in regEx.finditer(tag.text):
                if not match.group() in tagsContainingWord:
                    tagsContainingWord.append(match.group())
        return tagsContainingWord
    return aux

def searchForPattern(pattern: str, caseSensitive: bool, tagsListToSearch: list):
    """
    Returns function that searches HTML texts matching specified pattern.

    :type pattern: string
    :param pattern: Regular expression.

    :type caseSensitive: bool
    :param caseSensitive: Flag specifying whether capital and lowercase letters should be treated as the same.

    :type tagsListToSearch: list
    :param tagsListToSearch: List of tags inside of which searching should be performed.
    """

    def aux(siteHTML):
        if caseSensitive:
            regEx = re.compile(pattern)
        else:
            regEx = re.compile(pattern, re.IGNORECASE)
        bs = bs4.BeautifulSoup(siteHTML, 'lxml')
        tagsContainingMatch = []
        for tag in bs.findAll(tagsListToSearch):
            for match in regEx.finditer(tag.text):
                if not match.group() in tagsContainingMatch:
                    tagsContainingMatch.append(match.group())
        return tagsContainingMatch
    return aux

def processSite(toVisit: queue.Queue, downloaded: queue.Queue, visited: set, actionRes: list, maxDepth, aAttrsFilter: dict, action, l: threading.Lock):
    """
    Gets all links from site and returns result of action on it.

    :type toVisit: queue.Queue
    :param toVisit: Stores unvisited sites.

    :type downloaded: queue.Queue
    :param downloaded: Stores downloaded sites.

    :type visited: set
    :param visited: Stores visited sites.

    :type actionRes: list
    :param actionRes: Results of action performed on each of visited sites.

    :type maxDepth: int
    :param maxDepth: The biggest distance from start site crawler can reach.

    :type aAttrsFilter: dict
    :param aAttrsFilter: Contains allowed attribute values of <a> tags.

    :type action: function
    :param action: Action to perform on downloaded sites.

    :type l: threading.Lock
    :param l: Thread lock used to secure thread-unsafe operations.
    """
    
    while downloaded.empty() == False:
        siteAddress, dist, siteHTML = downloaded.get()
        l.acquire()
        visited.add(siteAddress)
        l.release()
        if dist < maxDepth or maxDepth == -1:
            bs = bs4.BeautifulSoup(siteHTML, 'lxml')
            for tag in bs.body.findAll('a', attrs=aAttrsFilter):
                link = tag.get('href')
                if not re.match(r'#.*', link): # don't try to follow anchors
                    matchObj1 = re.match(r'(\/.*)', link) # hrefs of type '/link' which should be interpreted as 'root/link'
                    matchObj2 = re.match(r'(\/\/.+)', link) # hrefs of type '//link' which should be interpreted as 'http://link'
                    if matchObj2:
                        fullLink = r'http:' + matchObj2.group(1)
                    elif matchObj1:
                        fullLink = re.match(r'(.+)\/', siteAddress).group(1) + matchObj1.group(1)
                    else:
                        fullLink = link # regular hrefs of type http[s]://link
                    matchObj = re.match(r'(.+)\#.*', fullLink) # escape anchors
                    if matchObj:
                        fullLink = matchObj.group(1)
                    if not fullLink in visited:
                        toVisit.put((fullLink, dist+1))

        result = action(siteHTML)
        if len(result) != 0:
            l.acquire()
            actionRes.append((siteAddress, result))
            l.release()

def crawl(startPage, maxDepth, aAttrsFilter, action):
    """
    Traverses the Internet.

    :type startPage: string
    :param startPage: Address of site from which crawl begins.

    :type maxDepth: int
    :param maxDepth: The biggest distance from start site crawler can reach.

    :type aAttrsFilter: dict
    :param aAttrsFilter: Contains allowed attribute values of <a> tags.

    :type action: function
    :param action: Action to perform on downloaded sites.
    """

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
