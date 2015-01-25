#!/usr/bin/env python

__author__ = 'Joakim Rishaug'

# -*- coding: utf-8 -*-
# Agreement: You can use, modify, or redistribute this tool under the terms of GNU General Public License (GPLv3).
# This tool is for educational purposes only. Any damage you make will not affect the author.

#Inspired by pantuts' https://github.com/pantuts/asskick kickass torrent-console.
# Dependencies:
# requests: https://pypi.python.org/pypi/requests
# beautifulSoup4: https://pypi.python.org/pypi/beautifulsoup4/4.3.2
# tabulate: https://pypi.python.org/pypi/tabulate

from multiprocessing.pool import ThreadPool
from bs4 import BeautifulSoup
import os
import re
import requests
import sys
import tabulate
import time
import arrangeTorrents
import workerpool
import downloadTorrents
from queue import Queue



#TODO implement graphical progress-bar?
#TODO implement sorting of output series-list
#TODO optimize speed of series searching


class CountJob(workerpool.Job):
    "Job for counting episodes in a given series"
    def __init__(self, url, titlesizelink):
        self.url = url # The url we'll need to download when the job runs
        self.titlesizelink = titlesizelink #array for keeping track of name, size and link
    def run(self):
        returnVal = countEpisodes(self.url)
        self.titlesizelink.append(returnVal)

class ProduceHrefJob(workerpool.Job):
    #Job for getting the next Href for a search of series
    #e.g. pagenum 1,2,3,4,5 of search
    def __init__(self, cont, urlarr, pagenum, hrefqueue, href):
        self.hrefqueue = hrefqueue
        self.pagenum = pagenum #which pagenum to start checking.
        self.cont = cont
        self.href = href
        self.urlarr = urlarr
    def run(self):
        returnHrefs = produceHref(self.cont, self.urlarr, self.pagenum,self.href)

        for returnhref in returnHrefs:
            self.hrefqueue.put(returnhref)


def combineLink(*linkarr): #hack way of getting the object which is somehow split into an array of chars???
    link = ""
    for char in linkarr:
        link += char
    return link

def produceHref(cont, urlarr, pageNum, href):
    limitNum = pageNum+10
    url_beg = urlarr[0]
    search_url = urlarr[1]
    query = urlarr[2]
    after_url = urlarr[3]
    queryInLink = urlarr[4]

    hrefs = []
    while cont.status_code != 404 and pageNum < limitNum:
        soup = BeautifulSoup(cont.content)

        for a in soup.find_all('a', href=re.compile(r'http://www.animetake.com/anime/')):
            if a.parent.name != 'li':
                link = a.get('href')
                if link not in href and re.search(queryInLink, link) != None:
                    href.append(link)
                    hrefs.append(link)
        pageNum+=1 ##goto next page of search
        url = url_beg + str(pageNum) + search_url + query + after_url + '/'
        cont = getContents(url)
    return hrefs


#consume a series and count all episodes per thread.
def countEpisodes(*linkarr):
    link = combineLink(*linkarr)

    #define name of the series.
    name=link.replace("http://www.animetake.com/anime/", "")
    name=name.replace("-", " ")
    name=name.replace("/", "")


    seriesPageNum = 1
    url = link + 'page/' + str(seriesPageNum)
    nextCont = getContents(url)

    curSize = 0

    while nextCont.status_code != 404:
        newCont = nextCont
        newSoup = BeautifulSoup(newCont.content)
        seriesPageNum+=1
        url = link + 'page/' + str(seriesPageNum)
        nextCont = getContents(url)

    curSize += ((seriesPageNum-2)*28) #a page has 28 episodes max
### Counts the number of episodes on the current series site
    for ul in newSoup.find_all("ul", {'class': 'catg_list'}):
        for li in ul.findAll('li'):
            curSize+=1
    nameSize = name, str(curSize), link
    return nameSize



class OutColors:
    DEFAULT = '\033[0m'
    BW = '\033[1m'
    LG = '\033[0m\033[32m'
    LR = '\033[0m\033[31m'

