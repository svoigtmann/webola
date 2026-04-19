from PyQt5 import Qt
from PyQt5.Qt import QTreeWidgetItem, QApplication, QMenu, QColor, QBrush,\
    QTreeWidget
from webola.containers import VBoxContainer, HBoxContainer
from webola.buttons import ToolButton
from pony import orm
from webola import exporter
from webola.dialogs import MedaillenSpiegelDisplay 
from webola.statistik import Medaillenspiegel, collect_data
from webola.exporter import MockWriter, generic_export_wertung
from pathlib import Path
from webola.latex import path2urkundepdf, TexTableWriter, prepare_to_run_latex, make_backup
import subprocess
import codecs
from webola.utils import have_latex
from webola.runner import ExportThread
from webola.database import UrkundenFertig

def with_wait_cursor(func):
    def inner(*args, **kwargs):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        res = func(*args, **kwargs)
        QApplication.restoreOverrideCursor()
        return res
    return inner

class Controls(HBoxContainer):
    def __init__(self, webola):
        super().__init__()
        self.setContentsMargins(0,10,0,0)

        self.webola = webola
                
        self.label  = self.add( Qt.QLabel('Ergebnisliste'))
        self.header = self.add( Qt.QLineEdit( webola.wettkampf.name ), stretch=3)
        self.am     = self.add( Qt.QLabel('am'))
        self.date   = self.add( Qt.QLineEdit( webola.wettkampf.datum), stretch=2)
        self.im     = self.add( Qt.QLabel('in'))
        self.ort    = self.add( Qt.QLineEdit( webola.wettkampf.ort  ), stretch=1)

        self.medaillen = self.add( ToolButton(":/result.png", tip="Medaillenspiegel anzeigen"))
        self.collapse  = self.add( ToolButton(":/minus.png" , tip="alle Einträge einklappen"  ))
        self.expand    = self.add( ToolButton(":/plus.png"  , tip="alle Einträge ausklappen"  ))
                
        self.header.textChanged.connect(self.commit_header)
        self.date  .textChanged.connect(self.commit_date  )
        self.ort   .textChanged.connect(self.commit_ort  )

        self.medaillen.clicked.connect(self.medaillenspiegel)

    def scale_font(self, fac):
        f   = self.header.font()
        new = 13 if fac is None else round(f.pointSize() * fac) 
        f.setPointSize(new)
        self.label .setFont(f)
        self.header.setFont(f)
        self.am    .setFont(f)
        self.date  .setFont(f)
        self.im    .setFont(f)
        self.ort   .setFont(f)

    def header(self):
        ort = self.ort.text().strip()
        return f"{self.header.text()}" + (f" in {ort}" if ort != '' else '')

    def medaillenspiegel(self):
        dlg = MedaillenSpiegelDisplay( Medaillenspiegel(self.webola.wettkampf) )
        dlg.exec()

    def commit_header(self):
        self.webola.wettkampf.name = self.header.text()
        orm.commit()

    def commit_date(self):
        if self.date.text():
            self.webola.wettkampf.datum = self.date.text()
            orm.commit()

    def commit_ort(self):
        self.webola.wettkampf.ort = self.ort.text()
        orm.commit()

