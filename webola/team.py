from PyQt5 import QtCore
from PyQt5.Qt import Qt, QMenu, QFont, QDialog, QMessageBox, QColor, QFontMetrics

from pony import orm
from math import ceil

from webola.buttons import SubtitleButton
from webola.utils import time2str
from webola.dialogs import AskModified, AskRestart, Edit
from webola import database
import webola

def get_parent(base, typ):
    parent = base.parent()
    assert isinstance(parent, typ)
    return parent        

def with_update_tooltip(func):
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        button = args[0]
        assert isinstance(button, TeamButton)
        button.update_tooltip()
    return wrapper

class TeamButton(SubtitleButton):
    
    log_msg = QtCore.pyqtSignal(str)
                 
    @with_update_tooltip   
    def __init__(self, num, lauf, team=None):
        SubtitleButton.__init__(self, self.was_clicked)
        self.team     = team or database.Team(nummer=num,lauf=lauf.lauf,wertung=1)
        self.lauf     = lauf
        self.offset   = 0
        self.modified = False

        self.set_monospace_font()
        
        self.connect_tics()
        self.enable_context_menu(self.context_menu)
        self.lauf.toolbar.display_mode.valueChanged.connect(lambda: self.update())

    def id2k(self, F=False): 
        n   = self.team.key_nummer()
        key = str(n % 10)
        if F:
            if n in (10,20): key = '10'
            key = 'F'+key
        if n>10: key = 'Ctrl+'+key
        return key

    def id2f(self): return self.id2k(F=True) 
        
    def ak  (self): return self.team.tooltip_summary() + ('' if self.team.wertung else " (außer Konkurrenz)") + "\n\n"
    def mtp (self, fmt): return self.ak() + fmt % (            self.id2f()) # Make Tool Tip
    def mtpm(self, fmt): return self.ak() + fmt % (self.id2k(),self.id2f()) # Make Tool Tip with number in the Middle 
    def mtpb(self, fmt): return self.ak() + fmt % (self.id2k(),self.id2f()) # Make Tool Tip with number at the Back

    def update_tooltip(self):
        if   self.need_start  (): self.setToolTip(self.mtpm('Starten mit %s, %s oder Linksklick,\nBearbeiten mit Rechtsklick'))
        elif self.can_stop    (): self.setToolTip(self.mtpm('Schießen markieren mit %s, Stoppen mit %s oder Linksklick,\nBearbeiten mit Rechtsklick'))
        elif self.can_restart (): self.setToolTip(self.mtp ('Zurücknehmen mit %s oder Linksklick,\nBearbeiten mit Rechtsklick'))
        elif self.lauf.is_done(): self.setToolTip(self.mtpb('Bearbeiten mit %s, %s oder Linksklick'))
        else:                     self.setToolTip(self.mtpb('Bearbeiten mit %s, %s oder Linksklick\nStarter löschen oder einfügen mit Rechtsklick'))

    #def __str__(self): return self.team.string( self.lauf.grid.ergebnis.first() )
    
    def zeit       (self): return self.team.zeit()
    def laufzeit   (self): return self.team.laufzeit()
    def fehler     (self): return self.team.fehler()
    def ist_staffel(self): return self.team.ist_staffel()
    def name       (self): return self.team.name
            
    def text_color(self, color):
        # change color without using Html/styleSheets since both collapse spaces
        palette = self.palette()
        palette.setColor(self.foregroundRole(), color)
        self.setPalette(palette)

    def enable_context_menu(self, slot):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(slot)

    def connect_tics   (self): 
        self.lauf.tic_signal().connect(self.update_time)
    
    def disconnect_tics(self): 
        try:
            self.lauf.tic_signal().disconnect(self.update_time)
        except:
            pass

    def context_menu(self, point):
        menu     = QMenu()
        num      = self.team.nummer
        increase = lambda: self.lauf.find_and_mark(num, add=+1 )
        decrease = lambda: self.lauf.find_and_mark(num, add=-1 )
        
        if self.lauf.is_running():
            menu.addAction("Bearbeiten", self.edit)        
             
            if self.need_start() : 
                menu.addAction("Start"                  , self.start  , self.id2f())                          
            if self.can_stop()   : 
                menu.addAction("Stop"                   , self.stop   , self.id2f())
                menu.addAction("Schießen markieren"     , increase    , self.id2k())
                menu.addAction("Markierung zurücknehmen", decrease    , 'Shift+'+self.id2k())
            if self.can_restart(): 
                menu.addAction("Restart"                , self.restart, self.id2f())
        
        else: 
            menu.addAction("Bearbeiten", self.edit   , '%s, %s' % (self.id2k(),self.id2f()))        
            group = get_parent(self , webola.grid.ButtonGroup) 
            grid  = get_parent(group, webola.grid.Grid) 
            run   = get_parent(grid , webola.run.RunTab) 

            max_starter = run.toolbar.anzahl.maximum()
            if not self.lauf.is_done():
                if self.parent().count() < max_starter:
                    sub = menu.addMenu('Starter einfügen ...')
                    sub.addAction("oberhalb" , lambda: self.parent().insert_new_button(self, +0))
                    sub.addAction("unterhalb", lambda: self.parent().insert_new_button(self, +1))
                menu.addAction('Starter löschen', lambda: self.parent().remove_button(self))

        menu.exec(self.mapToGlobal(point))
                
    def was_clicked(self):
        if    self.need_start() : self.start  ()
        elif  self.can_stop()   : self.stop   ()
        elif  self.can_restart(): self.restart()
        else: self.edit() 

    def need_start  (self): return self.lauf.is_running() and not self.team.has_finished() and self.zeit() == 0
    def can_stop    (self): return self.lauf.is_running() and not self.team.has_finished() and self.zeit() > 0
    def can_restart (self): return self.lauf.is_running() and     self.team.has_finished()
    
    def log(self, msg, idx=None):
        if idx is None:
            idx = self.team.running or 0
        self.log_msg.emit("<span style='color:green;'>%s Nr. %2d</span> %s%s (%d/%d) total=<strong>%s</strong>" % (
            self.lauf.name(),
            self.team.nummer, msg, max(0,7-len(msg))*".", 
            idx+1, self.lauf.staffel(), time2str(self.team.zeit())))

    @with_update_tooltip
    def start(self):
        assert not self.team.has_finished()
        offset = self.lauf.toolbar.stoppuhr.elapsed() 
        self.offset = offset
        self.connect_tics()

    @with_update_tooltip
    def stop(self):
        assert not self.team.has_finished()
        idx = self.team.running
        if self.team.stop(self.lauf.toolbar.stoppuhr.elapsed()):
            self.log('STOP', idx)
            self.disconnect_tics()
            self.lauf.grid.ergebnis.add(self, pos=True)
        else:
            self.log('NEXT',idx)
            self.lauf.grid.starter.sort(running=True)

    @with_update_tooltip
    def restart(self):
        assert self.team.has_finished()
        if self.modified:
            if AskModified(self).exec() == QMessageBox.Cancel:
                self.log('RESTART CANCELLED')
                return
        else:
            if AskRestart(self).exec() == QMessageBox.Cancel:
                self.log('RESTART CANCELLED')
                return
        self.log('RESTART',len(self.team.starter)-1)
        self.modified = False
        self.connect_tics()
        self.lauf.grid.starter.add(self, pos=False)
        self.lauf.grid.ergebnis.renumber()
        self.team.running = self.team.anzahl()-1
        self.update()
        
    @with_update_tooltip
    def reset(self, nummer):
        self.log('RESET', self.team.anzahl()-1)
        self.modified = False
        if self.team.platz is not None:
            self.lauf.grid.starter.add(self, pos=False)
        self.team.reset()
        self.update()
        orm.commit()
        
    def edit(self):
        first = self.lauf.grid.ergebnis.first()
        self.log("EDIT START {%s, %s}" % (self.team.string(first), time2str(self.zeit())))
        dlg = Edit(self.team)
        if dlg.exec() == QDialog.Accepted:
            modified = dlg.show_update()
            self.lauf.grid.ergebnis.sort()
            self.update_tooltip()
            self.update()
            if modified:
                assert self.team.has_finished() 
                self.lauf.grid.ergebnis.add(self, pos=True)
        self.log("EDIT DONE. {%s, %s}" % (self.team.string(first), time2str(self.zeit())))
        orm.commit()
        
    def update_time(self, tt):
        idx     = self.team.running or 0        
        starter = self.team.liste()[idx]
        others  = sum( s.laufzeit for s in self.team.liste()[:idx] )
        time    = tt - self.offset - others
        if self.team.running is None and time > 0:
            self.team.running = 0
        starter.laufzeit = time 
        self.update()

    def maybe_shorten(self, w, prefix, stem, suffix=""):
        w = max(4, w - len(prefix) - len(suffix) -2) # two spaces
        stem = stem[:w-3]+'...' if len(stem) > w else stem
        stem = f"%-{w}s" % stem
        if suffix == "":
            if self.ist_staffel():
                return f"{prefix} | {stem}"
            else:
                return f"{prefix} {stem}"
        else:
            return f"{prefix} {stem} {suffix}" 

    def update(self, first=None):
        if first is None:
            try:
                first = self.lauf.grid.ergebnis.first()
            except AttributeError: 
                # ignore initialisation error: 'RunTab' object has no attribute 'grid'
                first = None

        if self.team.has_finished():
            assert first is not None   
                
        if self.lauf.webola.top_text_width is None or self.lauf.webola.bot_text_width is None:
            self.compute_button_text_width()
    
        team_then_name = self.team.has_finished() or self.lauf.display_mode_team_or_name()
        top = self.team.string(first, current=not team_then_name, parts=True)
        bot = self.team.info  (       current=    team_then_name, parts=True)
        
        text = self.maybe_shorten(self.lauf.webola.top_text_width, *top)
        info = self.maybe_shorten(self.lauf.webola.bot_text_width, *bot)
                
        self.setText(text, info)
        
        delta = self.lauf.shootings() - (self.team.schiessen or 0)
        tt    =  self.zeit()
        color = Qt.black      if (not self.lauf.is_running() or
                                  self.team.has_finished()) else (
                Qt.darkYellow       if -20 <= tt < -10 else (
                Qt.darkRed          if -10 <= tt <   0 else (
                Qt.darkGreen        if   0 <= tt <  10 else (
                Qt.darkRed          if   0 == delta    else ( 
                QColor('goldenrod') if   1 == delta    else ( 
                Qt.darkGreen        if   2 == delta    else ( 
                Qt.black )))))))
        self.text_color(color)
            
    def set_monospace_font(self):
        font = QFont("Monospace");
        font.setStyleHint(QFont.TypeWriter);
        self.setFont(font)
        SubtitleButton.scale_fonts(self, font.pointSize()) # scale fonts but do not call update()

    def available(self, text, label):
        metrics = QFontMetrics(label.font())
        width   = metrics.boundingRect(text).width()+175
        cw      = width/len(text)
        return ceil(self.width() / cw)

    def compute_button_text_width(self):
        text = '1---5---'+"---".join(str(5*n) for n in range(2,35))
        top = self.available(text, self.main)
        bot = self.available(text, self.sub )
        self.setText(text[:top], text[:bot])
        self.lauf.webola.top_text_width = top
        self.lauf.webola.bot_text_width = bot

    def scale_fonts(self, new):
        SubtitleButton.scale_fonts(self, new)        
        self.update()