def helper():
    print(OutColors.DEFAULT + "\nSearch torrents from Animetake.com")

def select_torrent():
    torrent = input('>> ')
    return torrent

def select_resolution():
    arr = [480, 720, 1080]
    print("Press 1 for 480p, 2 for 720p or 3 for 1080p")
    userin = input("select resolution >>")

    if int(userin) < 4 and int(userin) > 0:
        return userin
    else:
        print("Write a number 1-3")
        select_resolution()


#get contents of an url
def getContents(url):
    try:
        cont = requests.get(url)
    except requests.exceptions.RequestException as e:
        raise SystemExit('\n' + OutColors.LR + str(e))
    return cont


def aksearch():
    hrefqueue = Queue() #holds all links to series yielded by search
    titleSizeLink = [] #holds name, num of episodes, link to series.
    href = []


    helper()
    pageNum = 1
    url_beg = 'http://www.animetake.com/page/'
    search_url = '?s='
    after_url = '&x=0&y=0'


    query = input('Type query: ')
    start = time.clock()

    #replace space with + for search
    query = query.replace(" ", "+")
    url = url_beg + str(pageNum) + search_url + query + after_url
    queryInLink = query.replace("+", "-")

    urlarr = [url_beg, search_url, query, after_url, queryInLink]
    print("searching...")
    cont = getContents(url)

    pool = workerpool.WorkerPool(size=5)

    #checks every tenth page, and uses threads to check the subsequent pages
    while cont.status_code != 404:
        job = ProduceHrefJob(cont, urlarr,pageNum,hrefqueue, href)
        pool.put(job)

        pageNum+=10
        url = url_beg + str(pageNum) + search_url + query + after_url + '/'
        cont = getContents(url)

    pool.shutdown()
    pool.wait()

    end = time.clock()      #time end
    spent = end-start
    print("time: " + str(spent)) #print time spent searching + counting

    ###Do all remaining operations for all series-links gathered.
    #gets number of episode-links for the given series (aka episodes to download)
    print("Counting episodes...")

    pool = workerpool.WorkerPool(size=5) # Initialize a pool of 5 threads

    while not hrefqueue.empty():
        job = CountJob(hrefqueue.get(), titleSizeLink)
        pool.put(job)

    pool.shutdown()
    pool.wait()



    # check if no torrents found
    if len(href) == 0:
        print('Series found: 0')
        aksearch()

    #for table printing
    table = []
    for index, value in enumerate(titleSizeLink):
        title, size, link = value
        #table format: index, title, size
        if index % 2 == 0:
            row = OutColors.BW + str(index+1) + OutColors.DEFAULT, OutColors.BW + title + OutColors.DEFAULT, OutColors.BW + size + OutColors.DEFAULT
        else:
            row = str(index+1), title, size
        table.append(row)

    print()
    print(tabulate.tabulate(table, headers=['No.', 'Title', 'Episodes']))

    end = time.clock()      #time end
    spent = end-start
    print("time: " + str(spent)) #print time spent searching + counting

    # torrent selection
    print('\nSelect series: [ 1 - ' + str(len(titleSizeLink)) + ' ] or [ M ] to go back to main menu or [ Q ] to quit')
    torrent = select_torrent()
    if torrent == 'Q' or torrent == 'q':
        sys.exit(0)
    elif torrent == 'M' or torrent == 'm':
        aksearch()
    else:
        if int(torrent) <= 0 or int(torrent) > len(titleSizeLink):
            print('The number you wrote is not present in the list...')
        else:
            quad = titleSizeLink.__getitem__(int(torrent)-1)
            title, size, link in quad
            path = arrangeTorrents.createFolder(title, "torrents")
            os.chdir(path)
            downloadTorrents.download_all_torrents(link)
            aksearch()


if __name__ == '__main__':
    try:
        aksearch()
    except KeyboardInterrupt:
        print('\nHuha!')