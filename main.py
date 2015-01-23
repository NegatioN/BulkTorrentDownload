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

from bs4 import BeautifulSoup
import os
import re
import requests
import subprocess
import sys
import tabulate
import time

#TODO implement graphical progress-bar?

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

#get contents of an url
def getContents(url):
    try:
        cont = requests.get(url)
    except requests.exceptions.RequestException as e:
        raise SystemExit('\n' + OutColors.LR + str(e))
    return cont
def find_torrents(link):
    torrent_links = []
    seriesPageNum = 1
    url = link + 'page/' + str(seriesPageNum)
    newCont = getContents(url)

    #finds all pages with selection of torrents for given episode.
    while newCont.status_code != 404:
        newSoup = BeautifulSoup(newCont.content)
        ### Counts the number of episodes on the current series site
        ul =  newSoup.find_all("ul", {'class': 'catg_list'})
        for uls in ul:
            for a in uls.findAll('a'):
                torrent_links.append(a['href'])

        seriesPageNum+=1
        url = link + 'page/' + str(seriesPageNum)
        newCont = getContents(url)

    #find a given torrent per episode for resolution-choice.
    stringRes = input("Set resolution(480, 720 or 1080): ")

    resolution = re.compile(stringRes)
    linktitle = []
    for link in torrent_links:
        newCont = getContents(link)
        newSoup = BeautifulSoup(newCont.content)
        ul =  newSoup.find_all("ul", {'class': 'catg_list'})
        for uls in ul:
            for a in uls.findAll('a'):
                #gets the first torrent that matches resolution setting
                if resolution.search(str(a.string)) and a.has_attr("href"):
                    var = a['href']
                    var = var.replace(" ", "")
                    titlelink = a.next, var
                    linktitle.append(titlelink)

                    #TODO download the file while finding it. Thereby making sure we can download an alternative version if
                    #we can't get the specified resolution.
                    break
    print(str(linktitle))
    return linktitle

def download_all_torrents(link):
    print("Finding torrents...")
    torrentTuples = find_torrents(link)
    print("Downloading Torrents...")
    title = 0
    url = 0
    for title, url in torrentTuples:
        download_torrent(title, url)


def download_torrent(title, url):
    print(OutColors.BW + 'Downloading >> ' + title)
    fname = os.getcwd() + '/' + title + '.torrent'
    # http://stackoverflow.com/a/14114741/1302018
    try:
        r = requests.get(url, stream=True)
        with open(fname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
    except requests.exceptions.RequestException as e:
        print('\n' + OutColors.LR + str(e) + '\nSomething went wrong with file: ' + title)
        print("Failed. Trying next torrent.")

    return fname


def aksearch():
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

    #holds all links to series in search
    href = []

#producer-part
    print("searching...")
    cont = getContents(url)
    count = 0
    while cont.status_code != 404:
        soup = BeautifulSoup(cont.content)

        for a in soup.find_all('a', href=re.compile(r'http://www.animetake.com/anime/')):
            if a.parent.name != 'li':
                link = a.get('href')
                if link not in href and re.search(queryInLink, link) != None:
                    href.append(link)
        ##goto next page of search
        pageNum+=1
        url = url_beg + str(pageNum) + search_url + query + after_url + '/'
        cont = getContents(url)



    # check if no torrents found
    if len(href) == 0:
        print('Series found: 0')
        aksearch()

    ###Do all remaining operations for all series-links gathered.
    title = []
    #goes through all hrefs to get the name of the series
    #also removes titles which does not have /Query/ in them
    for seriestitle in href:
        name=seriestitle.replace("http://www.animetake.com/anime/", "")
        name=name.replace("-", " ")
        name=name.replace("/", "")
        title.append(name)

    #gets number of episode-links for the given series (aka episodes to download)
    size = []
    print("Counting episodes...")
    for link in href:
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
        size.append(str(curSize))


    #size = [t.get_text() for t in soup.find_all('td', {'class':'nobr'}) ]
    #for table printing
    table = [[OutColors.BW + str(i+1) + OutColors.DEFAULT if (i+1) % 2 == 0 else i+1,
            OutColors.BW + title[i] + OutColors.DEFAULT if (i+1) % 2 == 0 else title[i],
            OutColors.BW + size[i] + OutColors.DEFAULT if (i+1) % 2 == 0 else size[i]] for i in range(len(href))]

    print()
    print(tabulate.tabulate(table, headers=['No.', 'Title', 'Episodes']))

    end = time.clock()      #time end
    spent = end-start
    print("time: " + str(spent)) #print time spent searching + counting

    # torrent selection
    print('\nSelect torrent: [ 1 - ' + str(len(href)) + ' ] or [ M ] to go back to main menu or [ Q ] to quit')
    torrent = select_torrent()
    if torrent == 'Q' or torrent == 'q':
        sys.exit(0)
    elif torrent == 'M' or torrent == 'm':
        aksearch()
    else:
        if int(torrent) <= 0 or int(torrent) > len(href):
            print('Use eyeglasses...')
        else:
            download_all_torrents(href[int(torrent)-1])
            #fname = download_torrent(href[int(torrent)-1])
            #subprocess.Popen(['xdg-open', fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            aksearch()


if __name__ == '__main__':
    try:
        aksearch()
    except KeyboardInterrupt:
        print('\nHuha!')