from webola.database import Lauf, Team, Starter
from pony.orm.core import commit
from webola.dialogs import AskCreateFinallauf, OkCancelDialog
from PyQt5.Qt import QMessageBox, QFormLayout, QLineEdit, QSpinBox, QLabel,\
    QSpacerItem, Qt

class Display(QLineEdit):
    def __init__(self, text):
        super().__init__(text)
        self.setReadOnly(True)
        
class MinMaxSpinBox(QSpinBox):
    def __init__(self, min_value,max_value,default):
        super().__init__()
        self.setMinimum(min_value)
        self.setMaximum(max_value)
        self.setValue  (default  )

    # do not highlight value after pressing +/-
    def stepBy(self, *args, **kwargs):
        QSpinBox.stepBy(self, *args, **kwargs)
        self.lineEdit().deselect()
             
class FinallaufParametersDialog(OkCancelDialog):
    def __init__(self, klasse, num_vorlaeufe):
        super().__init__()
        self.setWindowTitle('Neuer Finallauf')
        self.setMinimumWidth(400)
        self.num_vorlaeufe = num_vorlaeufe
        self.anzahl = MinMaxSpinBox(num_vorlaeufe,20,max(num_vorlaeufe,10))
        self.range  = MinMaxSpinBox(1,3,3)
        self.label  = QLabel()
        self.label.setAlignment(Qt.AlignRight)
        
        form = QFormLayout()        
        form.addRow("Bogenklasse:"         , Display(klasse))
        form.addRow("Anzahl Vorläufe:"     , Display(str(num_vorlaeufe)))
        form.addRow("max. Anzahl Starter:" , self.anzahl)
        form.addRow("sichere Vorlauf-Platzierte:"  , self.range )
        form.addRow(""  , self.label )
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        self.anzahl.valueChanged.connect(self.update_allowed_range)
        self.range .valueChanged.connect(self.update_allowed_range)
        self.update_allowed_range()
        
        self.layout().addLayout(form)
        self.layout().addSpacerItem(QSpacerItem(10,25))
        self.layout().addWidget(self.button_box)

    def update_allowed_range(self):
        a = self.anzahl.value() 
        m = a//self.num_vorlaeufe
        self.range.setMaximum(m)

        p = self.num_vorlaeufe*self.range.value()
        z = self.anzahl.value()-p
        self.label.setText(f"{p} Platzierte und {z} Zeitschnellste")

    def data(self):
        return self.anzahl.value(), self.range.value()

def create_finallauf(wertungen, vorlaeufe, klasse):
    info = sorted( l.name for l in vorlaeufe )
    if AskCreateFinallauf(klasse, info).exec() != QMessageBox.Ok: return
    
    dlg = FinallaufParametersDialog(klasse, len(vorlaeufe))
    if not dlg.exec(): return
    
    MAX_STARTER, MAX_PLATZIERTE = dlg.data()

    pfeile    = { l.anzahl_pfeile    for l in vorlaeufe }
    schiessen = { l.anzahl_schiessen for l in vorlaeufe }
    
    if len(pfeile)    != 1: print(f"[warn] Verschiedene Pfeilanzahlen in den Vorläufen für '{klasse}'!?")
    if len(schiessen) != 1: print(f"[warn] Verschiedene Anzahl Schiessen in den Vorläufen für '{klasse}'!?")
    
    pos = max(l.tab_position for l in vorlaeufe)+1
    finallauf = Lauf.create(f'F: {klasse}', pos, list(vorlaeufe)[0].wettkampf)
        
    finallauf.anzahl_pfeile    = pfeile.pop()
    finallauf.anzahl_schiessen = schiessen.pop()
    finallauf.finallauf        = True
        
    add_teams_by_occupied_place(MAX_PLATZIERTE, wertungen, finallauf)
    fill_up_with_fastest_teams (MAX_PLATZIERTE, wertungen, finallauf, MAX_STARTER)
    commit()

def fill_up_with_fastest_teams (num, wertungen, finallauf, MAX_STARTER):
    fastest = []
    for wertung in wertungen:
        liste = Team.sortiere(t for t in wertung.teams if t.platz)
        if len(liste) > num:
            fastest.extend(liste[num:])
    for idx in range( min(MAX_STARTER-len(finallauf.teams),len(fastest)) ):
        copy_team_to_final(fastest[idx], finallauf)
    

def add_teams_by_occupied_place(num, wertungen, finallauf):
    for idx in range(num):
        for wertung in wertungen:
            liste   = Team.sortiere(t for t in wertung.teams if t.platz)
            if idx < len(liste):
                copy_team_to_final(liste[idx], finallauf)

def copy_team_to_final(source, finallauf):
    nummer = len(finallauf.teams)+1
    target  = Team(nummer=nummer, lauf=finallauf, name = source.name, wertung=source.wertung)
    for starter in source.starter: 
        Starter(name      = starter.name,
                verein    = starter.verein,
                klasse    = starter.klasse,
                team      = target,
                nummer    = starter.nummer,
                strafen   = 0,
                einheit   = starter.einheit )
