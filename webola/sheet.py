from PyQt5.Qt import Qt, QTreeWidgetItem, QApplication, QMenu, QColor, QTreeWidget, QLabel, QLineEdit,\
    QBrush, QShortcut, QStyledItemDelegate, QPalette, QStyle,\
    QDesktopServices, QUrl
from webola.containers import VBoxContainer, HBoxContainer
from webola.buttons import ToolButton
from pony import orm
from webola import exporter
from webola.dialogs import MedaillenSpiegelDisplay 
from webola.statistik import Medaillenspiegel
from webola.exporter import MockWriter, generic_export_wertung
from pathlib import Path
from webola.latex import path2urkundepdf, TexTableWriter, prepare_to_run_latex, make_backup
import codecs
from webola.utils import have_latex
from webola.runner import ExportThread
from webola.database import Klasse
from pony.orm.core import commit

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
                
        self.label  = self.add( QLabel('Ergebnisliste'))
        self.header = self.add( QLineEdit( webola.wettkampf.name ), stretch=3)
        self.am     = self.add( QLabel('am'))
        self.date   = self.add( QLineEdit( webola.wettkampf.datum), stretch=2)
        self.im     = self.add( QLabel('in'))
        self.ort    = self.add( QLineEdit( webola.wettkampf.ort  ), stretch=1)

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

    def get_header(self):
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

def mix(color, factor=0.6):
    r, g, b = color.red(), color.green(), color.blue()
    mix = lambda f: int(f + (255 - f) * factor)
    return QColor(mix(r), mix(g), mix(b))

class KeepColorDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = option
        if option.state & QStyle.State_Selected:
            color = index.data(Qt.ForegroundRole)
            if color:
                opt.palette.setColor(QPalette.Highlight, mix(color.color()))
        super().paint(painter, opt, index)

class ResultsTree(QTreeWidget):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.setItemDelegate(KeepColorDelegate(self))
        
        self.setDragDropMode(self.InternalMove)
        self.setDropIndicatorShown(True)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.setHeaderLabels(['Name','Verein','', 'Zeit','Abstand','Fehler','Strafen'])
        self.setColumnCount(7)
        BasicItem.set_alignment(self.headerItem())

        QShortcut(Qt.CTRL + Qt.Key_Up  , self, lambda: self.move(Qt.Key_Up  ))
        QShortcut(Qt.CTRL + Qt.Key_Down, self, lambda: self.move(Qt.Key_Down))

    def renumber(self):
        root = self.invisibleRootItem()
        for idx in range(root.childCount()):
            item = root.child(idx)
            item.klasse.sort_idx = idx
        commit()
        
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item and item.parent() is None:
            # allow drag only for toplevel items
            super().startDrag(supportedActions)    
        else:
            return
    
    def dragMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.parent() is None:
            # allow drop only on toplevel items
            super().dragMoveEvent(event)
        else:
            event.ignore()

    def dropEvent(self, event):
        item  = self.currentItem()
        state = item.isExpanded()
        
        super().dropEvent(event) 
        
        if item.parent() is not None:
            # in case of self.dropIndicatorPosition() == QtWidgets.QAbstractItemView.OnItem
            # toplevel items may become children ... move them up again
            parent = item.parent()
            parent.takeChild(parent.indexOfChild(item))
        
            root = self.invisibleRootItem()
            idx  = root.indexOfChild(parent)
            root.insertChild(idx, item)
            
        item.setExpanded(state)
        self.setCurrentItem(item)
        item.setSelected(True)
        self.scrollToItem(item)
        self.renumber()
                
    def swap(self, root, item, idx, offset):
        state = item.isExpanded()
        root.takeChild(idx)
        root.insertChild(idx+offset, item)
        self.setCurrentItem(item)
        self.scrollToItem(item)
        item.setExpanded(state)
        item.setSelected(True)
        self.renumber()
        
    def move(self, key): 
        item = self.currentItem()
        if not isinstance(item, WertungItem): 
            return
            
        root = item.parent() or self.invisibleRootItem()
        idx  = root.indexOfChild(item)
        if key == Qt.Key_Up and idx >=1:
            self.swap(root, item, idx, -1)
        elif key == Qt.Key_Down and idx < root.childCount()-1:
            self.swap(root, item, idx, +1)

    def fill(self):
        # TODO keep expand state
        self.clear()
        self.row2item = dict()
        
        head = self.sheet.controls.header.text()
        
        # no export, but fill the ResultsTree ...
        exporter.generic_export(self.sheet.webola.wettkampf, head, MockWriter(self.write_cell))
        
        self.update_after_resize()
        self.scale_staffel_fonts()
        self.collapseAll()

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
        class ErgebnisMenu(QMenu):
            def __init__(self, tree):
                super().__init__()
                self.tree = tree

            def add_startliste(self):
                self.addAction(f"Startliste erzeugen und anzeigen", lambda: self.tree.generate_starter_list(item.klasse, liste))

            def add_make_vorlauf(self, state):
                if state:
                    self.addAction(f"Diese Wertung als Vorlauf markieren" , lambda: item.vorlauf(True))
                else:
                    self.addAction(f"Diese Wertung als Finallauf markieren", lambda: item.vorlauf(False))
        
            def add_pdf_options(self, latex, pdf): 
                if latex and pdf and pdf.exists():
                    self.addAction(f"Urkunden anzeigen", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf))))
                    if item.klasse.pdf:
                        self.addAction(f"Urkunden wurden noch nicht gedruckt", lambda: item.set_printing_done(None))
                    else:
                        self.addAction(f"Urkunden wurden bereits gedruckt"   , lambda: item.set_printing_done(pdf ))
        
        latex = have_latex() 
        item  = self.itemAt(point)
        if item and isinstance(item, WertungItem):
            menu  = ErgebnisMenu(self)
            liste = path2urkundepdf(self.sheet.xlsx_file(), item.klasse.name, typ='Starterliste')
            if latex and liste:
                menu.add_startliste()
            
            if item.klasse.ist_vorlauf:
                menu.add_make_vorlauf(False)
            else:                
                pdf = path2urkundepdf(self.sheet.xlsx_file(), item.klasse.name, typ='Urkunden')
                menu.add_pdf_options(latex, pdf)
                menu.add_make_vorlauf(True)
            
            if menu.actions():
                menu.exec(self.mapToGlobal(point))

    @with_wait_cursor        
    def generate_starter_list(self, klasse, pdf):
        tex    = pdf.with_suffix('.tex')
        backup = make_backup(tex)
        
        with codecs.open(str(tex), 'w', encoding="utf8") as latex:
            writer = TexTableWriter(latex, show_results=False)
            generic_export_wertung(klasse, writer, number=True)
            writer.finish()
       
        to_do = prepare_to_run_latex(tex, backup,pdf,['PDF'])    
       
        self.sheet.webola.exporter  = ExportThread(to_do)
        self.sheet.webola.exporter.start_work() # run in foreground 
        
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf)))
        
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
            item.setTextAlignment(col, Qt.AlignCenter)
        
