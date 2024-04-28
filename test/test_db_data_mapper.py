
from PyQt5 import Qt, QtSql
import sys
from webola.containers import VBoxContainer

db = QtSql.QSqlDatabase.addDatabase("QSQLITE")
db.setDatabaseName("test.sql")
if not db.open():
    print("Error opening DB")
    sys.exit(1)

class TextEntry(Qt.QLineEdit):
    def __init__(self, model, idx):
        Qt.QLineEdit.__init__(self)
        
        mapper = Qt.QDataWidgetMapper(self)
        mapper.setSubmitPolicy(Qt.QDataWidgetMapper.AutoSubmit)
        mapper.setModel(model)
        mapper.addMapping(self, 1)
        mapper.setCurrentIndex(idx)

        self.editingFinished.connect(mapper.submit)

class Gui(Qt.QDialog):
    
    def __init__(self):
        Qt.QDialog.__init__(self)
             
        self.model = QtSql.QSqlTableModel(self)
        self.model.setTable("text")
        self.model.select()

        vbox = VBoxContainer()
        self.t1 = vbox.add( TextEntry(self.model, 0) )
        self.t2 = vbox.add( TextEntry(self.model, 1) )

        self.setLayout(Qt.QVBoxLayout())
        self.layout().addWidget(vbox)   

app = Qt.QApplication(sys.argv)
dlg = Gui()
dlg.show()
app.exec_()



#
#