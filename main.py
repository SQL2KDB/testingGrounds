from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivymd.uix.button import MDRectangleFlatButton
from buildTable import dfToScreen, callYfinance, createBarChart, createPricePlot, pricePlotSimulation, maxDrawDown, bestWinningStreak,getInstrumentName, bootstrapAndSim
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
        if len(self.screenList)>0:
            if "_more" in self.root.ids.rootScreenManager.current:
                self.root.ids.rootScreenManager.transition = SlideTransition(direction='right')
                self.varNameDict[self.root.ids.rootScreenManager.current.replace("_more","")].manager.current = self.root.ids.rootScreenManager.current.replace("_more","")
            else:
                self.root.ids.rootScreenManager.transition = SlideTransition(direction='left')
                self.varNameMoreDict[self.root.ids.rootScreenManager.current+'_more'].manager.current = self.root.ids.rootScreenManager.current+'_more'
        else:
            self.root.ids.nav_drawer.set_state("open")

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

            self.logger0 = logging.getLogger()
            self.logger0.addHandler(MyLabelHandler(self.root.ids.logger_text,logging.INFO))
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
        Builder.load_file("main.kv")
        self.root.ids.prevFetched_msg.text=''
        #logging.basicConfig(filename='kikou.log', encoding='utf-8', level=logging.INFO)

        return self.root.ids.nav_drawer.set_state("open")


MainApp().run()