if __name__ == '__main__':
    from PyQt5.Qt import QApplication, pyqtSignal, QObject
    from types import SimpleNamespace
    import sys
    
    class MockWebola(QObject):
        def __init__(self):
            self.top_text_width=None
            self.bot_text_width=None
        def width(self): return 1000
        
    class MockDisplayMode(QObject):
        valueChanged = pyqtSignal()
    
    class MockLauf(QObject):
        tic = pyqtSignal()
        def __init__(self): 
            super().__init__()
            self.toolbar = SimpleNamespace(display_mode=MockDisplayMode())
            self.webola  = MockWebola()
        def shootings(self): return 3
        def tic_signal(self): return self.tic
        def is_running(self): return False
        def is_done(self): return False
        def display_mode_team_or_name(self): return True
    
    class MockTeam(QObject):
        def __init__(self):
            super().__init__()
            self.wertung = True
            self.schiessen = 0
        def zeit(self): return 0
        def has_finished(self): return False
        def key_nummer(self): return 1
        def tooltip_summary(self): return "Tooltip"
        def info(self,current,parts): return 'Verein','' 
        def ist_staffel(self): return False
        def string(self,first,current,parts): 
            prefix = "  ".join(['*',"/"," 1"]) 
            stem   = 'Vorname Nachname' 
            suffix = "  ".join(["00:00.0", "%-8s"  % '', "[%2s]" % "--"])
            return prefix, stem, suffix

    app = QApplication(sys.argv)
    b = TeamButton(12,MockLauf(),MockTeam())
    b.update()
    #b.setText('Vorname Name', 'Der Verein hat einen langen Namen')
    #b.scale_fonts(10)
    b.show()
    app.exec()
