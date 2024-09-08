from PyQt5.Qt import Qt, QFrame, QVBoxLayout, QShortcut, QKeySequence, QTimer

import itertools
from pony import orm
from datetime import datetime

from webola.grid import Grid
from webola.toolbar import ToolBar
from webola import utils
from webola.dialogs import GroupEdit

class RunTab(QFrame):

    def __init__(self, webola, lauf, args, parent=None):
        QFrame.__init__(self, parent)
        
        self.lauf   = lauf
        self.webola = webola
        n = len(lauf.teams)
            
        self.toolbar = ToolBar(n, lauf, args, parent=self)
        self.grid    = Grid(self.toolbar.get_anzahl(), lauf, self)
        
        if self.grid.ergebnis.count() > 0:
            self.toolbar.mark_as_finished()
        
        self.toolbar.groupedit.clicked     .connect(self.group_edit)
        self.toolbar.anzahl.valueChanged   .connect(self.grid.starter.update_button_anzahl)
        self.toolbar.offset.valueChanged   .connect(self.grid.starter.update_offset)
        self.toolbar.offset_button.clicked .connect(self.offset_button_clicked     )
        self.toolbar.editing_finished      .connect(self.editing_finished          )
        self.toolbar.staffel_button.clicked.connect(self.update_display            )
        self.toolbar.staffel.valueChanged  .connect(self.update_display            )
        self.toolbar.start.start           .connect(self.run_was_started           )
        self.toolbar.reset_clicked         .connect(self.reset_clicked             )
        
        self.grid.starter.team_number_changed.connect(lambda n: self.toolbar.anzahl.setValue(n))
        
        log_msg = lambda txt: webola.log.msg(txt, self.toolbar.stoppuhr.elapsed())
        self.toolbar.log_msg               .connect(log_msg)
        self.grid   .log_msg               .connect(log_msg)
        
        self.make_Fn_key_shortcuts()
            
        QShortcut(Qt.Key_Home           , self, lambda: self.toolbar.start.process_click(True ))
        QShortcut(Qt.Key_End            , self, lambda: self.toolbar.start.process_click(False))
        QShortcut(Qt.Key_Pause          , self, lambda: self.toolbar.start .click())
        QShortcut(Qt.CTRL+Qt.Key_S      , self,         self.group_edit)
        
        v = QVBoxLayout()
        v.addWidget(self.toolbar)
        v.addWidget(self.grid   )        
        
        self.setLayout(v)
        self.grid.setFocus()
        self.editing_finished()
        
    def display_mode_team_or_name(self):
        return self.toolbar.display_mode.state
    
    def group_edit(self):
        dlg = GroupEdit(self.lauf)
        if dlg.exec(): 
            dlg.ok_pressed()
            self.grid.starter .update_display()
            self.grid.ergebnis.update_display()

    def editing_finished(self):
        self.lauf.titel            = self.toolbar.run.text()
        self.lauf.startzeit        = self.toolbar.startzeit.text()
        self.lauf.anzahl_schiessen = self.toolbar.schiessen.value()
        self.lauf.anzahl_pfeile    = self.toolbar.pfeile.value()
        self.lauf.auto_start       = self.toolbar.offset_button.isChecked()
        self.lauf.start_offset     = self.toolbar.offset.value()
        self.lauf.team_groesse     = self.toolbar.staffel.value() if self.toolbar.staffel_button.isChecked() else None
        
        orm.commit()
                
        self.grid.setFocus()
        
    def update_tooltips(self):
        for _,b in itertools.chain(self.grid.starter.enumerate(),
                                   self.grid.ergebnis.enumerate()):
            b.update_tooltip()        
        
    def scale_fonts(self, new): self.grid.scale_fonts(new)
    
    def make_Fn_key_shortcuts(self):
        for key in list("1234567890"):
            n = 10 if key == '0' else int(key)
            self.make_shortcuts(key, n)
                        
        QShortcut(Qt.Key_F11, self, lambda: self.find_and_click(11))
        QShortcut(Qt.Key_F12, self, lambda: self.find_and_click(12))
        QShortcut(Qt.Key_F13, self, lambda: self.find_and_click(13))
        QShortcut(Qt.Key_F14, self, lambda: self.find_and_click(14))
                
    def make_shortcuts(self, key, n):
        QShortcut(                  Qt.Key_F1+n-1, self, lambda: self.find_and_click(n           )) #  1-10 start/stop/resart
        QShortcut(          Qt.CTRL+Qt.Key_F1+n-1, self, lambda: self.find_and_click(n+10        )) # 11-20 start/stop/resart
        QShortcut(                           key , self, lambda: self.find_and_mark (n           )) #  1-10 increase round count
        QShortcut(QKeySequence(      'Ctrl+'+key), self, lambda: self.find_and_mark (n+10        )) # 11-20 increase round count
        QShortcut(QKeySequence('Shift+'     +key), self, lambda: self.find_and_mark (n   , add=-1)) #  1-10 decrease round count
        QShortcut(QKeySequence('Shift+Ctrl+'+key), self, lambda: self.find_and_mark (n+10, add=-1)) # 11-20 decrease round count
    
    def find_and_mark(self, n, add=1):
        if self.is_running():
            but = self.grid.find(n)
            if but and but.team.zeit() > 0 and not but.team.has_finished():
                but.log('SHOOT') 
                but.team.next_shooting(self.shootings(), add, self.toolbar.stoppuhr.elapsed())
                self.grid.starter.sort(running=True)
        else:
            self.find_and_click(n, edit=True)
        
    def find_and_click(self, n, edit=False):
        but = self.grid.find(n)
        if but is None: return
        if edit:
            but.edit()
        else:
            but.was_clicked()  

    def update_display(self):
        n = self.toolbar.staffel_anzahl()
        for _,b in self.grid.starter.enumerate():
            b.team.update_anzahl(n)
            b.update_tooltip()
            b.update()

    def offset_button_clicked(self, checked):
        self.grid.starter.update_offset(self.toolbar.get_offset())
        if checked:
            self.grid.starter.prepare_auto_start()
        else:
            self.grid.starter.prepare_manual_start()

    def run_was_started(self):
        startzeit = f"{datetime.now().strftime('%H:%M')}"
        self.lauf.startzeit = startzeit
        self.toolbar.startzeit.setText(startzeit)
        QTimer.singleShot(250, self.update_tooltips)
        
    def reset_clicked(self):
        for idx,b in enumerate(itertools.chain(list(              self.grid.starter .list()),
                                 list(reversed(list(self.grid.ergebnis.list()))))):
            b.reset(idx+1)
            b.disconnect_tics()
        
        # always let the first starter start automatically
        first = self.grid.starter.first()
        if first: first.connect_tics()
        self.toolbar.display_mode.setEnabled(True)
        
        # set other starters behaviour depending on auto/manual switch
        self.offset_button_clicked(self.toolbar.offset_button.isChecked())
        # number_of_connections = self.toolbar.stoppuhr.receivers(self.toolbar.stoppuhr.tic)
        
    def is_running(self): return self.toolbar.is_running()
    def is_done   (self): return self.toolbar.is_done()
    def tic_signal(self): return self.toolbar.stoppuhr.tic
    def shootings (self): return self.toolbar.shootings()
    def staffel   (self): return self.toolbar.staffel_anzahl()
    def is_staffel(self): return self.staffel() > 1

    def startinfo (self): 
        #time = utils.join_nonempty('/', self.toolbar.startzeit.text(), self.toolbar.run_start_str())
        time = self.toolbar.startzeit.text()
        time = "Startzeit %s" % time if len(time) else ""
        return utils.join_nonempty(' .. ', self.toolbar.run.text(), time)
    
    def get_statistics(self):
        return self.grid.starter.count(), self.grid.ergebnis.count()
    
    def tab_widget(self):
        return self.parent().parent()
    
    def name(self):
        parent = self.tab_widget()
        tabs   = [ parent.widget(idx) for idx in range(parent.count()) ]
        tab    = [ idx for idx,t in enumerate(tabs) if t == self ]
        assert len(tab) == 1
        return parent.tab_name(tab[0])
