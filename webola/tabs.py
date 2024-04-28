from PyQt5 import Qt

from webola.sheet import SheetTab
from webola.run import RunTab

from webola import database
from PyQt5.Qt import QMessageBox, QTabBar, QMenu
from pony.orm.core import commit
from webola.database import Lauf

class TabBar(QTabBar):
    def __init__(self):
        super().__init__()
        self.was_drag = False   
        
    def set_drag(self):
        self.was_drag = True
        
    def mouseReleaseEvent(self, *args, **kwargs):
        if self.was_drag:
            self.parent().renumber_tabs()
        self.was_drag = False
        return QTabBar.mouseReleaseEvent(self, *args, **kwargs)     

class WebolaTabs(Qt.QTabWidget):
    def __init__(self, webola, args):
        Qt.QTableWidget.__init__(self)
        self.sheet = None # needed for initial call to renumber_tabs when no sheet is present
        self.setTabBar(TabBar())
        self.setMovable(True)
        #self.setTabsClosable(True)

        self.args   = args # needed by new_tab when creating Finallaeufe
        self.webola = webola
        self.neu = Qt.QToolButton(self)
        self.neu.setIcon(Qt.QIcon(":/plus.png"))
        self.neu.setCursor(Qt.Qt.ArrowCursor)
        self.neu.setAutoRaise(True)
        self.neu.setToolTip("Neuen Lauf hinzufügen")
        self.setCornerWidget(self.neu, Qt.Qt.TopLeftCorner)
        
        self.sheet = self.new_result_tab(webola)
        self.currentChanged.connect(self.current_tab_changed)


        self.tabBar().setContextMenuPolicy(Qt.Qt.CustomContextMenu)     
        self.tabBar().customContextMenuRequested.connect(self.edit_day_markers)

        self.tabBar().tabMoved  .connect(        self.tabBar().set_drag    )
        self.neu.clicked        .connect(lambda: self.new_tab(webola, args))

    def tabRemoved(self, *args, **kwargs):
        self.renumber_tabs()
        return Qt.QTabWidget.tabRemoved(self, *args, **kwargs)

    def tabInserted(self, *args, **kwargs):
        self.renumber_tabs()
        return Qt.QTabWidget.tabInserted(self, *args, **kwargs)

    def edit_day_markers(self, point):
        idx = self.tabBar().tabAt(point)
        run = self.widget(idx)
        if not isinstance(run, RunTab): return  
        
        menu = QMenu()
        if self.webola.wettkampf.has_day_markers():
            menu.addAction('Tag-Marker neu setzen', lambda: self.mark_another_day(idx))
            menu.addAction('Tag-Marker entfernen' , lambda: self.remove_day_marks(idx))
        else:
            menu.addAction('Tag-Marker setzen'    , lambda: self.mark_another_day(idx))
        
        menu.addAction('Lauf löschen'             , lambda: self.remove_tab(idx))
        menu.exec_(self.tabBar().mapToGlobal(point))   
        
    def remove_day_marks(self, idx):
        for i,tab in self.enumerate_run_tabs():
            tab.lauf.wettkampf_tag = 1
            tab.lauf.cleanup_name_from_wettkampf_tag()
            self.setTabText(i, tab.lauf.name)        
        commit()
        
    def mark_another_day(self, idx):        
        for i,tab in self.enumerate_run_tabs():
            tag    = 1 if i < idx else 2
            tab.lauf.wettkampf_tag = tag
            tab.lauf.update_name_for_wettkampf_tag()
            self.setTabText(i, tab.lauf.name)        
        commit()

    def remove_tab(self, idx):
        tab = self.widget(idx)
        if isinstance(tab,SheetTab) or tab.is_running(): return

        name = self.tab_name(idx)
        ans  = QMessageBox.question(self, 'Tab löschen', 
                                         f"Soll der Tab '{name}' wirklich gelöscht werden?", 
                                         QMessageBox.Yes, QMessageBox.No)
        if ans == QMessageBox.Yes:
            lauf = self.widget(idx).lauf
            for t in lauf.teams:
                for s in t.starter:
                    s.delete()
                t.delete()
            lauf.delete()
            commit()
            self.removeTab(idx)
        
    def fill_from_db(self, webola, args):
        self.blockSignals(True)
        for lauf in sorted(Lauf.select(lambda l: l.wettkampf == webola.wettkampf), key=lambda l: l.tab_position):
            self.new_tab(webola, args, lauf)
        self.sheet.fill_tree()
        self.blockSignals(False)
        self.setCurrentIndex(0)
        return len(self.runs())
            
    def maybe_add_tabs_for_finallaeufe(self):
        for finallauf in (self.webola.wettkampf.laeufe - {r.lauf for r in self.runs()}):
            assert finallauf.finallauf

            tabs = [ r for r in self.runs() if r.lauf in finallauf.vorlaeufe() ]
            tab_widget = tabs[0].tab_widget()
            to_idx = max(tab_widget.indexOf(t) for t in tabs)+1

            run = self.new_tab(self.webola, self.args, finallauf)
            from_idx = tab_widget.indexOf(run)
            
            tab_widget.tabBar().moveTab(from_idx, to_idx)
        
    def scale_font(self, new, fac):
        for r in self.runs():
            r.scale_fonts(new)
        
        self.sheet.scale_font(fac)
           
