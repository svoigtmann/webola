from PyQt5.Qt import Qt, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLineEdit, QGridLayout, QLabel, \
    QSpinBox, QRegExp, QRegExpValidator, QHBoxLayout, QCompleter, QApplication,\
    QWidget, QTimer, QComboBox, QSizePolicy, QScrollArea, QFrame, QPalette,\
    QIcon
from webola.utils import time2str, str2time
from pony import orm
from webola import database
import sys
from webola.containers import HBoxContainer, VBoxContainer
from webola.database import Starter, Wettkampf, Lauf, Wertung
from pony.orm.core import commit
from webola.buttons import NoFocusButton

def make_scroll_area_from(layout, frame = QFrame.NoFrame):
    h = QFrame()
    gray = QPalette().color(QPalette.Window).name()
    h.setStyleSheet("QFrame { background-color: %s; }" % (gray))
    #layout.setContentsMargins(10,10,10,10)
            
    h.setLayout(layout)
    scrollArea = QScrollArea()
    scrollArea.setFocusPolicy(Qt.NoFocus)
    #scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    #scrollArea.setVerticalScrollBarPolicy  (Qt.ScrollBarAlwaysOn )
    #scrollArea.setBackgroundRole(QPalette.Light)
    scrollArea.setFrameShape(frame)
    scrollArea.setWidgetResizable(True)
    scrollArea.setWidget(h)
    scrollArea.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
    
    return scrollArea


class OkCancelDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)         
        self.button_box.accepted.connect( self.accept )
        self.button_box.rejected.connect( self.reject )
        
        for b in self.button_box.buttons():
            #b.setAutoDefault(False)
            #b.setDefault(False)
            b.setFocusPolicy(Qt.NoFocus)
        
        self.setLayout(QVBoxLayout())

#class EditRunTitle(OkCancelDialog):
#    def __init__(self, string, forbidden):
#        OkCancelDialog.__init__(self)
#        
#        self.forbidden = forbidden
#        self.remove    = False
#        self.title     = QLineEdit(string)
#        self.title.setEnabled(False)
#        
#        self.layout().addWidget(self.title     )
#        self.layout().addWidget(NoFocusButton('Tab löschen', self.remove_tab))
#        self.layout().addSpacing(20)
#        self.layout().addWidget(self.button_box)
#        
#        self.title.textChanged.connect(self.check_name)
#        
#    def check_name(self):
#        title = self.title.text()
#        if title.strip().endswith('*') or title in self.forbidden:
#            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
#        else:
#            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
#        
#    def remove_tab(self):
#        self.remove = True
#        self.accept()
#    
#    def text(self):
#        return self.title.text()

class AskXlsOrSql(QMessageBox):
    def __init__(self, xlsx):
        QMessageBox.__init__(self)
        self.setIcon(QMessageBox.Question)
        self.setWindowIcon(QIcon(":/webola.png"))
        self.setWindowTitle('Neustart oder Fortsetzen ...')
        self.setText("Zu der angeforderten Datei <b>%s</b> gibt es bereits Wettkampf-Daten." % xlsx)
        self.setInformativeText('Wie soll mit diesen Daten umgegangen werden?')
        self.use_xlsx = self.addButton("Wettkampf neu starten", QMessageBox.ActionRole)
        self.use_sql  = self.addButton("Wettkampf fortsetzen" , QMessageBox.ActionRole)
        self.quit     = self.addButton("Webola beenden"       , QMessageBox.RejectRole)
        self.setDefaultButton(self.quit)

class AskYesNo(QMessageBox):
    def __init__(self, title, text, info):
        QMessageBox.__init__(self)
        self.setIcon(QMessageBox.Question)
        self.setWindowIcon(QIcon(":/webola.png"))
        self.setWindowTitle(title)
        self.setText(text)
        self.setInformativeText(info)
        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.setDefaultButton(QMessageBox.Ok)

