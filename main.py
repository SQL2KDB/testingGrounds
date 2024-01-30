from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivymd.uix.button import MDRectangleFlatButton
from buildTable import dfToScreen, callYfinance, createBarChart, createPricePlot, pricePlotSimulation, maxDrawDown, bestWinningStreak,getInstrumentName, bootstrapAndSim, refreshUStreasuryData, chartYieldCurve,updateMyPTFassets,ptfAnalyse, prodDateString
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivmob_mod import KivMob, TestIds
import os
import logging
from kivy.clock import Clock
from functools import partial
import concurrent.futures
import numpy as np

class MyLabelHandler(logging.Handler):

    def __init__(self, label, level=logging.NOTSET):
        super(MyLabelHandler, self).__init__(level=level)
        self.label = label
    def emit(self, record):
        "using the Clock module for thread safety with kivy's main loop"
        def f(dt=None):
            self.label.text = '[i]' + self.format(record) + '[/i] \n' #"use += to append..."
        Clock.schedule_once(f)

class MainApp(MDApp):
    def buttonFetchScreen(self,screen_to_fetch):
        self.root.ids.rootScreenManager.current = screen_to_fetch
        self.root.ids.nav_drawer.set_state("close")
        return print('Fetched screen '+screen_to_fetch)
    def buttonDelScreen(self,widgetId, widget_to_remove,screen_to_remove,screen_to_remove_more):
        self.root.ids.contentNavigationDrawer.remove_widget(widget_to_remove)
        self.root.ids.rootScreenManager.remove_widget(screen_to_remove)
        self.root.ids.rootScreenManager.remove_widget(screen_to_remove_more)
        self.screenList.remove(widgetId)
        self.screenListMore.remove(widgetId+'_more')
        del self.varNameDict[widgetId]
        del self.varNameMoreDict[widgetId+'_more']
        os.remove('dailyPerfBar_'+widgetId+'.png')
        os.remove('pricePlot_'+widgetId+'.png')
        if len(self.screenList)>0:
            self.root.ids.prevFetched_msg.text='Previously fetched queries:'
        else:
            self.root.ids.prevFetched_msg.text=''
        return print('Removed screen')

    def getMoreAnalysis(self):
        '''screen placeholder for further analysis'''
        if len(self.screenList)>0 and (("myPTFscreen" not in self.root.ids.rootScreenManager.current) and ("USyieldsScreen" not in self.root.ids.rootScreenManager.current)):
            if "_more" in self.root.ids.rootScreenManager.current:
                self.root.ids.rootScreenManager.transition = SlideTransition(direction='right')
                self.varNameDict[self.root.ids.rootScreenManager.current.replace("_more","")].manager.current = self.root.ids.rootScreenManager.current.replace("_more","")
            else:
                self.root.ids.rootScreenManager.transition = SlideTransition(direction='left')
                self.varNameMoreDict[self.root.ids.rootScreenManager.current+'_more'].manager.current = self.root.ids.rootScreenManager.current+'_more'
        else:
            self.root.ids.nav_drawer.set_state("open")

    def seeMyPTF(self):
        if "myPTFscreen" in self.screenList:
            if ("myPTFscreen_res" in self.screenList) and self.varNameDict[self.root.ids.rootScreenManager.current].manager.current=="myPTFscreen":
                self.root.ids.rootScreenManager.transition = SlideTransition(direction='left')
                self.varNameDict["myPTFscreen_res"].manager.current="myPTFscreen_res"
            elif ("myPTFscreen_res" in self.screenList) and self.varNameDict[self.root.ids.rootScreenManager.current].manager.current=="myPTFscreen_res":
                self.root.ids.rootScreenManager.transition = SlideTransition(direction='right')
                self.varNameDict["myPTFscreen"].manager.current="myPTFscreen"
            elif ("myPTFscreen_res" in self.screenList):
                self.varNameDict["myPTFscreen"].manager.current="myPTFscreen"
            #US_treasuries_screen = self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen
            #US_treasuries_screen.clear_widgets()
        else:
            self.root.ids.rootScreenManager.transition = SlideTransition(direction='left')
            self.screenList.append("myPTFscreen")
            self.varNameDict["myPTFscreen"]=Builder.load_file('myPTF.kv')
            self.varNameDict["myPTFscreen"].name = "myPTFscreen"
            self.root.ids.rootScreenManager.add_widget(self.varNameDict["myPTFscreen"])

            self.screenList.append("myPTFscreen_res")
            self.varNameDict["myPTFscreen_res"]=Builder.load_file('myPTF_res.kv')
            self.varNameDict["myPTFscreen_res"].name = "myPTFscreen_res"
            self.root.ids.rootScreenManager.add_widget(self.varNameDict["myPTFscreen_res"])
        #US_treasuries_screen = self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen
            self.varNameDict["myPTFscreen"].manager.current="myPTFscreen"
            myPTF_container_1 = self.varNameDict["myPTFscreen_res"].ids.myPTF_screen_1
            myPTF_container_1.add_widget(MDLabel(text='No results to show yet. Do a query by clicking on the wallet icon.'))
    def reUpdatePTFassets(self):
        updateMyPTFassets()
        self.varNameDict["myPTFscreen"].ids.updatePTFlog.text = 'Updated.'
        self.cleanLogs()
    def refreshPTF(self):
        myPTF_container_1 = self.varNameDict["myPTFscreen_res"].ids.myPTF_screen_1
        myPTF_container_2 = self.varNameDict["myPTFscreen_res"].ids.myPTF_screen_2

        #myPTFsummary = self.varNameDict["myPTFscreen"].ids.myPTFsummary
        self.varNameDict["myPTFscreen"].ids.updatePTFlog.text = ''
        myPTF_container_1.clear_widgets()
        myPTF_container_2.clear_widgets()
        startYear = self.varNameDict["myPTFscreen"].ids.startYear.text
        startMonth = self.varNameDict["myPTFscreen"].ids.startMonth.text
        startDay = self.varNameDict["myPTFscreen"].ids.startDay.text
        endYear = self.varNameDict["myPTFscreen"].ids.endYear.text
        endMonth = self.varNameDict["myPTFscreen"].ids.endMonth.text
        endDay = self.varNameDict["myPTFscreen"].ids.endDay.text

        rebalFreq = self.varNameDict["myPTFscreen"].ids.rebalFreq.text
        uproTargetRatio = self.varNameDict["myPTFscreen"].ids.uproTargetRatio.text
        rebalRatioTolerance = self.varNameDict["myPTFscreen"].ids.rebalRatioTolerance.text
        startingMoneys = self.varNameDict["myPTFscreen"].ids.startingMoneys.text
        useNewMoney = self.varNameDict["myPTFscreen"].ids.useNewMoney.text

        #try:
        if os.path.isfile('upro.csv') and os.path.isfile('tmf.csv'):
            pass
        else:
            updateMyPTFassets()
        res1,res2=ptfAnalyse(start=startYear+'-'+startMonth+'-'+startDay,end=endYear+'-'+endMonth+'-'+endDay,
                             rebalFreq=int(rebalFreq), uproTargetRatio=float(uproTargetRatio)/100, rebalRatioTolerance=float(rebalRatioTolerance)/100,
                             startingMoneys=int(startingMoneys), useNewMoney=useNewMoney)
        myPTF_container_1.add_widget(MDLabel(text=res1))
        myPTF_container_2.add_widget(Image(source="myPTF.png", nocache=True,fit_mode='fill'))
        self.varNameDict["myPTFscreen_res"].manager.current="myPTFscreen_res"
        #except:
            #myPTF_container.add_widget(MDLabel(text='Error. Check date or connectivity.'))
        self.cleanLogs()

    def seeUStreasuryYields(self):
        self.root.ids.rootScreenManager.transition = SlideTransition(direction='right')
        if "USyieldsScreen" in self.screenList:
            pass
            #US_treasuries_screen = self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen
            #US_treasuries_screen.clear_widgets()
        else:
            self.screenList.append("USyieldsScreen")
            self.varNameDict["USyieldsScreen"]=Builder.load_file('UStreasuries.kv')
            self.varNameDict["USyieldsScreen"].name = "USyieldsScreen"
            self.root.ids.rootScreenManager.add_widget(self.varNameDict["USyieldsScreen"])
        #US_treasuries_screen = self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen
        self.varNameDict["USyieldsScreen"].manager.current="USyieldsScreen"

    def clearChartsUStreasuryCurves(self):
        treasury_container = self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen
        treasury_container.clear_widgets()
    def refreshUStreasuryCurve(self):
        treasury_container = self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen
        #treasury_container.clear_widgets()
        treasYear = self.varNameDict["USyieldsScreen"].ids.treasYear.text
        treasMonth = self.varNameDict["USyieldsScreen"].ids.treasMonth.text
        treasDate = self.varNameDict["USyieldsScreen"].ids.treasDate.text
        refreshUStreasuryData(int(treasYear),int(treasMonth),int(treasDate))
        try:
            for i in range(len(self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen.children)):
                if isinstance(self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen.children[i],MDLabel):
                    if self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen.children[i].id=='fillerBlock':
                        treasury_container.remove_widget(self.varNameDict["USyieldsScreen"].ids.US_treasuries_screen.children[i])
        except:
            pass
        try:
            chartYieldCurve(int(treasYear),int(treasMonth),int(treasDate))
            treasury_container.add_widget(Image(source='chartYield.png', nocache=True,fit_mode='contain'))
            treasury_container.add_widget(MDLabel(text='',id='fillerBlock'))
        except:
            treasury_container.add_widget(MDLabel(text='Error. Check date or connectivity.'))
        self.cleanLogs()

    def checkStatus(self,fetchVarName,stage):
        t1Done=False
        t2Done=False
        while not (t1Done and t2Done):
            if self.t1.done():
                t1Done=True
                msg1='thread 1 idle. \n'
            else:
                msg1='thread 1 running. \n'
            if self.t2.done():
                t2Done=True
                msg2='thread 2 idle. \n'
            else:
                msg2='thread 2 running. \n'
            self.logger0.info(stage+'\n'+msg1+msg2)
        return fetchVarName

    def buildRes(self,t1res,t2res,fetchVarName):
        datadf=self.datadf
        instrNameScrape=self.instrNameScrape
        self.pool.shutdown()
        #self.logger0 = logging.getLogger()
        self.logger0.info('Query result returned.')
        fetchStart=fetchVarName.split('_')[1]
        fetchEnd=fetchVarName.split('_')[2]

        #preparing the main screen
        self.screenList.append(fetchVarName)
        self.varNameDict[fetchVarName]=Builder.load_file('pageTemplate.kv')
        self.varNameDict[fetchVarName].name = fetchVarName
        self.root.ids.rootScreenManager.add_widget(self.varNameDict[fetchVarName])

        self.screenListMore.append(fetchVarName+'_more')
        self.varNameMoreDict[fetchVarName+'_more']=Builder.load_file('pageMoreTemplate.kv')
        self.varNameMoreDict[fetchVarName+'_more'].name = fetchVarName+'_more'
        self.root.ids.rootScreenManager.add_widget(self.varNameMoreDict[fetchVarName+'_more'])

        self.logger0.info('Building screen...')
        summary_container = self.varNameDict[fetchVarName].ids.summary_container
        chart_container = self.varNameDict[fetchVarName].ids.chart_container
        table_header = self.varNameDict[fetchVarName].ids.table_header
        table_container = self.varNameDict[fetchVarName].ids.table_container

        chart_container.clear_widgets()
        table_header.clear_widgets()
        table_container.clear_widgets()
        summary_container.clear_widgets()
        createBarChart(datadf,'dailyPerfBar_'+fetchVarName.upper()+'.png')
        createPricePlot(datadf,'pricePlot_'+fetchVarName.upper()+'.png')


        #start of page summary
        summary_container.add_widget(MDLabel(markup=True, text='',size_hint_y=None, height='5dp'))
        summary_container.add_widget(MDLabel(markup=True, text='[b]'+instrNameScrape+'[/b]',size_hint_y=None, height='15dp'))
        summary_container.add_widget(MDLabel(markup=True, text='   (queried from '+fetchStart+' to '+fetchEnd+')',size_hint_y=None, height='15dp'))
        summary_container.add_widget(MDLabel(markup=True, text='Daily performance stats:',size_hint_y=None, height='15dp'))

        #daily perf CI
        d=[datadf['ClosePctChg'].mean(),t1res[0],t1res[1]]
        dn=[]
        for di in [d[0],d[1],d[2]]:
            if di <0:
                dn.append("[color=FF0000]"+"{:.2f}%".format(di)+"[/color]")
            else:
                dn.append("[color=008000]"+"{:.2f}%".format(di)+"[/color]")
        dLabel=MDLabel(markup=True, text="   Mean at 95% CI: ("+dn[1]+";[b]"+dn[0]+"[/b];"+dn[2]+")",theme_text_color='Custom',size_hint_y=None, height='15dp')
        summary_container.add_widget(dLabel)
        dLabel=MDLabel(markup=True, text="   Sample Std Dev: {:.2f}%".format(datadf['ClosePctChg'].std()),theme_text_color='Custom',size_hint_y=None, height='15dp')
        summary_container.add_widget(dLabel)

        #Path simulation
        simPerfs=t1res[2][len(datadf)-1].sort_values()
        simPerfs=np.array(simPerfs)
        below100=int(100*len(simPerfs[simPerfs<100])/len(simPerfs))
        below75=int(100*len(simPerfs[simPerfs<75])/len(simPerfs))
        below50=int(100*len(simPerfs[simPerfs<50])/len(simPerfs))
        dLabel=MDLabel(markup=True, text="Path simulations:",theme_text_color='Custom',size_hint_y=None, height='15dp')
        summary_container.add_widget(dLabel)
        dLabel=MDLabel(markup=True, text="   [i][b]"+str(below100)+"%[/b] of paths go below 100% of initial value.[/i]",theme_text_color='Custom',size_hint_y=None, height='15dp')
        summary_container.add_widget(dLabel)
        dLabel=MDLabel(markup=True, text="   [i][b]"+str(below75)+"%[/b] of paths go below 75% of initial value.[/i]",theme_text_color='Custom',size_hint_y=None, height='15dp')
        summary_container.add_widget(dLabel)
        dLabel=MDLabel(markup=True, text="   [i][b]"+str(below50)+"%[/b] of paths go below 50% of initial value.[/i]",theme_text_color='Custom',size_hint_y=None, height='15dp')
        summary_container.add_widget(dLabel)

        mdd=maxDrawDown(datadf)
        summary_container.add_widget(MDLabel(markup=True, text='Max drawdown during period: [color=FF0000]'+mdd[0]+'[/color]',size_hint_y=None, height='15dp'))
        summary_container.add_widget(MDLabel(markup=True, text='   [i]'+mdd[1]+'[/i]',size_hint_y=None, height='15dp'))
        summary_container.add_widget(MDLabel(markup=True, text='   [i]'+mdd[2]+'[/i]',size_hint_y=None, height='15dp'))

        bws=bestWinningStreak(datadf)
        summary_container.add_widget(MDLabel(markup=True, text='Best winning streak: [color=008000]'+bws[0]+'[/color]',size_hint_y=None, height='15dp'))
        summary_container.add_widget(MDLabel(markup=True, text='   [i]'+bws[1]+'[/i]',size_hint_y=None, height='15dp'))
        summary_container.add_widget(MDLabel(markup=True, text='   [i]'+bws[2]+'[/i]',size_hint_y=None, height='15dp'))

        pricePlotSimulation(t1res[2],datadf, 'priceSim_'+fetchVarName+'.png')

        #add charts in the middle of the page
        chart_container.add_widget(Image(source='dailyPerfBar_'+fetchVarName.upper()+'.png', fit_mode='fill', nocache=True))
        chart_container.add_widget(Image(source='pricePlot_'+fetchVarName.upper()+'.png', fit_mode='fill', nocache=True))
        chart_container.add_widget(Image(source='priceSim_'+fetchVarName.upper()+'.png', fit_mode='fill', nocache=True))
        chart_container.add_widget(Image(source='zoom_priceSim_'+fetchVarName.upper()+'.png', fit_mode='fill', nocache=True))

        #add recap table at the end of the page
        tbh,rowlist = dfToScreen(datadf)
        table_header.add_widget(tbh)
        for rl in rowlist:
            table_container.add_widget(rl)

        #TODO
        #summary_container.add_widget(MDLabel(markup=True, text='P/E:',size_hint_y=None, height='15dp'))

        #create a history of queries for quick retrieval
        thisQueryLine=MDBoxLayout(orientation="horizontal",id=fetchVarName+'_navline',spacing=5)
        self.root.ids.contentNavigationDrawer.add_widget(thisQueryLine)
        thisQueryLine.add_widget(MDRectangleFlatButton(padding=5, text=fetchVarName, id=fetchVarName+'_button', on_release = lambda a:self.buttonFetchScreen(fetchVarName)))
        thisQueryLine.add_widget(MDRectangleFlatButton(padding=5, text='Del', id=fetchVarName+'_delbutton',theme_text_color='Custom',text_color="red",line_color="red", on_release = lambda a:self.buttonDelScreen(fetchVarName,thisQueryLine,self.varNameDict[fetchVarName],self.varNameMoreDict[fetchVarName+'_more'])))

        #prepare the 'more' screen
        self.varNameMoreDict[fetchVarName+'_more'].ids.more_text_id.text=fetchVarName + " -- placeholder for extra stuff."

        #prepare final view
        self.varNameDict[fetchVarName].manager.current = fetchVarName
        self.root.ids.nav_drawer.set_state("close")

        self.cleanThreads()


        if len(self.screenList)>0:
            self.root.ids.prevFetched_msg.text='Previously fetched queries:'
        else:
            self.root.ids.prevFetched_msg.text=''

    def cleanThreads(self):
        self.logger0.info('Cleaning up any previous worker threads...')
        try:
            self.pool.shutdown()
            self.logger0.info('  ')
        except:
            self.logger0.info('Worker threads failed to shutdown (!)')

    def checkQueryIsGoodToGo(self,t1res,t2res,fetchVarName):
        if (len(t1res)>0):
            self.runPaths(t1res,t2res,fetchVarName)
        else:
            popup=Popup(title='Error',
                        content=MDLabel(text='Data query failed.\n Check validity of RIC, start and end dates, and whether your internet connection is on.\n Tap outside to close this popup.',
                                        theme_text_color="Custom",
                                        text_color=(1, 1, 1, 1)),
                        size_hint=(1, 0.3))
            popup.open()
            print('Query to yahoo finance failed.')
            self.logger0.info('Last query failed.')

    def runPaths(self,t1res,t2res,fetchVarName):
        self.datadf=t1res
        self.instrNameScrape=t2res
        self.t1=self.pool.submit(bootstrapAndSim,t1res)
        self.t3=self.pool.submit(self.checkStatus,fetchVarName,'95CI & price paths...')
        self.checkCompletion=Clock.schedule_interval(partial(self.checkThreadsDone,self.buildRes),0.01)


    def checkThreadsDone(self,callNextFuncOnMain,dt):
        if self.t3.done():
            self.checkCompletion.cancel()
            callNextFuncOnMain(self.t1.result(),self.t2.result(),self.t3.result())


    def fetch_data(self):

        if len(self.screenList)>0:
            self.cleanThreads()
        # Get the start and end dates from the text inputs
        fetchRic = self.root.ids.ric_input.text.upper()
        fetchStart = self.root.ids.start_date_input.text
        fetchEnd = self.root.ids.end_date_input.text
        fetchVarName = fetchRic+"_"+fetchStart+"_"+fetchEnd
        self.currentName=fetchVarName
        if fetchVarName not in self.screenList:

            self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
            self.t1=self.pool.submit(callYfinance, fetchRic,fetchStart,fetchEnd)
            self.t2=self.pool.submit(getInstrumentName, fetchRic)
            self.t3=self.pool.submit(self.checkStatus,fetchVarName,'Fetching data.')

            self.checkCompletion=Clock.schedule_interval(partial(self.checkThreadsDone,self.checkQueryIsGoodToGo),0.01)


        else:
            print("Query exists in previous screen, showing that screen again.")
            self.varNameDict[fetchVarName].manager.current = fetchVarName
            self.root.ids.nav_drawer.set_state("close")


    def build(self):
        self.ads = KivMob(TestIds.APP)
        self.screenList=[]
        self.screenListMore=[]
        self.ads.new_banner(TestIds.BANNER, top_pos=False)
        self.ads.request_banner()
        self.ads.show_banner()
        self.varNameDict={}
        self.varNameMoreDict={}
        prdDateString=prodDateString()
        with open("main_loadText.txt", 'r') as f:
            content=f.read()
            content=content % (prdDateString.soy(),prdDateString.prevBday(0))
            with open("main.kv",'w') as fe:
                fe.write(content)
        Builder.load_file("main.kv")
        self.root.ids.prevFetched_msg.text=''
        #logging.basicConfig(filename='kikou.log', encoding='utf-8', level=logging.INFO)
        self.logger0 = logging.getLogger()
        self.logger0.addHandler(MyLabelHandler(self.root.ids.logger_text,logging.INFO))
        self.root.ids.nav_drawer.set_state("open")
        return self.cleanLogs()

    def cleanLogs(self):
        Clock.schedule_once(lambda x:self.logger0.info(''),3)

MainApp().run()