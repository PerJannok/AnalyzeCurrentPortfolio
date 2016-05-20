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
import math
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
' Reads data from csv files extracted from NordicOMX
' @param ls_symbols:	    list of symbols: e.g. ['GOOG','AAPL','GLD','XOM']
' @returns d_data_csv:      dictionary structure of data mapped to keys e.g. 'open', 'close'
'''
def readNordicOMXCSVData(ls_symbols):
    csvFolderPath = "C:\\Users\\pjannok\\python_workspace\\AnalyzeCurrentPortfolio\\NASDAQOMX\\"
    
    ls_csv_keys = ['Bid', 'Trades', 'Closing price'];
    
    list_csv = [];
    
    for key in ls_csv_keys:

        df_combined = pd.DataFrame()
        for symbol in ls_symbols:
            for filename in os.listdir(csvFolderPath):
                pattern = symbol+"(.*).csv";
                if re.match(pattern, filename):
                
                    df_data = pd.read_csv(csvFolderPath+filename, delimiter=";", header=1, index_col=0, usecols=[0,1,2,3,4,5,6,7,8,9,10], dtype={'Closing price': np.float64, 'Bid': np.float64});
                    df_data.rename(columns={key:symbol}, inplace=True);
                    df_close = df_data[symbol];
                    df_combined=pd.concat([df_combined, df_close], axis=1);
                
        list_csv.append(df_combined);

    
    d_data_csv = dict(zip(ls_csv_keys, list_csv));

    return d_data_csv;

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

    
    #Read the data and map it to ls_keys via dict() (i.e. Hash Table structure)
    ldf_data = c_dataobj.get_data(ldt_timestamps, ls_symbols, ls_keys);
    
    d_data = dict(zip(ls_keys, ldf_data));
    
    return [d_data, dt_start, dt_end, dt_timeofday, ldt_timestamps];


def vol(returns):
    #Calculate volatility (stdev) of daily returns of portfolio
   	# np.std(squareArray) returns the standard deviation of all the elements in the given array
    # Return the standard deviation of returns
    return np.std(returns)

def lpm(returns, threshold, order):
    # This method returns a lower partial moment of the returns
    # Create an array he same length as returns containing the minimum return threshold
    threshold_array = np.empty(len(returns))
    threshold_array.fill(threshold)
    # Calculate the difference between the threshold and the returns
    diff = threshold_array - returns
    # Set the minimum of each to 0
    diff = diff.clip(min=0)
    # Return the sum of the different to the power of order
    return np.sum(diff ** order) / len(returns)    

def prices(returns, base):
    # Converts returns into prices
    s = [base]
    for i in range(len(returns)):
        s.append(base * (1 + returns[i]))
    return np.array(s)    
    
def dd(returns, tau):
    # Returns the draw-down given time period tau
    values = prices(returns, 100)
    pos = len(values) - 1
    pre = pos - tau
    drawdown = float('+inf')
    # Find the maximum drawdown given tau
    while pre >= 0:
        dd_i = (values[pos] / values[pre]) - 1
        if dd_i < drawdown:
            drawdown = dd_i
        pos, pre = pos - 1, pre - 1
    # Drawdown should be positive
    return abs(drawdown)


def max_dd(returns):
    # Returns the maximum draw-down for any tau in (0, T) where T is the length of the return series
    max_drawdown = float('-inf')
    for i in range(0, len(returns)):
        drawdown_i = dd(returns, i)
        if drawdown_i > max_drawdown:
            max_drawdown = drawdown_i
    # Max draw-down should be positive
    return abs(max_drawdown)

def sharpe_ratio(er, returns, rf):
    return (er - rf) / vol(returns)

def sortino_ratio(er, returns, rf, target=0):
    return (er - rf) / math.sqrt(lpm(returns, target, 2))

    
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
    na_portf_rets = na_portf_value.copy();
    tsu.returnize0(na_portf_rets);
    
    # Risk free rate (= 3 month STIBOR, https://www.avanza.se/index/om-indexet.html/171940/3-man-stibor)
    #risk_free_rate = -0.0047;
    risk_free_rate = 0;

    # ###   risk metrics    ###
    print
    print "###   risk metrics    ###";
    print "vol           = ", vol(na_portf_rets);
    print "Drawdown(5)   = ", dd(na_portf_rets, 5);
    print "Max Drawdown  = ", max_dd(na_portf_rets);
    
    
    #Calculate average daily returns of portfolio, ie. Expected return
    f_portf_avgret = np.mean(na_portf_rets);

    # ###   risk adjusted metrics   ###
    print
    print "###   risk adjusted metrics   ###";
    # Risk-adjusted return based on Volatility
    print "Sharpe Ratio              = ", sharpe_ratio(f_portf_avgret, na_portf_rets, risk_free_rate);
    print "Sharpe Ratio (annualized) = ", sharpe_ratio(f_portf_avgret, na_portf_rets, risk_free_rate) * np.sqrt(252);   # avg 252 business days in a year
    # Risk-adjusted return based on Lower Partial Moments
    print "Sortino Ratio             = ", sortino_ratio(f_portf_avgret, na_portf_rets, risk_free_rate);
    
    
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
   
    
    
    return [f_portf_avgret, f_portf_cumrets, na_portf_value];

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
    #[d_data, dt_start, dt_end, dt_timeofday, ldt_timestamps] = readData(li_startDate, li_endDate, ls_symbols);
    d_data_csv = readNordicOMXCSVData(ls_symbols);
    
    #tweak to backfill 'Closing price' for those stocks that does not have historical data for whole date range
    d_data_csv['Closing price'] = d_data_csv['Closing price'].fillna(method='bfill');
    d_data_csv['Closing price'] = d_data_csv['Closing price'].fillna(1.0);
    
    
    #Get numpy ndarray of close prices (numPy)
	#   Use adjusted close data. In QSTK, this is 'close'
    #na_price = d_data['close'].values;
    
    na_price_csv = d_data_csv['Closing price'].values;
    
    
    #Normalize prices to start at 1 (if we do not do this, then portfolio value
    #must be calculated by weight*Budget/startPriceOfStock)
    #### Normalizing the prices to start at 1 and see relative returns ####
    #   Normalize the prices according to the first day The first row for each stock should have a value of 1.0 at this point
    #na_normalized_price = na_price / na_price[0,:];
	
    na_normalized_price_csv = na_price_csv / na_price_csv[0,:];
    

    print "Start Date:              ", li_startDate;
    print "End Date:                ", li_endDate;
    print "Symbols:                 ", ls_symbols;

    
	#Assumption:
	#   Allocate some amount of value to each equity on the first day. You then "hold" those investments for the entire year.

    #lf_Stats_yahoo = calcStats(na_normalized_price, lf_allocations);
    
    lf_Stats_csv = calcStats(na_normalized_price_csv, lf_allocations);

    


'''
Actual Implementation Starts:
'''
startDate = [2015,1,1];
endDate = [2016,5,19];
analyze(startDate,endDate,['GRNG', 'RROS', 'AMAST-PREF', 'CTT', 'BINV', 'MCAP', 'CAST', 'HOFI', 'INDU-C', 'INVE-B', 'KLED', 'LATO-B', 'LUND-B', 'MSC', 'VIT-B', 'AVEG'], [0.045,0.04,0.12,0.11,0.05,0.07,0.04,0.05,0.06,0.08,0.04,0.04,0.065,0.04,0.13,0.02]);











