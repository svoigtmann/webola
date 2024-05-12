from PyQt5 import Qt
from PyQt5.Qt import QTreeWidgetItem, QApplication
from webola.containers import VBoxContainer, HBoxContainer
from webola.buttons import ToolButton
from pony import orm
from webola import exporter
from webola.dialogs import MedaillenSpiegelDisplay 
from webola.statistik import Medaillenspiegel


class SheetTab(VBoxContainer):

    def __init__(self, webola):
        VBoxContainer.__init__(self)
        
        hbox = HBoxContainer()
        
        self.staffel  = [] # allow empty initialisation before RunTabs are created

        self.label1   = hbox.add( Qt.QLabel('Ergebnisliste'))
        self.header   = hbox.add( Qt.QLineEdit( webola.wettkampf.name ), stretch=3)
        self.label2   = hbox.add( Qt.QLabel('am'))
        self.date     = hbox.add( Qt.QLineEdit( webola.wettkampf.datum), stretch=2)
        self.label3   = hbox.add( Qt.QLabel('in'))
        self.ort      = hbox.add( Qt.QLineEdit( webola.wettkampf.ort  ), stretch=1)

        self.layout().addWidget(hbox)
        self.tree     = self.add( Qt.QTreeWidget() )        
        self.webola   = webola

        self.medaillen = hbox.add( ToolButton(":/result.png", slot=self.medaillenspiegel, tip="Medaillenspiegel anzeigen"))
        self.collapse  = hbox.add( ToolButton(":/minus.png" , slot=self.tree.collapseAll, tip="alle Einträge einklappen"  ))
        self.expand    = hbox.add( ToolButton(":/plus.png"  , slot=self.tree.expandAll  , tip="alle Einträge ausklappen"  ))
                
        self.header.textChanged.connect(self.commit_header)
        self.date  .textChanged.connect(self.commit_date  )
        self.ort   .textChanged.connect(self.commit_ort  )

        hbox.setContentsMargins(0,10,0,0)
        self.tree.setHeaderLabels(['Klasse','Platz','Name','Verein','','Zeit','Abstand','Fehler',''])
        self.set_alignment(self.tree.headerItem())
        
        self.tree.setColumnCount(9)

        self.scale_font()
        
    def get_header(self):
        ort = self.ort.text().strip()
        #return f"{self.header.text()} am {self.date.text()}" + (f" in {ort}" if ort != '' else '')
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
    
    def root_item(self):
        return self.tree.invisibleRootItem()
    
    def fill_tree(self):
        self.tree.clear()
        self.last_parent = self.root_item()
        self.row2item    = dict()
        self.staffel     = list()
        
        head    = self.header.text()
        write   = lambda r, c, t, *args: self.write_cell(r, c, t, *args)
        
        # no export, but fill the QTreeWidget ...
        exporter.generic_export(self.webola.wettkampf, head, write)
        
        self.update_after_resize()
        self.scale_staffel_fonts()
        
        # fill_tree calls generic_export and hence additional Finallaeufe may be created.
        # Thus we may need to add additional tabs, too.
        
        self.webola.tabs.maybe_add_tabs_for_finallaeufe()

    def scale_font(self, fac=None):
        f = self.header.font()
        new = 13 if fac is None else round(f.pointSize() * fac) 
        f.setPointSize(new)
        self.label1.setFont(f)
        self.header.setFont(f)
        self.label2.setFont(f)
        self.date  .setFont(f)
        self.label3.setFont(f)
        self.ort   .setFont(f)
        self.scale_staffel_fonts()                
        self.update_after_resize()

    def scale_staffel_fonts(self):
        for item in self.staffel:
            for idx in range(self.tree.columnCount()):
                f = item.font(idx)
                new = round(QApplication.font().pointSize()*0.7)
                f.setPointSize(new)
                item.setFont(idx,f)

    def update_after_resize(self):
        self.tree.expandAll()
        [ self.tree.resizeColumnToContents(c) for c in range(self.tree.columnCount()) ]

    def write_cell(self, row, col, text, *args):
        assert col>=1
        if row <= 3: return # ignore header
        
        row -= 4
        col -= 1
       
        new_parent = col == 0
        
        if row in self.row2item.keys():
            item = self.row2item[row]
        else:
            parent = self.root_item() if new_parent else self.last_parent            
            if new_parent and self.last_parent != self.root_item():
                QTreeWidgetItem(self.last_parent) # add empty row
            
            item   = QTreeWidgetItem(parent)

            if new_parent:             
                self.last_parent = item
            self.row2item[row] = item

        item.setData(col, Qt.Qt.DisplayRole, text)
        self.set_alignment(item, col)
        
        if col == 4: self.staffel.append(item) # allow to scale fonts later
        
        
    def set_alignment(self, item, col=None):
        column_idx = (1,4,5,6,7)
        if col is None:
            for col in column_idx:
                item.setTextAlignment(col, Qt.Qt.AlignCenter)
        else:
            if col in column_idx:
                item.setTextAlignment(col, Qt.Qt.AlignCenter)                    
    
    def toprule(self, row, start=1, stop=9):
        pass #create_toprule(sheet, row, start, stop)
        
    def stand(self, row, start=1, stop=9): 
        pass #write_stand   (sheet, row, start, stop)
    
