from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivymd.uix.button import MDRectangleFlatButton
from buildTable import dfToScreen, callYfinance, createBarChart, createPricePlot, CIbounds, simulateTimeSeries, maxDrawDown, bestWinningStreak,getInstrumentName
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivmob_mod import KivMob, TestIds
import os

class InstrumentPage(Screen):
    pass

class ContentNavigationDrawer(MDBoxLayout):
    pass

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


    def fetch_data(self):
        # Get the start and end dates from the text inputs


        fetchRic = self.root.ids.ric_input.text.upper()
        fetchStart = self.root.ids.start_date_input.text
        fetchEnd = self.root.ids.end_date_input.text
        fetchVarName = fetchRic+"_"+fetchStart+"_"+fetchEnd
        self.currentName=fetchVarName
        if fetchVarName not in self.screenList:
            #preparing the main screen
            self.screenList.append(fetchVarName)
            self.varNameDict[fetchVarName]=Builder.load_file('pageTemplate.kv')
            self.varNameDict[fetchVarName].name = fetchVarName
            self.root.ids.rootScreenManager.add_widget(self.varNameDict[fetchVarName])

            self.screenListMore.append(fetchVarName+'_more')
            self.varNameMoreDict[fetchVarName+'_more']=Builder.load_file('pageMoreTemplate.kv')
            self.varNameMoreDict[fetchVarName+'_more'].name = fetchVarName+'_more'
            self.root.ids.rootScreenManager.add_widget(self.varNameMoreDict[fetchVarName+'_more'])

            summary_container = self.varNameDict[fetchVarName].ids.summary_container
            chart_container = self.varNameDict[fetchVarName].ids.chart_container
            table_header = self.varNameDict[fetchVarName].ids.table_header
            table_container = self.varNameDict[fetchVarName].ids.table_container

            datadf=callYfinance(fetchRic,fetchStart,fetchEnd)

            if len(datadf)>0:

                chart_container.clear_widgets()
                table_header.clear_widgets()
                table_container.clear_widgets()
                summary_container.clear_widgets()

                createBarChart(datadf,'dailyPerfBar_'+fetchVarName.upper()+'.png')
                createPricePlot(datadf,'pricePlot_'+fetchVarName.upper()+'.png')


                #start of page summary
                instrNameScrape=getInstrumentName(fetchRic)
                summary_container.add_widget(MDLabel(markup=True, text='[b]'+instrNameScrape+'[/b]',size_hint_y=None, height='15dp'))
                summary_container.add_widget(MDLabel(markup=True, text='   (queried from '+fetchStart+' to '+fetchEnd+')',size_hint_y=None, height='15dp'))
                summary_container.add_widget(MDLabel(markup=True, text='Daily performance stats:',size_hint_y=None, height='15dp'))

                #daily perf CI
                lbAvg,upAvg = CIbounds(0.05,datadf['ClosePctChg'],nbRuns=500, operatorType='average')
                lbMed,upMed = CIbounds(0.05,datadf['ClosePctChg'],nbRuns=500, operatorType='median')
                for d in [("Mean",datadf['ClosePctChg'].mean(),lbAvg,upAvg),
                          ("Median",datadf['ClosePctChg'].median(),lbMed,upMed)]:
                    dn=[d[0]]
                    for di in [d[1],d[2],d[3]]:
                        if di <0:
                            dn.append("[color=FF0000]"+"{:.2f}%".format(di)+"[/color]")
                        else:
                            dn.append("[color=008000]"+"{:.2f}%".format(di)+"[/color]")
                    dLabel=MDLabel(markup=True, text="   "+dn[0]+" at 95% CI: ("+dn[2]+";[b]"+dn[1]+"[/b];"+dn[3]+")",theme_text_color='Custom',size_hint_y=None, height='15dp')
                    summary_container.add_widget(dLabel)

                #Path simulation
                simPerfs = simulateTimeSeries(datadf['ClosePctChg'],nbSims=1000)
                below100=int(100*len(simPerfs[simPerfs<100])/len(simPerfs))
                below75=int(100*len(simPerfs[simPerfs<75])/len(simPerfs))
                below50=int(100*len(simPerfs[simPerfs<50])/len(simPerfs))
                dLabel=MDLabel(markup=True, text="Path [1000] simulations:",theme_text_color='Custom',size_hint_y=None, height='15dp')
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

                #add charts in the middle of the page
                chart_container.add_widget(Image(source='dailyPerfBar_'+fetchVarName.upper()+'.png', fit_mode='fill', nocache=True))
                chart_container.add_widget(Image(source='pricePlot_'+fetchVarName.upper()+'.png', fit_mode='fill', nocache=True))

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

            else:
                print('Query to yahoo finance failed.')
        else:
            print("Query exists in previous screen, showing that screen again.")
            self.varNameDict[fetchVarName].manager.current = fetchVarName
            self.root.ids.nav_drawer.set_state("close")

        if len(self.screenList)>0:
            self.root.ids.prevFetched_msg.text='Previously fetched queries:'
        else:
            self.root.ids.prevFetched_msg.text=''
        #self.ads.show_banner()
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
        return self.root.ids.nav_drawer.set_state("open")


MainApp().run()