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


def updateMyPTFassets():
    upro=callYfinance('upro','2016-01-01','2030-12-31')
    tmf=callYfinance('tmf','2016-01-01','2030-12-31')
    upro['upro_closePctChg']=upro['ClosePctChg']
    tmf['tmf_closePctChg']=tmf['ClosePctChg']
    upro.to_csv('upro.csv')
    tmf.to_csv('tmf.csv')
def ptfAnalyse(start='2023-10-01',end='2023-11-03',
               rebalFreq=20,uproTargetRatio=0.5,rebalRatioTolerance=0.01,
               startingMoneys=200,useNewMoney=False,showOutput=True):
    pd.options.mode.chained_assignment = None
    pd.options.display.float_format = '{:,.1f}'.format
    pd.set_option('display.min_rows', 50)  # <-add this!
    pd.set_option('display.max_rows', 50)

    upro=pd.read_csv('upro.csv')
    tmf=pd.read_csv('tmf.csv')
    upro=upro.set_index('Date')
    tmf=tmf.set_index('Date')

    ptf=pd.merge(upro['upro_closePctChg'],tmf['tmf_closePctChg'],on='Date')
    ptf.loc[(ptf['upro_closePctChg']<=0)&(ptf['tmf_closePctChg']>=0),'Type']='upro<0, tmf>0'
    ptf.loc[(ptf['upro_closePctChg']>=0)&(ptf['tmf_closePctChg']>=0),'Type']='upro>0, tmf>0'
    ptf.loc[(ptf['upro_closePctChg']>=0)&(ptf['tmf_closePctChg']<=0),'Type']='upro>0, tmf<0'
    ptf.loc[(ptf['upro_closePctChg']<=0)&(ptf['tmf_closePctChg']<=0),'Type']='upro<0, tmf<0'
    ptf=ptf[start:end]

    #rebalFreq=10
    #uproTargetRatio=0.5
    #rebalRatioTolerance=0.01
    #startingMoneys=200
    #useNewMoney=False

    ptf_ratioUPRO_s=[]
    ptf_ratioTMF_s=[]
    ptf_valueUPRO_s=[]
    ptf_valueTMF_s=[]
    ptf_cfUPRO_s=[]
    ptf_cfTMF_s=[]
    ptf_ratioUPRO_e=[]
    ptf_ratioTMF_e=[]
    ptf_valueUPRO_e=[]
    ptf_valueTMF_e=[]
    ptf_cfUPRO_e=[]
    ptf_cfTMF_e=[]
    for i in range(len(ptf)):
        if i==0:
            ptf_valueUPRO_s.append(startingMoneys*uproTargetRatio)
            ptf_valueTMF_s.append(startingMoneys*(1-uproTargetRatio))
            ptf_cfUPRO_s.append(startingMoneys*uproTargetRatio)
            ptf_cfTMF_s.append(startingMoneys*(1-uproTargetRatio))
            ptf_ratioUPRO_s.append(ptf_valueUPRO_s[i]/(ptf_valueUPRO_s[i]+ptf_valueTMF_s[i]))
            ptf_ratioTMF_s.append(ptf_valueTMF_s[i]/(ptf_valueUPRO_s[i]+ptf_valueTMF_s[i]))


        else:
            if ((ptf_ratioUPRO_e[i-1]<=(uproTargetRatio-rebalRatioTolerance)) or \
                (ptf_ratioUPRO_e[i-1]>=(uproTargetRatio+rebalRatioTolerance))) and \
                    ptf.reset_index().index[i]%rebalFreq==0:

                if (useNewMoney=='True') or (useNewMoney=='true'):
                    shortfall=ptf_valueUPRO_e[i-1]-ptf_valueTMF_e[i-1]
                    if shortfall>0:
                        ptf_cfUPRO_s.append(0)
                        ptf_cfTMF_s.append(shortfall)
                        ptf_valueUPRO_s.append(ptf_valueUPRO_e[i-1])
                        ptf_valueTMF_s.append(ptf_valueTMF_e[i-1]+shortfall)
                    else:
                        ptf_cfUPRO_s.append(shortfall)
                        ptf_cfTMF_s.append(0)
                        ptf_valueUPRO_s.append(ptf_valueUPRO_e[i-1]+shortfall)
                        ptf_valueTMF_s.append(ptf_valueTMF_e[i-1])
                else:
                    if ptf_valueTMF_e[i-1]-ptf_valueUPRO_e[i-1]>0:
                        ptf_cfUPRO_s.append((ptf_valueTMF_e[i-1]-ptf_valueUPRO_e[i-1])/2)
                        ptf_cfTMF_s.append(-1*(ptf_valueTMF_e[i-1]-ptf_valueUPRO_e[i-1])/2)
                        ptf_valueUPRO_s.append(ptf_valueUPRO_e[i-1]+(ptf_valueTMF_e[i-1]-ptf_valueUPRO_e[i-1])/2)
                        ptf_valueTMF_s.append(ptf_valueTMF_e[i-1]-1*(ptf_valueTMF_e[i-1]-ptf_valueUPRO_e[i-1])/2)
                    if ptf_valueUPRO_e[i-1]-ptf_valueTMF_e[i-1]>0:
                        ptf_cfTMF_s.append((ptf_valueUPRO_e[i-1]-ptf_valueTMF_e[i-1])/2)
                        ptf_cfUPRO_s.append(-1*(ptf_valueUPRO_e[i-1]-ptf_valueTMF_e[i-1])/2)
                        ptf_valueUPRO_s.append(ptf_valueUPRO_e[i-1]-1*(ptf_valueUPRO_e[i-1]-ptf_valueTMF_e[i-1])/2)
                        ptf_valueTMF_s.append(ptf_valueTMF_e[i-1]+(ptf_valueUPRO_e[i-1]-ptf_valueTMF_e[i-1])/2)

                ptf_ratioUPRO_s.append(ptf_valueUPRO_s[i]/(ptf_valueUPRO_s[i]+ptf_valueTMF_s[i]))
                ptf_ratioTMF_s.append(ptf_valueTMF_s[i]/(ptf_valueUPRO_s[i]+ptf_valueTMF_s[i]))

            else:
                ptf_valueUPRO_s.append(ptf_valueUPRO_e[i-1])
                ptf_valueTMF_s.append(ptf_valueTMF_e[i-1])
                ptf_ratioUPRO_s.append(ptf_ratioUPRO_e[i-1])
                ptf_ratioTMF_s.append(ptf_ratioTMF_e[i-1])
                ptf_cfUPRO_s.append(0)
                ptf_cfTMF_s.append(0)

        ptf_valueUPRO_e.append(ptf_valueUPRO_s[i]*(1+ptf['upro_closePctChg'].iloc[i]/100))
        ptf_valueTMF_e.append(ptf_valueTMF_s[i]*(1+ptf['tmf_closePctChg'].iloc[i]/100))
        ptf_ratioUPRO_e.append(ptf_valueUPRO_e[i]/(ptf_valueUPRO_e[i]+ptf_valueTMF_e[i]))
        ptf_ratioTMF_e.append(ptf_valueTMF_e[i]/(ptf_valueUPRO_e[i]+ptf_valueTMF_e[i]))

    ##look at number of days ups and downs
    chronological=False
    ptf_incrDays=ptf.sort_values('Date',ascending=chronological)
    ptf_incrDays['cumTypeCount']=ptf_incrDays.groupby(['Type']).cumcount()+1
    ptf_incrDays=ptf_incrDays.reset_index().pivot(index='Date', columns='Type', values='cumTypeCount').sort_values('Date',ascending=chronological).ffill().fillna(0)
    ptf_incrDays['CountDay']=ptf_incrDays.reset_index().index+1
    for col in ['upro<0, tmf<0','upro>0, tmf>0','upro<0, tmf>0','upro>0, tmf<0']:
        if col not in ptf_incrDays.columns:
            ptf_incrDays[col]=0
    #show output if needed
    if showOutput:
        perf='{:,.2f}%'.format(100*(((ptf_valueUPRO_e[-1]+ptf_valueTMF_e[-1])/(np.array(ptf_cfUPRO_s)+np.array(ptf_cfTMF_s)).sum())-1))

        summaryText=''
        summaryText+='Performance of '+perf+' \n'
        summaryText+='PnL of '+format(int(ptf_valueUPRO_e[-1]+ptf_valueTMF_e[-1])-int(np.array(ptf_cfUPRO_s).sum()+np.array(ptf_cfTMF_s).sum()),',d') + ' HKD'+' \n'
        summaryText+='           '+' \n'
        #print('Influx of '+format(int((np.array(ptf_cfUPRO_s)[np.array(ptf_cfUPRO_s)>0].sum())+np.array(ptf_cfTMF_s)[np.array(ptf_cfTMF_s)>0].sum()),',d')+' HKD')
        #print('Breakdown: '+format(int(np.array(ptf_cfUPRO_s)[np.array(ptf_cfUPRO_s)>0].sum()),',d')+' HKD of UPRO, of which '+format(int(ptf_valueUPRO_s[0]),',d')+ ' HKD was initial seed.')
        #print('           '+format(int(np.array(ptf_cfTMF_s)[np.array(ptf_cfTMF_s)>0].sum()),',d')+' HKD of TMF, of which '+format(int(ptf_valueTMF_s[0]),',d')+ ' HKD was initial seed.')
        #print('           ')
        summaryText+='Last valuation at '+format(int(ptf_valueUPRO_e[-1]+ptf_valueTMF_e[-1]),',d')+ ' HKD'+' \n'
        summaryText+='Breakdown: '+format(int(ptf_valueUPRO_e[-1]),',d')+' HKD of UPRO'+' \n'
        summaryText+='                      '+format(int(ptf_valueTMF_e[-1]),',d')+' HKD of TMF'+' \n'
        summaryText+='           '+' \n'
        summaryText+='Influx of '+format(int(np.array(ptf_cfUPRO_s).sum()+np.array(ptf_cfTMF_s).sum()),',d')+' HKD'+' \n'
        summaryText+='Breakdown: '+format(int(np.array(ptf_cfUPRO_s).sum()),',d')+' HKD of UPRO, of which '+format(int(ptf_valueUPRO_s[0]),',d')+ ' HKD was initial seed.'+' \n'
        summaryText+='                     '+format(int(np.array(ptf_cfTMF_s).sum()),',d')+' HKD of TMF, of which '+format(int(ptf_valueTMF_s[0]),',d')+ ' HKD was initial seed.'+' \n'
        summaryText+='            '+' \n'

        fig, (ax, ax1, ax2) = plt.subplots(nrows=3, sharex=True,figsize=(8, 8),constrained_layout = True)

        ax.plot(ptf.index,np.array(ptf_valueUPRO_e)+np.array(ptf_valueTMF_e),label='ptf ending value')


        ax1.plot(ptf_incrDays.index,np.array(ptf_incrDays['upro<0, tmf<0'].values),label='upro<0, tmf<0', color='blue')
        ax1.plot(ptf_incrDays.index,np.array(ptf_incrDays['upro>0, tmf>0'].values),label='upro>0, tmf>0',color='red')
        ax1.plot(ptf_incrDays.index,np.array(ptf_incrDays['upro<0, tmf>0'].values),label='upro<0, tmf>0',color='orange')
        ax1.plot(ptf_incrDays.index,np.array(ptf_incrDays['upro>0, tmf<0'].values),label='upro>0, tmf<0',color='green')

        ax2.bar(ptf_incrDays.index,np.array(ptf_incrDays['upro<0, tmf<0'].values/ptf_incrDays['CountDay'].values),label='upro<0, tmf<0',color='blue')
        ax2.bar(ptf_incrDays.index,np.array(ptf_incrDays['upro>0, tmf>0'].values/ptf_incrDays['CountDay'].values),bottom=np.array(ptf_incrDays['upro<0, tmf<0'].values/ptf_incrDays['CountDay'].values),label='upro>0, tmf>0',color='red')
        ax2.bar(ptf_incrDays.index,np.array(ptf_incrDays['upro<0, tmf>0'].values/ptf_incrDays['CountDay'].values),bottom=np.array(ptf_incrDays['upro<0, tmf<0'].values/ptf_incrDays['CountDay'].values)+np.array(ptf_incrDays['upro>0, tmf>0'].values/ptf_incrDays['CountDay'].values),label='upro<0, tmf>0',color='orange')
        ax2.bar(ptf_incrDays.index,np.array(ptf_incrDays['upro>0, tmf<0'].values/ptf_incrDays['CountDay'].values),bottom=np.array(ptf_incrDays['upro<0, tmf<0'].values/ptf_incrDays['CountDay'].values)+np.array(ptf_incrDays['upro>0, tmf>0'].values/ptf_incrDays['CountDay'].values)+np.array(ptf_incrDays['upro<0, tmf>0'].values/ptf_incrDays['CountDay'].values),label='upro>0, tmf<0',color='green')

        for label in ax2.get_xticklabels():
            label.set_rotation(90)
        for axis in [ax, ax1, ax2]:
            axis.minorticks_on()
            axis.xaxis.set_tick_params(which='minor', bottom=True)
            axis.xaxis.grid(True, which='minor')
            axis.yaxis.grid(True, which='major')
        plt.legend(bbox_to_anchor=(0.5, -0.5))
        plt.savefig("myPTF.png", transparent=True)
    return summaryText, pd.merge(ptf_incrDays, pd.DataFrame({'Date':ptf.index, 'ptf_value':np.array(ptf_valueUPRO_e)+np.array(ptf_valueTMF_e),'upro_value':np.array(ptf_valueUPRO_e),'tmf_value':np.array(ptf_valueTMF_e)}).set_index('Date'),on='Date')
