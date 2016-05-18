#imports
# QSTK Imports
import QSTK.qstkutil.qsdateutil as du
import QSTK.qstkutil.tsutil as tsu
import QSTK.qstkutil.DataAccess as da

# Third Party Imports
import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import sys
import csv
import os.path
import re
from scipy.optimize import minimize
from collections import namedtuple

class stock_csv(csv.Dialect):
    delimiter=';'
    quotechar='"'
    skipinitialspace=False
    lineterminator='\n'
    quoting=csv.QUOTE_MINIMAL

csv.register_dialect('stock_csv', stock_csv)


'''
' Reads data from Yahoo Finance
' @param li_startDate:  start date in list structure: [year,month,day] e.g. [2012,1,28]
' @param li_endDate:  end date in list structure: [year,month,day] e.g. [2012,12,31]
' @param ls_symbols:	list of symbols: e.g. ['GOOG','AAPL','GLD','XOM']
' @returns d_data:      dictionary structure of data mapped to keys e.g. 'open', 'close'
'''
def readData(li_startDate, li_endDate, ls_symbols):
    #Create datetime objects for Start and End dates (STL)
    dt_start = dt.datetime(li_startDate[0], li_startDate[1], li_startDate[2]);
    dt_end = dt.datetime(li_endDate[0], li_endDate[1], li_endDate[2]);

    #Initialize daily timestamp: closing prices, so timestamp should be hours=16 (STL)
    dt_timeofday = dt.timedelta(hours=16);

    #Get a list of trading days between the start and end dates (QSTK)
    ldt_timestamps = du.getNYSEdays(dt_start, dt_end, dt_timeofday);

    #Create an object of the QSTK-dataaccess class with Yahoo as the source (QSTK)
    c_dataobj = da.DataAccess('Yahoo', cachestalltime=0);

    #Keys to be read from the data
    ls_keys = ['open', 'high', 'low', 'close', 'volume', 'actual_close'];

    
    allStocksData={};
    
    csvFolderPath = "C:\\Users\\pjannok\\python_workspace\\AnalyzeCurrentPortfolio\\NASDAQOMX\\"
    for symbol in ls_symbols:
        
        for filename in os.listdir(csvFolderPath):
            pattern = symbol+"(.*).csv";
            if re.match(pattern, filename):
                
                d={};
                for i, row in enumerate(csv.reader(open(csvFolderPath+filename), 'stock_csv')):
                    if i==0:
                        separator=row;
                    elif i==1:
                        header=row;
                        header.pop()
                    else:
                        drow=dict(zip(header, row))
                        d[drow['Date']]=drow
        
                allStocksData[symbol]=d;
    
#    print "#INVE closing price#";
#    print allStocksData["INVE-B"]["2015-01-07"]["Closing price"];
#    print "###"
#    print "#INDU closing price#";
#    print allStocksData["INDU-C"]["2015-01-05"]["Bid"];
#    print "###"
    
    
    
    
    #Read the data and map it to ls_keys via dict() (i.e. Hash Table structure)
    ldf_data = c_dataobj.get_data(ldt_timestamps, ls_symbols, ls_keys);
    
    print ldf_data;
    
    d_data = dict(zip(ls_keys, ldf_data));
    

    return [d_data, allStocksData, dt_start, dt_end, dt_timeofday, ldt_timestamps];

    
    
'''
' Calculate Portfolio Statistics 
' @param na_normalized_price: NumPy Array for normalized prices (starts at 1)
' @param lf_allocations: allocation list
' @return list of statistics:
' (Volatility, Average Return, Sharpe, Cumulative Return)
'''
def calcStats(na_normalized_price, lf_allocations):
    #Calculate cumulative daily portfolio value
    #row-wise multiplication by weights
    na_weighted_price = na_normalized_price * lf_allocations;
    #row-wise sum
    na_portf_value = na_weighted_price.copy().sum(axis=1);

    #Calculate daily returns on portfolio
    # Calculate the daily returns of the prices. (Inplace calculation)
    # returnize0 works on ndarray and not dataframes.
    na_portf_rets = na_portf_value.copy()
    tsu.returnize0(na_portf_rets);

    #Calculate volatility (stdev) of daily returns of portfolio
   	# np.std(squareArray) returns the standard deviation of all the elements in the given array
    f_portf_volatility = np.std(na_portf_rets); 

    #Calculate average daily returns of portfolio
    f_portf_avgret = np.mean(na_portf_rets);

	# Sharpe ratio (Always assume you have 252 trading days in an year. And risk free rate = 0) of the total portfolio
    #	Calculate portfolio sharpe ratio (avg portfolio return / portfolio stdev) * sqrt(252)
    f_portf_sharpe = (f_portf_avgret / f_portf_volatility) * np.sqrt(252);

	# Cumulative return of the total portfolio
    #	Calculate cumulative daily return
    #	...using recursive function
    def cumret(t, lf_returns):
        #base-case
        if t==0:
            return (1 + lf_returns[0]);
        #continuation
        return (cumret(t-1, lf_returns) * (1 + lf_returns[t]));
    f_portf_cumrets = cumret(na_portf_rets.size - 1, na_portf_rets);