class ResultsTree(QTreeWidget):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet
        self.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.setHeaderLabels(['Name','Verein','', 'Zeit','Abstand','Fehler','Strafen'])
        self.setColumnCount(7)
        BasicItem.set_alignment(self.headerItem())

    def fill(self):
        # TODO keep expand state
        self.clear()
        self.last_parent = self.invisibleRootItem()
        self.row2item    = dict()
        
        head = self.sheet.controls.header.text()
        
        # no export, but fill the ResultsTree ...
        exporter.generic_export(self.sheet.webola.wettkampf, head, MockWriter(self.write_cell))
        
        self.update_after_resize()
        self.scale_staffel_fonts()
        
        # fill_tree calls generic_export and hence additional Finallaeufe may be created.
        # Thus we may need to add additional tabs, too.
        self.sheet.webola.tabs.maybe_add_tabs_for_finallaeufe()


    def scale_staffel_fonts(self):
        for item in self.walk(staffel=True):
            for idx in range(self.columnCount()):
                f = item.font(idx)
                new = round(QApplication.font().pointSize()*0.8)
                f.setPointSize(new)
                item.setFont(idx,f)

    def walk(self, staffel=None):
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            wertung = root.child(i)
            if not staffel: yield wertung
            
            for j in range(wertung.childCount()):
                ergebnis = wertung.child(j)
                if not staffel: yield ergebnis
                
                for k in range(ergebnis.childCount()):
                    staffel = ergebnis.child(k)
                    if staffel or staffel is None: yield staffel

    def update_after_resize(self):
        self.expandAll()
        for item in self.walk(staffel=True):
            item.parent().parent().setExpanded(False)
        
        for c in range(self.columnCount()):
            self.resizeColumnToContents(c)

        width = self.columnWidth(1)

        self.expandAll()
        for c in range(self.columnCount()):
            self.resizeColumnToContents(c)

        self.setColumnWidth(1, width)



    def context_menu(self, point):
        if not have_latex(): return 
        
        if item := self.itemAt(point):
            if klasse := item.text(0):
                menu = QMenu()
                if liste := path2urkundepdf(self.sheet.xlsx_file(), klasse, typ='Starterliste'):
                    menu.addAction(f"{liste.name} anzeigen", lambda: self.sheet.generate_starter_list(klasse, liste))
                
                if pdf := path2urkundepdf(self.sheet.xlsx_file(), klasse, typ='Urkunden'):
                    if pdf.exists():
                        menu.addAction(f"{pdf.name} anzeigen", lambda: self.sheet.run_okular(pdf))
                        if self.sheet.urkunden_already_printed(item):
                            menu.addAction(f"Setze Status: Urkunden für {klasse} noch nicht gedruckt"    , lambda: self.sheet.mark_urkunden_done(item, klasse, False))
                        else:
                            menu.addAction(f"Setze Status: Urkunden für {klasse} wurden bereits gedruckt", lambda: self.sheet.mark_urkunden_done(item, klasse, True))
                
                if menu.actions():
                    menu.exec(self.mapToGlobal(point))

    def write_cell(self, row, col, text, *args):
        assert col>=1
        
        if row <= 3: 
            return # ignore header
        
        elif row in self.row2item.keys():
            item = self.row2item[row]
            item.setText(col, str(text))
            if col == 5:
                self.new_staffel_detailed_result(row, item)
        else:
            if col == 1:
                self.last_parent   = WertungItem(self.invisibleRootItem(), text)
            else:
                self.row2item[row] = ErgebnisItem(self.last_parent, text)

    def new_staffel_detailed_result(self, row, item):
        assert isinstance(item, ErgebnisItem)
        prev = self.row2item[row-1]
        if isinstance(prev, StaffelDetailItem): prev = prev.parent()
        self.row2item[row] = StaffelDetailItem(prev, item) 
        item.parent().takeChild(item.parent().indexOfChild(item))        

class BasicItem(QTreeWidgetItem):
    def __init__(self, parent, text):
        super().__init__(parent)
        BasicItem.set_alignment(self)
        self.setText(0, text)

    @staticmethod
    def set_alignment(item):
        column_idx = (3,4,5)
        for col in column_idx:
            item.setTextAlignment(col, Qt.Qt.AlignCenter)
    
