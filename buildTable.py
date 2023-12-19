import pandas as pd
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.uix.popup import Popup
from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.relativedelta import relativedelta
import yfinance as yf
import matplotlib.pyplot as plt
import os
import random
import numpy as np
import requests
from bs4 import BeautifulSoup
import logging
import math
from io import StringIO

def chartYieldCurve(year=2023,month=12,day=18):
    '''chart US treasury yield curve'''
    fig, ax = plt.subplots()
    plotRatetable=pd.read_csv('USrates_{YEAR}.csv'.format(YEAR=str(year)))
    plotRatetable['Date']=[datetime.strptime(i, "%m/%d/%Y") for i in df['Date']]
    plotRatetable=plotRatetable.sort_values('Date',ascending=True).reset_index()
    plotRatetable=plotRatetable.iloc[plotRatetable['Date'].searchsorted(datetime(year, month, day))]

    plotRatetable=plotRatetable[["1 Mo","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"]]
    masking=np.isfinite(plotRatetable.values.astype(float) )
    ax.plot(np.array([1/12,2/12,3/12,4/12,6/12,1,2,3,5,7,10,20,30])[masking],plotRatetable.values.astype(float)[masking],marker="o")
    ax.set_xlabel('Maturities')
    ax.set_ylabel('Yield in %')
    ax.set_title('US treasury yields - '+str(year)+'/'+str(month)+'/'+str(day))
    return plt.savefig(chartYield.png, transparent=True)
def refreshUStreasuryData():
    '''downloads US treasury data'''
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    cookies = {}
    headers = {}
    params = {}
    response=[]
    strReq="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{YEAR}/all?type=daily_treasury_yield_curve&field_tdr_date_value={YEAR}&page&_format=csv"
    for year in range(2017,2024):
        #for year in [2016]:
        if os.path.isfile('USrates_{YEAR}.csv'.format(YEAR=str(year))):
            logging.info(str(year)+' already queried.')
        else:
            logging.info('Querying '+str(year)+' [START] '+str(datetime.now(tzlocal())))
            response=requests.get(strReq.format(YEAR=str(year)), params=params, cookies=cookies, headers=headers)
            if response.status_code==200:
                with open('USrates_{YEAR}.csv'.format(YEAR=str(year)),'w') as f:
                    f.write(response.text)
                    #logging.info('Yields for {YEAR} saved to csv!'.format(YEAR=str(year)))
            else:
                logging.info('query of {YEAR} failed.'.format(YEAR=str(year)))



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

def bootstrapAndSim(datadf, nbRuns=1000):
    '''give 95pct CI and price path simulation'''
    logging.info('Running bootstrap and price sim...')
    array = np.random.randint(low=0, high=len(datadf), size=(nbRuns, len(datadf)))
    newArray=[datadf['ClosePctChg'].iloc[array[i]].values for i in range(nbRuns)]
    array=pd.DataFrame(newArray)
    average=array.apply(np.average, axis=1)
    #std=array.apply(np.std, axis=1)
    cumprod=array.apply(lambda x:100*np.cumprod(1+x/100), axis=1)
    lb=average.sort_values().to_list()[int(5*len(average)/100)]
    ub=average.sort_values().to_list()[int(95*len(average)/100)]
    return lb,ub, cumprod

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
    ax.set_xlabel('Close Perf (%)')
    ax.set_ylabel('Number of days in each bucket')
    ax.set_title('Empirical distribution')
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
    ax.set_ylabel('Stock price')
    ax.set_xlabel('Trading day')
    axbis.set_ylabel('Transact volume')
    ax.set_title('Stock price and volume')
    return plt.savefig(pngNameDOTpng, transparent=True)

def pricePlotSimulation(pricePaths,datadf, pngNameDOTpng):
    '''showing the possible price paths given the actual returns'''
    logging.info('Creating price sim plots...')
    fig, ax = plt.subplots()
    for i in pricePaths:
        ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(i) for i in np.concatenate([np.array(100),pricePaths.iloc[i].values],axis=None)], alpha=0.2, color='lightgrey')

    ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(50) for i in np.concatenate([np.array(100),pricePaths.iloc[0].values],axis=None)], color='orange',linestyle='--')
    ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(75) for i in np.concatenate([np.array(100),pricePaths.iloc[0].values],axis=None)], color='orange',linestyle='--')
    ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(100) for i in np.concatenate([np.array(100),pricePaths.iloc[0].values],axis=None)], color='black')
    ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(125) for i in np.concatenate([np.array(100),pricePaths.iloc[0].values],axis=None)], color='cyan',linestyle='--')
    ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(150) for i in np.concatenate([np.array(100),pricePaths.iloc[0].values],axis=None)], color='cyan',linestyle='--')

    ax.plot(np.concatenate([np.array([0]),1+pricePaths.iloc[i].index],axis=None),[math.log(i) for i in np.concatenate([np.array(100),100*datadf['Close']/datadf['Close'].iloc[0]],axis=None)], color='red',linestyle='-')

    ax.text(1,math.log(50), "50", color="orange", ha="left", va="top")
    ax.text(1,math.log(75), "75", color="orange", ha="left", va="top")
    ax.text(1,math.log(100), "100", color="black", ha="right", va="center")
    ax.text(1,math.log(125), "125", color="cyan", ha="left", va="bottom")
    ax.text(1,math.log(150), "150", color="cyan", ha="left", va="bottom")

    ax.set_ylabel('log scale, starting at log(100)')
    ax.set_xlabel('Number of trading days (red: actual path)')
    ax.set_title('Price path simulation ('+str(len(pricePaths))+')')

    plt.savefig(pngNameDOTpng, transparent=True)
    zoomRange=[math.log(i) for i in pricePaths[min(30,len(pricePaths.iloc[0])-1)].values]
    ax.set_ylim(min(zoomRange),max(zoomRange))
    ax.set_xlim(0,min(30,len(pricePaths.iloc[0])-1))
    plt.savefig('zoom_'+pngNameDOTpng, transparent=True)

    return 0