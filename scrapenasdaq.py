#!/usr/bin/env python
# -*- coding: utf-8 -*-

#============================================================================================================================
# python script that uses the selenium package to automatically brows http://www.nasdaqomxnordic.com/aktier/historiskakurser
# in order to download and store historical data on the Stockholm stock-exchange.
#============================================================================================================================
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import os
import subprocess
import shutil
import distutils.core
import datetime
import time

#====================
# User defined input:
#====================

OSX = False; # Set to true if you are working on a mac.

#====================================================================================================
# Here the user specifies the download location of the stockmarket data files and where to save them:
# Observe that you need to use double back-slash (\\) also in the end of the locations if you are 
# using a windows system, and a single slash (/) in the end of the locations otherwise.
#====================================================================================================
if OSX:
    DOWNLOADLOCATION = "/Users/?/Downloads/";
    SAVELOCATION = "/Users/?/AKTIER/DATA/";
else:
    DOWNLOADLOCATION = "C:\\Users\\pjannok\\Downloads\\";
    SAVELOCATION = "C:\\Users\\pjannok\\python_workspace\\AnalyzeCurrentPortfolio\\NASDAQOMX\\";
    TMPFILE = "C:\\Users\\pjannok\\python_workspace\\AnalyzeCurrentPortfolio\\NASDAQOMX\\TEMP";


#========================================================================================================
# Here the user fills in the start date defining how long back in history we should try and download data
#========================================================================================================
syear = '2015';
smonth = '01';
sday = '01';

#==========================
# END of user defined input
#==========================

#=================================================
# Clean csv-files from the download directory:
#=================================================
if OSX:
    command = 'rm '+DOWNLOADLOCATION+'*.csv';
    os.system(command);
else:
    command = 'DEL '+DOWNLOADLOCATION+'*.csv';
    os.system(command);



startdate = syear+'-'+smonth+'-'+sday;

mydriver = webdriver.Chrome();

stockname = [];
xpaths = [];



    
#========================================================================
# The list of companies to retrieve historic data for:
#========================================================================
# å = \u00E5
# ä = \u00E4
# ö = \u00F6
stockname.append("Castellum");
stockname.append("Industriv"+u'\u00E4'+"rden C");
stockname.append("Investor B");
#stockname.append("Latour B");
#stockname.append("Lundbergf");
#stockname.append("Kungsleden");
#stockname.append("Vitec");


# Here we get the date of today
eyear = str(datetime.datetime.now().year);
eday = str(datetime.datetime.now().day-1);
emonth = str(datetime.datetime.now().month);

if datetime.datetime.now().day-1 < 10: eday='0'+eday;
if datetime.datetime.now().month < 10: emonth ='0'+emonth;


enddate = eyear+'-'+emonth+'-'+eday;

xpaths.append('//*[@id="instSearchHistorical"]');
xpaths.append('//*[@id="FromDate"]');
xpaths.append('//*[@id="ToDate"]');

xpaths.append('//*[@id="exportExcel"]');




#================================================================================================================
# Loop over all big and medium sized companies at the Stockholm stock-market. Downloading historical data of the 
# stock from a date specified by the user to today.
#================================================================================================================
for name in stockname:
    mydriver.get('http://www.nasdaqomxnordic.com/aktier/historiskakurser');
    time.sleep(2);
    
    mydriver.find_element_by_xpath('//*[@id="instSearchHistorical"]').send_keys(name);
    time.sleep(1);
    
    mydriver.find_element_by_xpath('//*[@id="instSearchHistorical"]').send_keys(Keys.ARROW_DOWN);
    time.sleep(1);
    mydriver.find_element_by_xpath('//*[@id="instSearchHistorical"]').send_keys(Keys.ENTER);
    time.sleep(1);
    mydriver.find_element_by_xpath('//*[@id="FromDate"]').clear();
    time.sleep(1);
    mydriver.find_element_by_xpath('//*[@id="FromDate"]').send_keys(startdate);
    time.sleep(1);
    mydriver.find_element_by_xpath('//*[@id="ToDate"]').clear();
    time.sleep(1);
    mydriver.find_element_by_xpath('//*[@id="ToDate"]').send_keys(enddate);
    mydriver.find_element_by_xpath('//*[@id="ToDate"]').send_keys(Keys.TAB);
    time.sleep(2);
    mydriver.find_element_by_xpath('//*[@id="exportExcel"]').click();
    time.sleep(2);
    
    
if OSX:
    command = 'ls '+DOWNLOADLOCATION+'*.csv > '+TMPFILE;
    os.system(command);
else:
    command = 'DIR /b '+DOWNLOADLOCATION+'*.csv > '+TMPFILE;
    os.system(command);

with open(TMPFILE) as f:
    for line in f:
        downloadfile = line;
        downloadfile = downloadfile.strip('\n');
        if OSX:
            subprocess.call(["mv",DOWNLOADLOCATION+downloadfile,SAVELOCATION+downloadfile]);
        else:
            downl = DOWNLOADLOCATION+downloadfile;
            savefile = SAVELOCATION+downloadfile;
            shutil.move(downl, savefile);

if OSX:
    cmd = 'rm '+TMPFILE
    os.system(cmd);
else:
    cmd = 'DEL '+TMPFILE
    os.system(cmd);
    


# Here we close the driver after all the data has been downloaded
mydriver.close();