class WertungItem(BasicItem):
    def __init__(self, parent, text):
        super().__init__(parent, text)
        # TODO use correct tooltip
        self.indicate_wertung_done(text)

    def indicate_wertung_done(self, klasse):
        sheet = self.treeWidget().sheet
        pdf   = path2urkundepdf(sheet.xlsx_file(), klasse)
        if pdf and pdf.exists():
            font = self.font(0)
            font.setBold(True)
            self.setFont(0, font)
            
            if UrkundenFertig.get(wertung=klasse, wettkampf=sheet.webola.wettkampf):
                color = 'black'     # Wertung.is_done() ... and was printed 
                self.setToolTip(0,'Ergebnisse wurden bereits gedruckt')
            else:
                color = 'darkgreen' # Wertung.is_done() ... but needs printing
                self.setToolTip(0,'Ergebnisse müssen noch gedruckt werden')
                
            self.setForeground(0, QBrush(QColor(color)))
        elif pdf:
            self.setToolTip(0,'Wertung ist abgeschlossen')
        else:
            self.setToolTip(0,'Wertung ist noch nicht abgeschlossen')

class ErgebnisItem(BasicItem):
    def __init__(self, parent, text):
        super().__init__(parent, text)

    def setText(self, col, text):
        if   col == 0: super().setText(0, text)
        elif col == 1: raise NotImplementedError(f"col=1: {text}")            
        elif col == 2: raise NotImplementedError(f"col=2: {text}")            
        elif col == 3: super().setText(0, f"{self.text(0)} {text}")
        else:
            super().setText(col-3, text)

class StaffelDetailItem(ErgebnisItem):
    def __init__(self, parent, other):
        super().__init__(parent, '')
        self.setText(0, other.text(0))
        for col in range(1,5):
            QTreeWidgetItem.setText(self, col, other.text(col))

    def setText(self, col, text):
        if col == 0:
            letter = chr(64 + self.parent().childCount())
            super().setText(0, f"{letter} {text}")
        
class SheetTab(VBoxContainer):

    def __init__(self, webola):
        VBoxContainer.__init__(self)
        
        self.controls = self.add( Controls (webola) )
        self.tree     = self.add( ResultsTree(self) )
        self.webola   = webola

        self.controls.collapse.clicked.connect(self.tree.collapseAll)
        self.controls.expand  .clicked.connect(self.tree.expandAll  )
                
        self.scale_font()
            
    def scale_font(self, fac=None):
        self.controls.scale_font(fac)
        self.tree.scale_staffel_fonts()                
        self.tree.update_after_resize()
        
    def xlsx_file(self):
        if name := self.webola.control.xlsx.file(dialog=False):
            return Path(name)
        else:
            return None

    def urkunden_already_printed(self, item):
        return item.foreground(0).color() == QColor('black')

    @with_wait_cursor        
    def generate_starter_list(self, klasse, pdf):
        wertungen = collect_data(self.webola.wettkampf, only=klasse)
        wertung = [ w for w in wertungen if w.klasse == klasse]
        if len(wertung) != 1:
            print(f'[warn] Found {", ".join(w.klasse for w in wertung)}')
            return
        
        tex = pdf.with_suffix('.tex')
        backup = make_backup(tex)
        
        with codecs.open(str(tex), 'w', encoding="utf8") as latex:
            writer = TexTableWriter(latex, show_results=False)
            generic_export_wertung(wertung[0], writer, number=True)
            writer.finish()
       
        to_do = prepare_to_run_latex(tex, backup,pdf,['PDF'])    
       
        self.webola.exporter  = ExportThread(to_do)
        self.webola.exporter.start_work() # run in foreground 
        self.run_okular(pdf)

    def mark_urkunden_done(self, item, klasse, done):
        fertig = UrkundenFertig.get(wertung=klasse, wettkampf=self.webola.wettkampf)

        if done:
            if not fertig: UrkundenFertig(wertung=klasse, wettkampf=self.webola.wettkampf)
        else:
            if     fertig: fertig.delete()
            
        item.indicate_wertung_done(klasse)
        orm.commit()
                
    def run_okular(self, pdf):
        try:
            subprocess.Popen(["okular", str(pdf)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except:
            print("Error starting Okular on '{pdf}'.")
    
    def toprule(self, row, start=1, stop=9):
        pass #create_toprule(sheet, row, start, stop)
        
    def stand(self, row, start=1, stop=9): 
        pass #write_stand   (sheet, row, start, stop)
    
