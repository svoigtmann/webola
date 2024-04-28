from PyQt5 import QtCore
from PyQt5.Qt import QLabel, QPushButton, QVBoxLayout, QFrame

from webola.team import TeamButton
from webola.containers import HBoxContainer
from webola.dialogs import AskRemoveStarter

from pony import orm

class ButtonGroup(QFrame):
    
    log_msg = QtCore.pyqtSignal(str)
    team_number_changed = QtCore.pyqtSignal(int)

    def __init__(self, n, tab, teams):
        QFrame.__init__(self)
        
        self.lauf = tab

        v = QVBoxLayout()
        v.addStretch()
        self.setLayout(v)
        self.setMinimumHeight(200)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        
        self.update_button_anzahl(n, teams)

    
    @staticmethod
    def multisort(xs, specs):
        for get, reverse in reversed(specs):
            xs.sort(key=lambda b: get(b) , reverse=reverse)
        return xs

    @staticmethod
    def sorted_buttons(buttons):
        return ButtonGroup.multisort(buttons, ((lambda b: b.team.is_dsq()           , True),
                                               (lambda b: b.team.running            , True ),
                                               (lambda b: b.team.schiessen      or 0, True ),
                                               (lambda b: b.team.schiessen_time or 0, False),
                                               (lambda b: b.team.nummer             , False)))
        
    def sort(self, running=False):                  
        if running:
            for idx,button in enumerate(ButtonGroup.sorted_buttons(self.clear())):
                self.add(button, idx=idx)        
        else:
            for button in self.clear():
                self.add(button, pos=True)
        
    def scale_fonts(self, new):
        for _,b in self.enumerate():
            b.scale_fonts(new)
                    
    def count(self):
        return self.layout().count()-1
    
    def button(self, idx):
        n = self.count() 
        if n == 0: 
            return None
        else:
            assert 0 <= idx < n
            return self.layout().itemAt(idx).widget()
        
    def first(self): return self.button(0)
    def last (self): return self.button(self.count()-1)
    
    def list(self):
        for idx in range(self.count()):
            yield self.layout().itemAt(idx).widget()

    def enumerate(self):
        for idx in range(self.count()):
            w = self.layout().itemAt(idx).widget()
            yield idx, w 

    def find(self, key):
        for _, w in self.enumerate():
            if w.team.key_nummer() == key:
                return w
        #raise Exception('Item with id == %d not found.' %key)
        return None
                
    def prepare_auto_start(self):
        for idx, w in self.enumerate():
            if idx > 0: w.connect_tics()

    def prepare_manual_start(self):
        for idx, w in self.enumerate():
            if idx > 0: w.disconnect_tics()
            
    def renumber(self):
        for idx, w in self.enumerate():
            w.team.platz = idx+1
            w.update()
        orm.commit()
        
    def update_display(self):
        for _, w in self.enumerate():
            w.update()
        
    def update_offset(self, n):
        for idx, w in self.enumerate():
            w.offset = idx*n
            tt = self.lauf.toolbar.stoppuhr.elapsed() 
            w.update_time( tt )
        
    def update_button_anzahl(self, n, teams=[]):
        self.lauf.toolbar.anzahl.setEnabled(False)
        # maybe add more buttons ...
        assert len(teams) in (0,n)
        team = lambda k: teams[k] if teams else None 
        for k in range(self.count(), n):
            self.insert_new_button(self.last(), +1, team(k))
        # ... or maybe delete buttons 
        for k in reversed(range(n,self.count())):
            but = self.button(k)
            remove_ok = True
            if not but.team.is_empty():
                dlg = AskRemoveStarter(but)
                remove_ok = dlg.exec() == AskRemoveStarter.Ok
            if remove_ok:
                but.setParent(None)
                but.deleteLater()
                for s in but.team.starter:
                    s.delete()
                but.team.delete()
                
        self.team_number_changed.emit(self.count())
        self.lauf.toolbar.anzahl.setEnabled(True)
        
    def add(self, b, pos=False, idx=None):
        if idx is None:
            if pos:
                idx = self.find_position_by_time(b)
                b.team.platz = idx+1
            else:
                idx = self.find_position_by_id(b.team.nummer)
                b.team.platz = None
        self.layout().insertWidget(idx, b)
        b.update()
        if pos: self.renumber()
        orm.commit()
        
    def find_position_by_id(self, num):
        for idx, w in self.enumerate():
            if w.team.nummer > num: 
                return idx
        return self.count()
        
    def find_position_by_time(self, b):
        this   = b.team.zeit()             
        offset = 0
        for idx, w in self.enumerate():
            that = w.team.zeit()
            this_faster_than_that = ( (this >= 0 and that < 0   ) or               # this team has started, but that team not
                                      (this >= 0 and that > this) or               # both teams have started, but this team is faster 
                                      (this <  0 and that < 0 and this > that) )   # no team has started, but this team will start later

            
            
            if w==b: offset = -1
            if w!=b and (
                (not b.team.is_dsq() and     w.team.is_dsq()) or # this team is active, but that team is disqualified
                (not b.team.is_dsq() and not w.team.is_dsq() and this_faster_than_that) or 
                (    b.team.is_dsq() and     w.team.is_dsq() and this_faster_than_that) ): 
                return idx+offset
        return self.count()+offset
    
    def clear(self):
        buts = []
        for _, but in self.enumerate():
            buts.append(but)
        for but in reversed(buts):
            but.setParent(None)
        return buts

    def insert_new_button(self, button, offset, team=None):
        if button is None:
            pos = 0
            num = 1
        else:
            # find position of button in the widget list
            pos = [ p for p,b in self.enumerate() if b == button ]
            assert len(pos) == 1
            # compute position where to insert new button (offset==0 or offset==1)
            pos = pos[0] + offset
            # provide team start number (may be a duplicate here)
            if offset == 1:
                num = button.team.nummer + 1
            else:
                num = button.team.nummer
                button.team.nummer +=1
            
        new = TeamButton(num, self.lauf, team)
        new.team.update_anzahl(self.lauf.staffel())
        new.log_msg.connect(lambda txt: self.log_msg.emit(txt))
        #new.log("Insert new TeamButton with number %d." % idx)
        self.layout().insertWidget(pos, new)
        self.reinsert(self.clear())
        self.team_number_changed.emit(self.count())

    def reinsert(self, buttons):
        # (1) ensure consistent button height by re-inserting all buttons
        # (2) ensure consistent team numbers by renumbering buttons (if needed)
        numbers = set()
        for idx,b in enumerate(buttons):
            while b.team.nummer in numbers:
                b.team.nummer += 1
            numbers.add(b.team.nummer)
            b.update(first=buttons[0])
            self.layout().insertWidget(idx,b)
            b.update_tooltip()

    def remove_button(self, button):
        team = button.team
        for s in team.starter:
            s.delete()
        team.delete()
        buts = [ b for b in self.clear() if b != button ]        
        self.reinsert(buts)
        
        self.team_number_changed.emit(self.count())
        
