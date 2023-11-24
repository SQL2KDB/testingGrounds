import pandas as pd
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.uix.popup import Popup
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import matplotlib.pyplot as plt
import os
import random
import numpy as np
import requests
from bs4 import BeautifulSoup
import logging

def getInstrumentName(tickerSearch):
    '''scrape yahoo finance website to get actual name of instrument'''
    logging.info('Webscraping basic stock info...')
    cookies = {}
    headers = {}
    params = {'p': tickerSearch,'.tsrc': 'fin-srch'}
    try:
        response = requests.get('https://finance.yahoo.com/quote/'+tickerSearch, params=params, cookies=cookies, headers=headers)
        if response.status_code==200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.title.text.split(') ')[0]+')'
        else:
            return tickerSearch
    except:
        return tickerSearch

def maxDrawDown(datadf):
    '''compute drawdown and create message'''
    logging.info('Computing max drawdow during period...')
    datadf['Date_copy']=datadf.index
    datadf=datadf.assign(indexNb=list(range(len(datadf))))
    datadf=datadf.set_index('indexNb')
    timelinePerfs=datadf.apply(lambda x:x['Close']-datadf['Close'],axis=1)
    cleanTimeLinePerfs=timelinePerfs.apply(lambda x:x.name>x.index,axis=0)
    worstDrop=np.nanmax(timelinePerfs[cleanTimeLinePerfs].apply(lambda x:np.nanmax(x),axis=1))
    pairsWorstDrop=[(x, timelinePerfs.columns[y]) for x, y in zip(*np.where(timelinePerfs.values == worstDrop))]
    worstDropCoor=[]
    for i in pairsWorstDrop:
        if i[1]>i[0]:
            worstDropCoor.append(i)
    datadf=datadf.assign(Date=datadf['Date_copy'])
    datadf=datadf.set_index('Date')
    msg=["{:.1f}%".format(100*(datadf['Close'][worstDropCoor[0][1]]/datadf['Close'][worstDropCoor[0][0]]-1))]
    for i in worstDropCoor[0]:
        msg.append(datadf.iloc[[i]].index.strftime('%Y-%m-%d')[0]+' @'+"{:.2f}".format(datadf['Close'][i]))
    return msg

def bestWinningStreak(datadf):
    '''compute best winning streak and create message'''
    logging.info('Computing best winning streak...')
    datadf['Date_copy']=datadf.index
    datadf=datadf.assign(indexNb=list(range(len(datadf))))
    datadf=datadf.set_index('indexNb')
    timelinePerfs=datadf.apply(lambda x:x['Close']-datadf['Close'],axis=1)
    cleanTimeLinePerfs=timelinePerfs.apply(lambda x:x.name>x.index,axis=0)
    bestWin=np.nanmin(timelinePerfs[cleanTimeLinePerfs].apply(lambda x:np.nanmin(x),axis=1))
    pairsBestUp=[(x, timelinePerfs.columns[y]) for x, y in zip(*np.where(timelinePerfs.values == bestWin))]
    bestUpCoor=[]
    for i in pairsBestUp:
        if i[1]>i[0]:
            bestUpCoor.append(i)
    datadf=datadf.assign(Date=datadf['Date_copy'])
    datadf=datadf.set_index('Date')
    msg=["{:.1f}%".format(100*(datadf['Close'][bestUpCoor[0][1]]/datadf['Close'][bestUpCoor[0][0]]-1))]
    for i in bestUpCoor[0]:
        msg.append(datadf.iloc[[i]].index.strftime('%Y-%m-%d')[0]+' @'+"{:.2f}".format(datadf['Close'][i]))
    return msg
