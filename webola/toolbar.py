from PyQt5 import QtCore
from PyQt5.Qt import QLabel, QLineEdit, QSpinBox, QMessageBox, QSizePolicy,\
    QIcon, pyqtSignal

import time

from webola.buttons import NoFocusButton, ToolButton
from webola.containers import HBoxContainer
from webola.timer import Stoppuhr
from webola.state      import State
from webola.dialogs    import AskStop, AskRestartTab

import webola.icons # @UnusedImport @UnresolvedImport
import re

class ToggleSpinbox(QSpinBox):
    def __init__(self, parent=None):
        QSpinBox.__init__(self, parent)
    
    def use(self, toggle, state=True):
        toggle.set_widget(self, state)
        return self
    
    # do not highlight value after pressing +/-
    def stepBy(self, *args, **kwargs):
        QSpinBox.stepBy(self, *args, **kwargs)
        self.lineEdit().deselect()
        
class MinMaxSpinbox(ToggleSpinbox):
    def __init__(self, min_value, max_value=None, default=None, parent=None):
        ToggleSpinbox.__init__(self, parent)
        if max_value is None:
            self.setMinimum(min_value)
        else:
            self.setRange(min_value, max_value)
        if default: self.setValue(default)

class IncrementSpinbox(ToggleSpinbox):
    def __init__(self, incr, default=None, parent=None):
        ToggleSpinbox.__init__(self, parent)
        self.setSingleStep(incr)
        self.setSuffix(' s')
        if default: self.setValue(default)

class ToggleButton(NoFocusButton):
    def __init__(self, label, parent=None):
        NoFocusButton.__init__(self, label, self.toggle)
        self.setCheckable(True)
        self.widgets = []
        
    def set_widget(self, widget, state):
        self.widgets.append(widget)
        if state: 
            self.setChecked(state)
        else:
            widget.setEnabled( False )
    
    def toggle(self):
        for widget in self.widgets:
            widget.setEnabled( self.isChecked() )

class StartStopRestartButton(NoFocusButton):
    start   = QtCore.pyqtSignal()
    stop    = QtCore.pyqtSignal()
    restart = QtCore.pyqtSignal()

    def __init__(self, run):
        NoFocusButton.__init__(self, 'Lauf starten', False)
        self.run = run
        self.setCheckable(True)
        self.state = State.WAITING
        
        self.clicked.connect(lambda: self.process_click())

    def new_state(self, state, text, signal):
        self.state = state
        self.setText(text)
        signal.emit()
        
    def process_click(self, manual=None):
        if manual == True  and self.state != State.WAITING: return
        if manual == False and self.state != State.RUNNING: return
        
        if   self.state == State.WAITING: 
            self.new_state(State.RUNNING, 'Lauf beenden', self.start  )
        
        elif self.state == State.RUNNING: 
            s, e = self.run.get_statistics()
            if s == 0 or AskStop(self.run.name(), s,e).exec() == QMessageBox.Ok:
                self.new_state(State.DONE   , 'Lauf zurücksetzen', self.stop)
                self.run.tab_widget().sheet.fill_tree() # force generic_export and thus maybe creation of Finallaeufe
                self.run.tab_widget().setCurrentWidget(self.run)
            else:
                self.setChecked(True)
                
        elif self.state == State.DONE: 
            if AskRestartTab(self.run.name()).exec() == AskRestartTab.Ok:
                self.new_state(State.WAITING, 'Lauf starten', self.restart)
            self.setChecked(False)
                
        else: raise Exception('Unknown state %s' % self.state)
        
class DisplayModeButton(ToolButton):
    valueChanged = pyqtSignal(bool)
    
    def __init__(self):
        self.a, self.b = ":/team_name.png", ":/name_team.png"
        super().__init__(self.a)
        self.state = True
        self.clicked.connect(self.switch_icon)        
        
    def switch_icon(self):
        self.state = not self.state
        self.setIcon(QIcon(self.a if self.state else self.b))
        self.valueChanged.emit(self.state)

    def use(self, toggle, state=True):
        toggle.set_widget(self, state)
        return self

    def disable(self):
        if not self.state: self.switch_icon()
        self.setEnabled(False)
        

