from bs4 import BeautifulSoup
import urllib2
import sys
import json
import codecs
import re
import sqlite3 as lite
import csv
import os

def scraping():
    
    reload(sys)
    sys.setdefaultencoding('utf8')

    conn = lite.connect('orbis.sqlite',isolation_level = None)
    cur = conn.cursor()
    cur.execute('''create table holding
             (name varchar primary key,
              weight varchar,
              shares_held Integer)''')
    cur.close()
    query = "insert into holding values (?,?,?)"
    #url = "http://40.114.93.58:8111/"
    url = "file:///C:/Users/xz258/demo/SPY%20-%20SPDR%20S&P%20500%20ETF%20_%20State%20Street%20Global%20Advisors%20(SSGA).html#"
    #url = "https://us.spdrs.com/en/product/fund.seam?ticker=SPY"
    #p = urllib2.build_opener(urllib2.HTTPCookieProcessor).open(url)
    p = urllib2.urlopen(url)
    html = p.read()
    soup = BeautifulSoup(html, "html5lib")
    fundTable = soup.findAll(id="FUND_TOP_TEN_HOLDINGS")

    result = []
    allrows = fundTable[0].findAll('tr')
    for row in allrows:
        result.append([])
        allcols = row.findAll('td')
        for col in allcols:
            thestrings = [unicode(s) for s in col.findAll(text=True)]
            thetext = ''.join(thestrings)
            result[-1].append(thetext)

    i=1
    while i<len(result):
        dataTuple = tuple(result[i])
        #print (query,dataTuple)
        cur = conn.cursor()
        cur.execute(query,dataTuple)
        cur.close()
        i += 1
        print ("store succeeds")

    #print html
    #print (soup.prettify())
    #print(soup.find_all(id="FUND_TOP_TEN_HOLDINGS"))