class WertungItem(BasicItem):
    def __init__(self, parent, text):
        super().__init__(parent, text)
        self.klasse = Klasse.get(name = text)
        self.indicate_wertung_done()

    def vorlauf(self, status):
        self.klasse.ist_vorlauf = status
        self.indicate_wertung_done()

    def set_printing_done(self, pdf):
        self.klasse.set_printing_done(pdf)
        self.indicate_wertung_done()
        
    def set_bold(self, colour, hint):
        font = self.font(0)
        font.setBold(True)
        self.setFont(0, font)    
        self.setForeground(0, QBrush(QColor(colour)))
        self.setToolTip(0, hint)

    def indicate_wertung_done(self):
        sheet = self.treeWidget().sheet
        pdf   = path2urkundepdf(sheet.xlsx_file(), self.klasse.name)
        
        if running := [ r.lauf for r in self.treeWidget().sheet.webola.tabs.runs() if r.is_running() ]:
            assert len(running) == 1
            running = set(running[0].teams) & self.klasse.teams() 
        
        if not running and self.klasse.is_wertung_done():
            vorlauf  = self.klasse.ist_vorlauf
            have_pdf = pdf and pdf.exists()
            done     = have_pdf and self.klasse.pdf == str(pdf)
            color, hint = ('gray'     , 'Vorlauf'                                 ) if vorlauf      else ( 
                          ('black'    , 'Ergebnisse wurden bereits gedruckt'      ) if done         else ( 
                          ('darkgreen', 'Ergebnisse müssen noch gedruckt werden'  ) if have_pdf     else (
                          ('darkblue' , 'Ergebnisse müssen noch exportiert werden') if have_latex() else (
                          ('darkblue' , 'Wertung ist abgeschlossen')))))
            self.set_bold(color, hint)
        else:
            if self.klasse.ist_vorlauf:
                self.setForeground(0, QBrush(QColor('gray')))
                self.setToolTip(0,'Vorlauf ist noch nicht abgeschlossen')
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
    
    def toprule(self, row, start=1, stop=9):
        pass #create_toprule(sheet, row, start, stop)
        
    def stand(self, row, start=1, stop=9): 
        pass #write_stand   (sheet, row, start, stop)
    

if __name__ == '__main__':
    from pony.orm.core   import db_session
    from webola.database import db, Wettkampf
    import sys, os

    os.chdir('..')
    print(Path().cwd())
    
    db.bind(provider='sqlite', filename='../Startliste_Werder_2026.sql')
    db.generate_mapping()

    with db_session:
        class HeaderStub  (): text   = lambda self: 'Test'
        class ControlsStub(): header = HeaderStub()
        class WebolaStub  (): 
            wettkampf = Wettkampf.get()
        class SheetStub(): 
            controls  = ControlsStub()
            webola    = WebolaStub()
            xlsx_file = lambda self: Path('dummy.xlsx').resolve()

        app = QApplication(sys.argv)
        dlg = ResultsTree(SheetStub())
        dlg.setMinimumSize(800, 600)
        dlg.fill()
        dlg.show()
        app.exec()
    