class ToolBar(HBoxContainer):

    reset_clicked    = QtCore.pyqtSignal()
    editing_finished = QtCore.pyqtSignal()
    log_msg          = QtCore.pyqtSignal(str)

    def __init__(self, n, lauf, args, parent=None):
        HBoxContainer.__init__(self,parent)
        
        self.run            = self.add( QLineEdit        (              ) )
        _                   = self.add( QLabel           ('Startzeit'   ) )
        self.startzeit      = self.add( QLineEdit        (              ) )
        self.groupedit      = self.add( ToolButton       (":/target.png"), tooltip='Strafrunden eintragen (Ctrl-S)' )
        _                   = self.add( QLabel           ('Schießen'    ) )
        self.schiessen      = self.add( MinMaxSpinbox    ( 1,6,  args.schiessen ), tooltip="Anzahl Schießen" )
        _                   = self.add( QLabel           ('Ziele'       ) )
        self.pfeile         = self.add( MinMaxSpinbox    ( 1,6,  args.pfeile    ), tooltip="Anzahl der Ziele/Pfeile pro Scheiben")
        _                   = self.add( QLabel           ('Starter'     ) )
        self.anzahl         = self.add( MinMaxSpinbox    ( 0, 20, n     ), tooltip="Anzahl Starter*innen")
        self.offset_button  = self.add( ToggleButton     ('Auto'        ), tooltip="automatischer oder manueller Start")
        self.offset         = self.add( IncrementSpinbox ( 5, 0         ), tooltip="alle starten gemeinsam ...\noder einzeln mit festem Abstand"
                                                                        ).use(self.offset_button , True )
        self.staffel_button = self.add( ToggleButton     ('Staffel'     ), tooltip='Staffel-Modus an/aus')
        self.staffel        = self.add( MinMaxSpinbox    ( 2, 6, 3      ), tooltip="Anzahl Starter je Staffel"
                                                                        ).use(self.staffel_button, False)
        self.display_mode   = self.add( DisplayModeButton(              ), tooltip="Bei Staffeln die Anzeige Team<->Starter im linken Fenster umschalten"
                                                                        ).use(self.staffel_button, False)
        
        hbox = self.add(HBoxContainer())
        self.stoppuhr       = hbox.add( Stoppuhr() )
        self.start          = hbox.add( StartStopRestartButton(self.parent()), tooltip="Lauf starten/stoppen/zurücksetzen" )
        self.battery        = hbox.add( QLabel() )
        
        for w in (self.stoppuhr, self.start):
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.start_time = None
        self.start_data = None

        for w in (self.run, self.startzeit):
            w.editingFinished.connect(lambda: self.editing_finished.emit()) 

        for w in (self.schiessen, self.pfeile, self.anzahl, self.offset, self.staffel):
            w.valueChanged.connect(lambda: self.editing_finished.emit())

        self.schiessen.valueChanged.connect(lambda: self.schiessen.setStyleSheet(None))
        self.pfeile   .valueChanged.connect(lambda: self.pfeile   .setStyleSheet(None))
 
        self.start.start  .connect(self.do_start  )
        self.start.stop   .connect(self.do_stop   )
        self.start.restart.connect(self.do_restart)

        self.staffel_button.clicked    .connect(self.staffel_button_clicked)
        self.run           .textChanged.connect(self.maybe_mark_title)
        
        self.startzeit.setPlaceholderText("geplante Startzeit")
        
        if lauf.titel: 
            self.run.setText(lauf.titel)
        else:
            self.run.setPlaceholderText("Titel für %s" % lauf.name)
        
        is_staffel = lauf.team_groesse and lauf.team_groesse > 1 
            
        if lauf.startzeit             : self.startzeit    .setText(re.sub(r'^(\d\d:\d\d):\d\d$',r'\1', lauf.startzeit))
        if lauf.auto_start is not None: self.offset_button.setChecked(lauf.auto_start)
        if lauf.start_offset          : self.offset       .setValue(lauf.start_offset)        
        laufname = f"'{lauf.name}'"
        if not is_staffel and (lauf.anzahl_schiessen and lauf.anzahl_schiessen != self.schiessen.value()):
            print(f"Obwohl -s {self.schiessen.value()} für {laufname:<9} angefordert wurde, wird -s {lauf.anzahl_schiessen} aus der Datenbank verwendet.")
            self.schiessen.setValue(lauf.anzahl_schiessen)
        if not is_staffel and (lauf.anzahl_pfeile and lauf.anzahl_pfeile != self.pfeile.value()):
            print(f"Obwohl -p {self.pfeile.value()} für {laufname:<9} angefordert wurde, wird -p {lauf.anzahl_pfeile} aus der Datenbank verwendet.")
            self.pfeile       .setValue(lauf.anzahl_pfeile)
                
        if lauf.team_groesse:
            self.staffel_button.setChecked( is_staffel )
            self.staffel.setEnabled       ( is_staffel )        
            self.display_mode.setEnabled  ( is_staffel )        
            if lauf.teams:
                self.staffel.setValue(lauf.team_groesse)

    def is_running    (self): return self.start.state == State.RUNNING
    def is_done       (self): return self.start.state == State.DONE
    def shootings     (self): return self.schiessen.value() 
    def staffel_anzahl(self): return self.staffel  .value() if self.staffel_button.isChecked() else 1
    def get_anzahl    (self): return self.anzahl   .value()
    def get_offset    (self): return self.offset   .value() if self.offset_button .isChecked() else 0

    def mark_as_finished(self):
        self.disable()
        self.start.new_state(State.DONE, 'Lauf zurücksetzen', self.start.stop)

    def staffel_button_clicked(self, is_staffel):
        run = self.parent()
        if is_staffel:
            run.lauf.make_staffel(self.staffel.value())
        else:
            run.lauf.make_staffel(None)
        self.highlight_staffel_particulars()

    def highlight_staffel_particulars(self):
        if self.maybe_mark_title():
            css = 'QSpinBox {background-color: rgb(255,215,215); }' # MistyRose1
        else:
            css = None
        self.schiessen.setStyleSheet(css) 
        #self.pfeile   .setStyleSheet(css) 
        
    def maybe_mark_title(self):
        text    = self.run.text().strip()
        staffel = self.staffel_button.isChecked()
        run     = self.parent()
        unique  = text not in list(filter(lambda t: t != "", [ r.toolbar.run.text().strip() for r in run.webola.tabs.runs() if r != run ])) 
        
        text_ok = (text == "" and not staffel) or (text != "" and unique)
        
        if text_ok:
            self.run.setStyleSheet(None)
            return False
        else:
            self.run.setFocus(True)
            self.run.setStyleSheet('QLineEdit {background-color: rgb(255,215,215); }') # MistyRose1
            return True
        
             
    def set(self, tf):
        self.run           .setEnabled(tf)
        self.startzeit     .setEnabled(tf)
        self.schiessen     .setEnabled(tf)
        self.pfeile        .setEnabled(tf)
        self.anzahl        .setEnabled(tf)
        self.offset_button .setEnabled(tf)
        self.staffel_button.setEnabled(tf)
        self.offset        .setEnabled(tf and self.offset_button .isChecked())
        self.staffel       .setEnabled(tf and self.staffel_button.isChecked())

    def disable(self): self.set(False)
    def enable (self): self.set(True )

    def update_gui_state(self, all_runs):
        self.start.setEnabled( State.RUNNING not in [ run.toolbar.start.state for run in all_runs ] )
        
    def do_start(self):
        name    = self.parent().name()
        self.log_msg.emit('Race started: %s' % name)
        self.start_time = time.time()
        self.stoppuhr.start()
        self.disable()        
 
    def do_stop(self):
        self.stoppuhr.done()
        self.run      .setEnabled(True)
        self.schiessen.setEnabled(True)
        self.pfeile   .setEnabled(True)
        self.startzeit.setEnabled(True)
        self.display_mode.disable()
        try:
            # parent not yet present when reading sql files
            self.log_msg.emit('Race stopped: %s' % self.parent().name())
        except:
            pass
 
    def do_restart(self):
        self.enable()
        self.stoppuhr.reset()
        self.reset_clicked.emit()
            
    def run_start_str(self, sep=':'): 
        fmt = '%%H%s%%M' % sep
        return time.strftime(fmt, time.localtime(self.start_time)) if self.start_time else ""