class AskRemoveStarter(AskYesNo):
    def __init__(self, button):
        if button.ist_staffel():
            key = "Staffel"
            text = button.team.tooltip_summary()
        else:
            key = "Starter"
            name = button.team.get_name()
            info = '' if button.team.info() == '' else '(%s)' % button.team.info()
            text = "%s %s" % (name, info)
        AskYesNo.__init__(self,
                          title = "%s löschen?" % key,
                          text  = text, 
                          info  = "Soll %s Nr. %d wirklich gelöscht werden?" % (key, button.team.nummer))

class AskCreateFinallauf(AskYesNo):
    def __init__(self, klasse, vorlaeufe):
        info = ", ".join(vorlaeufe)
        AskYesNo.__init__(self,
                          title = "Finallauf anlegen?",
                          text  = f"Es gibt für <b>{klasse}</b> Ergebnisse in {len(vorlaeufe)} Vorläufen ({info}).",
                          info  = "Soll ein zugehöriger Finallauf erzeugt werden?")

class AskRestartTab(AskYesNo):
    def __init__(self, name):
        AskYesNo.__init__(self,
                          title = "Rennen neu starten?",
                          text  = "Beim Neustart werden alle Zeiten / Fehler / Platzierungen gelöscht. Eventuell erzeugte Finalläufe werden aber <b>nicht</b> zurückgesetzt und müssen manuell angepasst werden.",
                          info  = "Soll das Rennen '%s' wirklich zurück gesetzt werden?" % name)

class AskModified(AskYesNo):
    def __init__(self, item):
        AskYesNo.__init__(self,
                          title = "Neu starten?",
                          text  = "Die Laufzeit für Nr. %d wurde manuell geändert: %s." % (item.team.nummer, time2str(item.team.zeit()).strip()),
                          info  = "Soll Nr. %d das Rennen wirklich fortsetzen?" % item.team.nummer)

class AskRestart(AskYesNo):
    def __init__(self, item):
        AskYesNo.__init__(self,
                          title = "Neu starten?",
                          text  = "Soll Nr. %d das Rennen wirklich erneut fortsetzen?" % item.team.nummer,
                          info  = "")

class AskStop(AskYesNo):
    def __init__(self, name, s, e):
        msg = "." if s == 0 else (", aber %d fehlen noch!!!" % s)
        AskYesNo.__init__(self,
                          title = "Rennen beenden?",
                          text  = "Es sind %d Läufer im Ziel%s" % (e, msg),
                          info  = "Soll das Rennen '%s' wirklich beendet werden?" % name)

class AskReallyQuit(AskYesNo):
    def __init__(self):
        AskYesNo.__init__(self,
                          title = "Programm beenden",
                          text  = "Soll <b>Webola</b> wirklich beendet werden?",
                          info  = "")
        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.setDefaultButton  (QMessageBox.Ok)

class TimeEdit(QLineEdit):
    def __init__(self, tt, parent=None):
        QLineEdit.__init__(self, parent)
        reg_exp   = QRegExp(r"-?\d?\d?\:\d?\d?\.\d?")
        validator = QRegExpValidator(reg_exp, self)
        self.setValidator(validator)
        self.setTime(tt)
        
    def time   (self    ): return str2time(self.text())
    def setTime(self, tt): 
        self.setText(time2str(tt))
        
class NoHighlightSpinBox(QSpinBox):
    def __init__(self, nn, maximum=None):
        QSpinBox.__init__(self)
        self.setMinimum(-1) # use '-1' to indicate 'not yet set'
        self.setSpecialValueText('--')
        if maximum is not None: self.setMaximum(maximum)
        self.setValue(nn)
        
    def check_modified(self):
        self.was_set = False
        self.valueChanged.connect(self.was_modified)
        
    def was_modified(self):
        if not self.was_set:
            self.was_set = True
            self.setMinimum(0)
            self.setSpecialValueText(None)
        
    # do not highlight value after pressing +/-
    def stepBy(self, *args, **kwargs):
        QSpinBox.stepBy(self, *args, **kwargs)
        self.lineEdit().deselect()

class PenaltySpinBox(NoHighlightSpinBox):
    def __init__(self, value, maximum):
        NoHighlightSpinBox.__init__(self, value, maximum)
        self.setMinimum(0)
        self.setSpecialValueText(None)