class Grid(HBoxContainer):
    
    log_msg = QtCore.pyqtSignal(str)

    def __init__(self, n, lauf, tab):
        HBoxContainer.__init__(self)
        if lauf:
            left  = sorted([ t for t in lauf.teams if t.platz is     None ], key=lambda t: t.nummer)
            right = sorted([ t for t in lauf.teams if t.platz is not None ], key=lambda t: t.platz )
        else:
            left  = []
            right = []        
              
        self.starter  = self.add( ButtonGroup(len(left ), tab, left ) )
        self.ergebnis = self.add( ButtonGroup(len(right), tab, right) )
                
        self.starter .log_msg.connect(lambda txt: self.log_msg.emit(txt))
        self.ergebnis.log_msg.connect(lambda txt: self.log_msg.emit(txt))
        
        self.starter.setFocus()

    def scale_fonts(self, new): 
        self.starter .scale_fonts(new)
        self.ergebnis.scale_fonts(new)
        
    def reset(self, n):
        self.starter .clear()
        self.ergebnis.clear()
        self.starter.update_button_anzahl(n)
        
    def labelled_widget(self, label, widget, button=False):
        info = QPushButton(label) if button else QLabel(label)
        self.addWidget(info)
        self.addWidget(widget)
        return widget

    def find(self, n):
        s = self.starter.find(n)
        return s if s is not None else self.ergebnis.find(n)
        