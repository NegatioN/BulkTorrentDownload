__author__ = 'NegatioN'

import requests
from bs4 import BeautifulSoup
import re
import os

#TODO thread-optimise download of torrents and crawling of pages.

class OutColors:
    DEFAULT = '\033[0m'
    BW = '\033[1m'
    LG = '\033[0m\033[32m'
    LR = '\033[0m\033[31m'

#get contents of an url
def getContents(url):
    try:
        cont = requests.get(url)
    except requests.exceptions.RequestException as e:
        raise SystemExit('\n' + OutColors.LR + str(e))
    return cont

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
    stringRes = select_resolution()

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
    return linktitle

def select_resolution():
    arr = [480, 720, 1080]
    print("Press 1 for 480p, 2 for 720p or 3 for 1080p")
    userin = input("select resolution >>")

    if int(userin) < 4 and int(userin) > 0:
        return userin
    else:
        print("Write a number 1-3")
        select_resolution()