class PenaltyNumber(PenaltySpinBox):
    def __init__(self, n, max_anzahl):
        PenaltySpinBox.__init__(self, n, max_anzahl)
        self.setAlignment(Qt.AlignRight)

class PenaltyUnit(PenaltySpinBox):
    def __init__(self, n):
        PenaltySpinBox.__init__(self, n, 180)
        self.setSuffix(' sec')

    def stepBy(self, n):
        return NoHighlightSpinBox.stepBy(self, n*45)
         
class Penalty(HBoxContainer):
    def __init__(self, number, unit, max_anzahl):
        super().__init__() 
        self.number = self.add( PenaltyNumber(number, max_anzahl) )
        self.label  = self.add( QLabel('x')           )
        self.unit   = self.add( PenaltyUnit  (unit  ) )

        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def time(self):
        return self.number.value() * self.unit.value()

class TimeAndSpin(QGridLayout):
    def __init__(self, tt, nn, maximum=None, staffel=False, parent=None):
        QHBoxLayout.__init__(self, parent)
        if tt is None:
            self.time = TimeEdit(0)
            self.time.setEnabled(False)
        else:
            self.time = TimeEdit(tt)
        if nn is None:
            self.spin = NoHighlightSpinBox(-1, maximum=maximum)
        else:
            self.spin = NoHighlightSpinBox(nn, maximum=maximum)

        self.addWidget(self.time, 1, 0, 1, 3)
        self.addWidget(self.spin, 1, 4)
        if not staffel:
            self.addWidget(QLabel('Fehler'), 1, 3)

    def setEnabled(self, tf): 
        self.time.setEnabled(tf)
        self.spin.setEnabled(tf)
         
    def text (self): 
        return self.time.text()
    
    def value(self, lower=None): 
        v = self.spin.value()
        return v if lower is None else max(lower, v)
    
class Data():
    def __init__(self, wettkampf):
        self.namen, self.vereine, self.klassen = set(), set(), set()
        self.name2verein, self.name2klasse     = dict(), dict()
      
        orm.commit()
          
        for s in orm.select( s for s in database.Starter if s.team.lauf.wettkampf == wettkampf ):
        
            if s.verein is not None: self.vereine.add(s.verein)
            if s.klasse is not None: self.klassen.add(s.klasse)
            if s.name   is not None: 
                self.namen.add(s.name)
                self.register(s.name, s.verein, self.name2verein)
                self.register(s.name, s.klasse, self.name2klasse)

    def register(self, name, info, container):
        if info is None: return
        if name in container:
            container[name].add(info)
        else:
            container[name] = { info }
    
    def verein(self, name):
        if name in self.name2verein:
            return ", ".join(self.name2verein[name]), len(self.name2verein[name])

    def klasse(self, name):
        if name in self.name2klasse:
            return ", ".join(self.name2klasse[name]), len(self.name2klasse[name])

def make_edit(text, hint):
    edit = QLineEdit()
    if text:
        edit.setText(text)
    else:
        edit.setPlaceholderText(hint)
    return edit