def CIbounds(setLowerBound_dec,array,nbRuns=10000,operatorType='average'):
    '''compute a bootstrapped CI of a list'''
    bootstrapped_list=[]
    logging.info('Running bootstrap to get CI...')
    if operatorType=='average':
        for i in range(nbRuns):
            bootstrapped_list.append(np.average(random.choices(array, k=len(array))))
    if operatorType=='median':
        for i in range(nbRuns):
            bootstrapped_list.append(np.median(random.choices(array, k=len(array))))
    bootstrapped_list.sort()
    lb=bootstrapped_list[int(setLowerBound_dec*len(bootstrapped_list))]
    ub=bootstrapped_list[1+int((1-setLowerBound_dec)*len(bootstrapped_list))]
    return lb,ub
def simulateTimeSeries(array,nbSims=10000):
    '''simulate perf paths given distribution'''
    logging.info('Simulating price paths...')
    endingPrices=[]
    for i in range(nbSims):
        perf_path=random.choices(array, k=len(array))
        startPrice=100
        for j in perf_path:
            startPrice*=(1+j/100)
        endingPrices.append(startPrice)
    endingPrices.sort()
    return endingPrices
def dfToScreen(data):
    '''flexible table builder'''
    header_layout = MDBoxLayout(orientation='horizontal', size_hint=(1,None),height='20dp')
    header_layout.add_widget(MDLabel(text='Date'))
    header_layout.add_widget(MDLabel(text='Close',halign='center'))
    header_layout.add_widget(MDLabel(text='PctChange(%)',halign='right'))

    rowList = []
    for index, row in data.iterrows():
        row_index=str(index).split(' ')[0]
        row_Close="{:.4f}".format(row['Close'])
        row_ClosePctChg="{:.2f}".format(row['ClosePctChg'])
        row_layout = MDBoxLayout(orientation='horizontal')

        date_label = MDLabel(size_hint_y= None,height='15dp', text=row_index)
        close_label = MDLabel(size_hint_y= None,height='15dp', text=row_Close,halign='center')

        if row['ClosePctChg']<0:
            perfColor=(1, 0, 0, 1)
        else:
            perfColor=(0, 0.5, 0, 1)
        closePctChg_label = MDLabel(size_hint_y= None, height='15dp', text=row_ClosePctChg,halign='right',theme_text_color='Custom', text_color=perfColor,bold=False)

        row_layout.add_widget(date_label)
        row_layout.add_widget(close_label)
        row_layout.add_widget(closePctChg_label)

        rowList.append(row_layout)

    return header_layout, rowList


def callYfinance(ric_input, start_date, end_date):
    '''abstract the call to yfinance. Compute pct close including for first date on the table'''
    start_date_query=(datetime.strptime(start_date, "%Y-%m-%d") + relativedelta(days = -30)).strftime('%Y-%m-%d')
    # Make a call to yfinance to fetch UPRO data
    logging.info('Getting historical prices...')
    data = yf.download(ric_input, start=start_date_query, end=end_date)
    if len(data)>0:
        data['ClosePctChg']=100*data['Close'].pct_change()
        data=data[start_date:end_date]
        return data
    else:
        return pd.DataFrame()

def createBarChart(datadf,pngNameDOTpng):
    '''create a chart with the yfinance data on close pct moves'''
    logging.info('Creating bar charts...')
    if os.path.isfile(pngNameDOTpng):
        os.remove(pngNameDOTpng)
        print('removed previous png')
    fig, ax = plt.subplots()
    ax.hist(datadf['ClosePctChg'], bins=30)
    #plt.plot()
    return plt.savefig(pngNameDOTpng, transparent=True)

def createPricePlot(datadf,pngNameDOTpng):
    '''create a chart with the yfinance data on close pct moves'''
    logging.info('Creating price plots...')
    if os.path.isfile(pngNameDOTpng):
        os.remove(pngNameDOTpng)
        print('removed previous png')
    fig, ax = plt.subplots()
    ax.plot(datadf.index,datadf['Close'])
    axbis = ax.twinx()
    axbis.bar(datadf.index,datadf['Volume'], color='grey', alpha=0.5)
    #plt.plot()
    return plt.savefig(pngNameDOTpng, transparent=True)