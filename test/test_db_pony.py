
from PyQt5 import Qt
from pony import orm
import sys
from webola.containers import VBoxContainer, HBoxContainer
from webola.buttons import NoFocusButton

db = orm.Database()
db.bind(provider='sqlite', filename=':memory:')

class Text(db.Entity):
    text = orm.Required(str)

    @staticmethod
    def count():
        return orm.select(orm.count(t) for t in Text).first()

class Gui(Qt.QDialog):
    
    @orm.db_session
    def __init__(self):
        Qt.QDialog.__init__(self)
        
        vbox = VBoxContainer()
        hbox = HBoxContainer()
        
        self.texts = []
        for _ in range(Text.count()):
            w = Qt.QLineEdit()
            vbox.add(w)
            self.texts.append(w)

        hbox.add(NoFocusButton('Laden'    , self.load))
        hbox.add(NoFocusButton('Speichern', self.save))

        self.setLayout(Qt.QVBoxLayout())
        self.layout().addWidget(vbox)
        self.layout().addWidget(hbox)
        
    @orm.db_session
    def save(self):
        assert len(self.texts) == Text.count()
        for idx,t in enumerate(orm.select( t for t in Text )[:]):
            t.text = self.texts[idx].text()
        orm.commit()
        
    @orm.db_session
    def load(self):
        assert len(self.texts) == Text.count()
        for idx,t in enumerate(orm.select( t for t in Text )[:]):
            self.texts[idx].setText(t.text)
    
@orm.db_session
def populate_database():
    #orm.set_sql_debug(True)
    Text(text='abc')
    Text(text='xyz')
    orm.commit()

db.generate_mapping(create_tables=True)
populate_database()

app = Qt.QApplication(sys.argv)
dlg = Gui()
dlg.show()
app.exec_()



#
#