def chartYieldCurve(year=2023,month=12,day=18):
    '''chart US treasury yield curve'''

    dictDuration={'1 Mo':1/12, '2 Mo':1/6, '3 Mo':1/4,'4 Mo':1/3, '6 Mo':1/2, '1 Yr':1, '2 Yr':2, '3 Yr':3, '5 Yr':5,
                  '7 Yr':7, '10 Yr':10, '20 Yr':20, '30 Yr':30}
    fig, ax = plt.subplots()
    plotRatetable=pd.read_csv('USrates_{YEAR}.csv'.format(YEAR=str(year)))
    plotRatetable['Date']=[datetime.strptime(i, "%m/%d/%Y") for i in plotRatetable['Date']]
    plotRatetable=plotRatetable.sort_values('Date',ascending=True).reset_index()
    plotRatetable=plotRatetable.iloc[plotRatetable['Date'].searchsorted(datetime(year, month, day))]
    col2plot=np.array(plotRatetable.index)[[i[0].isnumeric() for i in plotRatetable.index]]
    x4cols=[dictDuration[i] for i in col2plot]
    plotRatetable=plotRatetable[col2plot]
    masking=np.isfinite(plotRatetable.values.astype(float) )
    ax.plot(np.array(x4cols)[masking],plotRatetable.values.astype(float)[masking],marker="o")
    ax.set_xlabel('Maturities')
    ax.set_ylabel('Yield in %')
    ax.set_title('US treasury yields - '+str(year)+'/'+str(month)+'/'+str(day))
    ax.set_ylim(0,8)
    for i, j in zip(np.array(x4cols)[masking],plotRatetable.values.astype(float)[masking]):
        ax.text(i,j, str(j), ha='center', va='bottom')
    return plt.savefig("chartYield.png", transparent=True)
def refreshUStreasuryData(year,month,day):
    '''downloads US treasury data'''
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    cookies = {}
    headers = {}
    params = {}
    response=[]
    strReq="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{YEAR}/all?type=daily_treasury_yield_curve&field_tdr_date_value={YEAR}&page&_format=csv"

    query=True
    if os.path.isfile('USrates_{YEAR}.csv'.format(YEAR=str(year))):
        if datetime.today().year<int(year):
            logging.info(str(year)+' already queried.')
            query=False
        else:
            checkPD=pd.read_csv('USrates_{YEAR}.csv'.format(YEAR=str(year)))
            if datetime(year, month, day)<= datetime.strptime(max(checkPD['Date']),'%m/%d/%Y'):
                query=False

    if query:
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