class StarterColumn():
    def __init__(self, starter, data, team):
        lauf       = starter.team.lauf
        max_fehler = lauf.anzahl_schiessen * lauf.anzahl_pfeile
        
        self.name        = self.make_edit(starter.name  , starter.get_name(), data.namen  )
        self.klasse      = self.make_edit(starter.klasse, 'Bogenklasse'     , data.klassen)
        self.verein      = self.make_edit(starter.verein, 'Verein'          , data.vereine)
        self.penalty     = Penalty(number     = starter.strafen, 
                                   unit       = starter.einheit, 
                                   max_anzahl = lauf.wettkampf.disqualifikation or None) # 0 also means None
        self.zeit_fehler = TimeAndSpin(starter.laufzeit, starter.fehler, max_fehler, team.ist_staffel())

        self.zeit_fehler.spin.valueChanged.connect(self.penalty.number.setMaximum)

        self.name.completer().activated.connect(lambda name: self.complete(name, data))

        if starter.laufzeit is None or starter.laufzeit <= 0:
            self.zeit_fehler.spin.setEnabled(False)
            self.penalty.setEnabled(False)

        if not starter.team.has_finished():
            self.zeit_fehler.time.setEnabled(False)

    def make_edit(self, text, hint, data):
        edit      = make_edit(text, hint)
        completer = QCompleter(sorted(data), edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        edit.setCompleter(completer)
        return edit

    def complete(self, name, data):
        if self.verein.text() == '':
            verein, n = data.verein(name) 
            if n == 1:
                self.verein.setText(verein)
            elif n >= 2:
                self.verein.setPlaceholderText(verein)
        
        if self.klasse.text() == '':
            klasse, n = data.klasse(name) 
            if n == 1:
                self.klasse.setText(klasse)
                self.penalty.unit.setValue( Starter.compute_einheit(klasse) )
            elif n >= 2:
                self.klasse.setPlaceholderText(klasse)


class WertungCombo(QComboBox):
    def __init__(self, wertung):
        super().__init__()
        self.setFocusPolicy(Qt.NoFocus)
        for known in sorted(Wertung.select(), key=lambda w: w.id):
            self.addItem(known.name, known)
        
        self.setCurrentText(wertung.name)
    
    def value(self):
        return self.currentIndex() == 0
        
class TeamTable(QGridLayout):
    def __init__(self, team):
        QGridLayout.__init__(self)
        self.column = []
        
        nummer = QLineEdit(str(team.nummer))
        nummer.setEnabled(False)
        colspan = 1 if team.ist_staffel() else 2
        self.addWidget(nummer, 0, 1, 1, colspan)
       
        self.wertung = WertungCombo(team.wertung)
        
        if team.ist_staffel():
            self.add_staffel_details(team)
            start_row = 2 
        else:
            start_row = 1
            
        self.addWidget(QLabel('Nummer'), 0, 0)

        for row, label in enumerate(('Name', 'Verein', 'Klasse', 'Strafe', 'Laufzeit'), start_row):
            self.addWidget(QLabel(label), row, 0)

        data = Data(team.lauf.wettkampf)

        for s in team.liste():
            column = self.add(s, data, team, start_row, colspan)
            if team.ist_staffel():
                column.zeit_fehler.time .textChanged.connect(lambda: self.zeit_fehler.time.setTime (self.zeit  ()))
                column.zeit_fehler.spin.valueChanged.connect(lambda: self.zeit_fehler.spin.setValue(self.fehler()))
                column.penalty.number  .valueChanged.connect(lambda: self.zeit_fehler.time.setTime (self.zeit  ()))
                column.penalty.unit    .valueChanged.connect(lambda: self.zeit_fehler.time.setTime (self.zeit  ()))
        
    def zeit  (self): return sum( c.zeit_fehler.time.time()+c.penalty.time() for c in self.column )
    def fehler(self): return sum( c.zeit_fehler.value(lower=0)               for c in self.column )
            
    def add_staffel_details(self, team):
        self.name = make_edit(team.name, team.get_name())
        self.addWidget(self.name   , 0, 2)
        self.addWidget(self.wertung, 1, 1)
        
        max_fehler       = team.lauf.anzahl_schiessen * team.lauf.anzahl_pfeile * team.anzahl()
        self.zeit_fehler = TimeAndSpin(team.zeit(), team.fehler(), max_fehler, staffel=True)
        self.zeit_fehler.setEnabled(False)
        self.addLayout(self.zeit_fehler, 1, 2)
        
    def add(self, starter, data, team, start_row, colspan):
        sc = StarterColumn(starter, data, team)
        self.column.append(sc)
        sc.zeit_fehler.spin.check_modified()
        for row, widget in enumerate((sc.name, sc.verein, sc.klasse, sc.penalty, sc.zeit_fehler), start_row):
            if isinstance(widget, QWidget):
                if widget == sc.penalty:
                    self.addWidget(widget      , row, starter.nummer  )
                    if not team.ist_staffel():
                        self.addWidget(self.wertung, row, starter.nummer+1)

                else:
                    self.addWidget(widget, row, starter.nummer, 1, colspan)
            else:
                self.addLayout(widget, row, starter.nummer, 1, colspan)
        return sc
            
class Edit(OkCancelDialog):

    def __init__(self, team):
        OkCancelDialog.__init__(self)
        
        self.team  = team
        self.table = TeamTable(team)
        
        self.layout().addLayout(self.table)
        self.layout().addWidget(self.button_box)
        
        # store initial times for later comparison
        self.initial = [ s.laufzeit or 0.0 for s in team.liste() ]
                                            
        #self.adjustSize() # does not work for single starter!?
#        QTimer.singleShot(0, lambda: self.set_column_width(team))
        QTimer.singleShot(0, lambda: self.table.column[0].zeit_fehler.spin.setFocus(True))
        
#    def set_column_width(self, team):
#        pass
#        #width   = self.table.column[0].name.width()        
#        #columns = max( len(team.starter), 3 if team.ist_staffel() else 1 )
#        #for col in range(1,columns+1):
#        #    self.table.setColumnMinimumWidth(col, width)

    def maybe_update(self, old, new):
        text = new.text()
        if old is None and text == "": text = None
        return text if text != old else old
        
    def show_update(self):
        modified = False
        for db, gui, time in zip(self.team.liste(), self.table.column, self.initial):
            db.name    = self.maybe_update( db.name  , gui.name   ) 
            db.klasse  = self.maybe_update( db.klasse, gui.klasse )
            db.verein  = self.maybe_update( db.verein, gui.verein )
            
            fehler = gui.zeit_fehler.spin.value()
            if db.fehler is None and fehler == -1: fehler = None
            if fehler is not None and fehler != db.fehler:
                db.fehler = fehler

            if gui.zeit_fehler.time.time() != time: 
                db.laufzeit = gui.zeit_fehler.time.time()
                modified = True
                
            strafen = gui.penalty.number.value()
            if strafen != db.strafen:
                db.strafen = strafen

            einheit = gui.penalty.unit.value()
            if einheit != db.einheit:
                db.einheit = einheit
            
        if self.team.ist_staffel() and self.table.name.text() != self.team.get_name(): 
            self.team.name = self.table.name.text()
        
        self.team.wertung = self.table.wertung.currentData()
            
        orm.commit()
        
        return modified


class GroupEdit(OkCancelDialog):

    def __init__(self, lauf):
        OkCancelDialog.__init__(self)
        
        self.setWindowTitle('Strafrunden eintragen')
        self.setMinimumWidth(450)
                
        grid = QGridLayout()
        grid.setAlignment(Qt.AlignTop)
        grid.setColumnStretch(1,1)
        grid.setColumnStretch(2,0)
        grid.addWidget(self.header('Name')  , 0, 1)
        grid.addWidget(self.header('Fehler'), 0, 2)

        max_fehler = lauf.anzahl_schiessen * lauf.anzahl_pfeile
        self.starters = []
        self.spins    = []
        
        for team in sorted(lauf.teams, key=lambda t: t.nummer):
            nummer = QLabel(f'[{team.lauf.name} Nr. {team.nummer}]')
            nummer.setAlignment(Qt.AlignCenter)
            grid.addWidget(nummer, len(self.starters)+1, 0)
            for starter in sorted(team.starter, key=lambda s: s.nummer):
                self.starters.append(starter)
                name = QLineEdit(starter.name)
                name.setCursorPosition(0)
                name.setReadOnly(True)
                name.setFocusPolicy(Qt.NoFocus)
                name.setToolTip(f'{starter.verein}, {starter.klasse}')
                
                fehler = -1 if starter.fehler is None else starter.fehler
                self.spins.append(NoHighlightSpinBox(fehler, maximum=max_fehler))
                
                row = len(self.starters)
                grid.addWidget(name          , row, 1)
                grid.addWidget(self.spins[-1], row, 2)            
            
        self.layout().addWidget(make_scroll_area_from(grid))
        self.layout().addWidget(self.button_box)

    def header(self, text):
        label = QLabel(f'<b>{text}</b>')
        label.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        return label

    def ok_pressed(self):
        for starter, spin in zip(self.starters, self.spins):
            fehler = spin.value()
            if starter.fehler is None and fehler == -1: fehler = None
            if fehler is not None and fehler != starter.fehler:
                starter.fehler = fehler

        commit()

class Headline(QLabel):
    def __init__(self, txt, pt=12, w=None, bold=True):
        super().__init__(f"<b>{txt}</b>" if bold else txt)

        f = self.font()
        f.setPointSize(pt)
        self.setFont(f)
        
        if w: 
            self.setMinimumWidth(w)
            self.setAlignment(Qt.AlignCenter)

class CLabel(QLabel):
    def __init__(self, txt):
        super().__init__(txt)
        self.setAlignment(Qt.AlignCenter)

class TinyWrappedLabel(CLabel):
    def __init__(self, text):
        super().__init__(text)
        f = self.font()
        f.setPointSize(8)
        self.setFont(f)
        self.setWordWrap(True)

class MedaillenSpiegelDisplay(QDialog):
    def __init__(self, ms):
        super().__init__()
        self.setWindowTitle('Statistik')
        #self.setMaximumHeight(500)
        self.setMinimumWidth(750)
        
        vbox = VBoxContainer()
        vbox.add(Headline('Medaillenspiegel',pt=20, bold=False))
        vbox.add(QLabel(f"{ms.starter} Starter:innen bei {ms.meldungen} Meldungen aus {ms.vereine} Vereinen"))
        
        vbox.add(make_scroll_area_from(self.generate_table(ms), frame=QFrame.StyledPanel))

        vbox.add(TinyWrappedLabel(ms.info))
        vbox.add(NoFocusButton('OK', self.accept))
            
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(vbox)
        
    def generate_table(self, ms):
        grid = QGridLayout()
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing  (0)
        
        grid.addWidget(Headline('Verein')     , 1, 1)
        grid.addWidget(Headline('Gold'  ,w=70), 1, 2)
        grid.addWidget(Headline('Silber',w=70), 1, 3)
        grid.addWidget(Headline('Bronze',w=70), 1, 4)

        for row,v in enumerate(ms.ergebnisse,2):
            grid.addWidget(CLabel(str(v.position) if v.first else ""), row, 0)
            grid.addWidget(QLabel(    v.verein  ), row,1)
            grid.addWidget(CLabel(str(v._gold  )), row,2)
            grid.addWidget(CLabel(str(v._silber)), row,3)
            grid.addWidget(CLabel(str(v._bronze)), row,4)
            bgcolor = '' if row % 2 else 'background-color: white;'
            for col in range(5):
                grid.itemAtPosition(row,col).widget().setStyleSheet(f'{bgcolor} padding: 2px;')
            
        return grid


if __name__ == '__main__':    
    from webola.database import db
    
    app = QApplication(sys.argv)
    
    db.bind(provider='sqlite', filename='../2022DM/Startliste_08_01.sql')
    db.generate_mapping()
        
    with orm.db_session:
        wettkampf = Wettkampf.get()
        lauf = Lauf.get(name='Lauf 12')

        dlg = GroupEdit(lauf)
        if dlg.exec():
            dlg.ok_pressed() 
        
            
#    database.db.bind(provider='sqlite', filename=':memory:')
#    database.db.generate_mapping(create_tables=True)
#        
#    with orm.db_session:
#        wettkampf = database.Wettkampf.create('Test')
#        lauf      = database.Lauf(name='Werder', wettkampf=wettkampf, anzahl_schiessen=3, anzahl_pfeile=3, 
#                                  auto_start=True, start_offset=0, team_groesse=1,finallauf=False)
#        team      = database.Team(nummer = 3, lauf = lauf, name = "Werder", wertung=1)
#        database.Starter(name='AA', verein='WB', klasse='H Stand', team=team, nummer=1, laufzeit=72, strafen=2, einheit=None)
#        database.Starter(name='AB', verein='WB', klasse='D Stand', team=team, nummer=2, laufzeit=56)
#        database.Starter(team=team, nummer=3)
#        
#        app = QApplication(sys.argv) #@UnusedVariable
#        #dlg = EditItem(wettkampf, button, True)
#        dlg = Edit(team)
#        if dlg.exec() == QDialog.Accepted:
#            dlg.show_update()
#