#    def rename_tab(self, idx):
#        tab = self.widget(idx)
#        if isinstance(tab,SheetTab) or tab.is_running(): return
#        title     = self.tab_name(idx)
#        forbidden = self.tab_names()+['Ergebnis']
#        forbidden.remove(title)
#        dlg = EditRunTitle(title, forbidden)
#        if dlg.exec() == dlg.Accepted:
#            if dlg.remove:
#                lauf = self.widget(idx).lauf
#                for t in lauf.teams:
#                    for s in t.starter:
#                        s.delete()
#                    t.delete()
#                lauf.delete()
#                orm.commit()
#                self.removeTab(idx)
#            else:
#                lauf = self.widget(idx).lauf
#                lauf.name = dlg.text()
#                orm.commit()
#                self.setTabText(idx, dlg.text())
#    
    def tab_name(self, idx=None):
        idx = self.currentIndex() if idx is None else idx
        return self.tabText(idx).replace('&','').rstrip('*')#.lstrip('(1) ').lstrip('(2) ')
    
    def tab_names(self):
        return [ self.tab_name(idx) for idx, _ in self.enumerate_run_tabs() ]

    def enumerate_all_tabs(self):
        for idx in range(self.count()):
            yield idx, self.widget(idx) 

    def enumerate_run_tabs(self):
        for idx,t in self.enumerate_all_tabs():
            if isinstance(t, RunTab):
                yield idx,t

    def runs(self):
        return [ t for _,t in self.enumerate_run_tabs() ]
    
    def show_run(self, lauf):
        for idx,r in self.enumerate_run_tabs():
            if r.lauf == lauf:
                self.setCurrentIndex(idx)
                return
            
    def current_tab_changed(self, idx):
        new = self.widget(idx)
        if isinstance(new, SheetTab):
            self.sheet.fill_tree()
          
    def new_result_tab(self, webola):
        title = "Ergebnis"
        sheet = SheetTab(webola)
        n = self.addTab(sheet, title)
        self.tabBar().setTabIcon(n,Qt.QIcon(":/xlsx.png"))
        return sheet
        
    def new_tab(self, webola, args, lauf=None):
        n = len(self.runs())
        forbidden = self.tab_names()+['Ergebnis']
                
        if not lauf:
            name = self.generate_name(n+1, forbidden)
            lauf = database.Lauf.create(name, n, webola.wettkampf)
            if n > 0:
                left = Lauf.get(lambda l: l.wettkampf == webola.wettkampf and l.tab_position == n-1)
                if left and left.wettkampf_tag == 2: 
                    lauf.wettkampf_tag = 2
                    lauf.update_name_for_wettkampf_tag()
        
        run = RunTab(webola, lauf, args)
        run.toolbar.start.clicked.connect(lambda: webola.tabs.tab_start_stop(webola, run))
        pos = lauf.tab_position
                
        self.insertTab(pos,run, lauf.name)
        self.tabBar().setTabToolTip(pos,'Tipp: Rechtsklick für Kontext-Menü')
        self.tabBar().setTabIcon(pos,Qt.QIcon(":/run.png"))
        self.setCurrentIndex(pos)
        run.toolbar.update_gui_state(self.runs())
        
        return run
    
    
    def tab_start_stop(self, webola, run):
        runs  = []
        for idx, r in self.enumerate_run_tabs():
            if r == run:
                self.update_is_running_marker(idx, run.is_running())
            else:
                runs.append(r)
        if  run.is_running():   
            for r in runs: r.toolbar.start.setEnabled(False)
        elif run.is_done():
            for r in runs: r.toolbar.start.setEnabled(True)
        else:
            pass # State.WAITING: must not happen

        webola.control.exit.setEnabled(not run.is_running())
    
    def generate_name(self, k, forbidden):
        title = "Lauf %d" % k
        return self.generate_name(k+1, forbidden) if title in forbidden else title

    def switch_tab(self, num):
        n   = self.count()
        idx = self.currentIndex()
        new = min(max(idx+num,0),n-1)
        self.setCurrentIndex(new) 

    def renumber_tabs(self):
        runs = self.runs()
        if self.sheet:
            idx = self.indexOf(self.sheet)
            if idx < len(runs): 
                self.tabBar().moveTab(idx,len(runs))
        
        mark_day = any(r.lauf.wettkampf_tag > 1 for r in runs)
        
        tag = 1
        for idx, tab in enumerate(runs):
            tag = max(tag,tab.lauf.wettkampf_tag)
            tab.lauf.wettkampf_tag = tag
            tab.lauf.tab_position  = idx
            if mark_day: 
                tab.lauf.update_name_for_wettkampf_tag()
                self.setTabText(idx, tab.lauf.name)

    def update_is_running_marker(self, idx, state):
        name = self.tab_name(idx).replace('*','')
        self.setTabText(idx, name + ('*' if state else ''))
        