#   Another way of calculating total portfolio return
#    # Estimate portfolio returns
#	#   Multiply each column by the allocation to the corresponding equity
#	#   Sum each row for each day. That is your cumulative daily portfolio value
#    na_portfolio_rets = np.sum(na_rets * ls_allocation, axis=1)
#    na_port_total = np.cumprod(na_portfolio_rets + 1)
#    na_component_total = np.cumprod(na_rets + 1, axis=0)
   
    
    
    
    return [f_portf_volatility, f_portf_avgret, f_portf_sharpe, f_portf_cumrets, na_portf_value];

'''
' Simulate and assess performance of multi-stock portfolio
' @param li_startDate:	start date in list structure: [year,month,day] e.g. [2012,1,28]
' @param li_endDate:	end date in list structure: [year,month,day] e.g. [2012,12,31]
' @param ls_symbols:	list of symbols: e.g. ['GOOG','AAPL','GLD','XOM']
' @param lf_allocations:	list of allocations: e.g. [0.2,0.3,0.4,0.1]
'''
def analyze(li_startDate, li_endDate, ls_symbols, lf_allocations):

    #Check if ls_symbols and lf_allocations have same length
    if len(ls_symbols) != len(lf_allocations):
        print "ERROR: Make sure symbol and allocation lists have same number of elements.";
        return;
    #Check if lf_allocations adds up to 1
    sumAllocations = 0;
    for x in lf_allocations:
        sumAllocations += x;
    if sumAllocations != 1:
        print "ERROR: Make sure allocations add up to 1.";
        return;

    #Prepare data for statistics
    [d_data, allStocksData, dt_start, dt_end, dt_timeofday, ldt_timestamps] = readData(li_startDate, li_endDate, ls_symbols);

    # numpy ndarray of close prices
#    print d_data['close'];
    
    #for symbol in ls_symbols:
    #    array = {'date': np.array(allStocksData[symbol].keys()), 'values': np.array(allStocksData[symbol].values())}
    #    print array
        
    #Get numpy ndarray of close prices (numPy)
	#   Use adjusted close data. In QSTK, this is 'close'
    na_price = d_data['close'].values;
    
    
    sys.exit();
    

    #Normalize prices to start at 1 (if we do not do this, then portfolio value
    #must be calculated by weight*Budget/startPriceOfStock)
    #### Normalizing the prices to start at 1 and see relative returns ####
    #   Normalize the prices according to the first day The first row for each stock should have a value of 1.0 at this point
    na_normalized_price = na_price / na_price[0,:];
	
	#Assumption:
	#   Allocate some amount of value to each equity on the first day. You then "hold" those investments for the entire year.

    lf_Stats = calcStats(na_normalized_price, lf_allocations);

    #Print results
    print "Start Date: ", li_startDate;
    print "End Date: ", li_endDate;
    print "Symbols: ", ls_symbols;
    print "Volatility (stdev daily returns): " , lf_Stats[0];
    print "Average daily returns: " , lf_Stats[1];
    print "Sharpe ratio: " , lf_Stats[2];
    print "Cumulative daily return: " , lf_Stats[3];

    #Return list: [Volatility, Average Returns, Sharpe Ratio, Cumulative Return]
    return lf_Stats[0:3]; 



'''
Actual Implementation Starts:
'''
startDate = [2015,1,1];
endDate = [2016,5,13];
#analyze(startDate,endDate,['VIT_B', 'INDU-C', 'KLED', 'LUND-B', 'INVE-B'], [0.2, 0.2, 0.2, 0.2, 0.2]);
analyze(startDate,endDate,['INDU-C', 'INVE-B'], [0.5, 0.5]);



