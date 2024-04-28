from webola.wertung import Wertung
from pony import orm
from webola.database import Wettkampf, Starter, Team, Lauf

class Ergebnis():
    def __init__(self, verein):
        self.verein   = verein
        self._gold    = 0
        self._silber  = 0
        self._bronze  = 0
        self.position = None 
        self.first    = None
        
    def at(self, pos):
        self.position = pos
        return self

    def gold  (self): self._gold   += 1
    def silber(self): self._silber += 1
    def bronze(self): self._bronze += 1
    
    def __str__(self): 
        return self.tex(' ')

    def tex(self, sep=' & '): 
        pos = f"{self.position:>2}" if self.first and self.position else (
              f"  "                 if self.position                else (
              f"--" ))
        tail = "" if sep == ' ' else r"\\" 
        return sep.join((f"{pos}",f"{self.verein:<26} ~ \\dotfill",f"{self._gold:>2}",f"{self._silber:>2}",f"{self._bronze:>2}"))+tail
    
    def key(self): return self._gold*3+self._silber*2+self._bronze
    
    def __lt__(self, other): 
        return self.key() < other.key() or (
            self.key() == other.key() and self._gold < other._gold) or (
            self.key() == other.key() and self._gold == other._gold and self._silber < other._silber) or (
            self.key() == other.key() and self._gold == other._gold and self._silber == other._silber and self._bronze < other._bronze)


class Medaillenspiegel():
    def __init__(self, wettkampf):
        self.count_starters  (wettkampf)
        self.register_results(wettkampf)
        self.sort()

    def register_results(self, wettkampf):
        for wertung in collect_data(wettkampf):
            pos = 0
            if 'Vorlauf' in wertung.klasse: 
                continue
            for team in Team.sortiere(wertung.teams):
                maybe_staffel = self.with_staffel or not team.ist_staffel()
                if maybe_staffel and team.wertung and team.platz:
                    pos += 1
                    # we checked before that all staffel starters have the same verein
                    starter = list(team.starter)[0] 
                    self.register(starter.verein,pos)
        
    def count_starters(self, wettkampf):
        meldung = set()
        starter = set()
        vereine = set()
        staffel = set()

        for s in Starter.select(lambda s: s.team.lauf.wettkampf == wettkampf):
            meldung.add(s.name  )     # zähle auch Meldungen/Vereine, die nur in Staffeln starten
            vereine.add(s.verein)      
            if s.team.has_finished(): starter.add(s.name)
            if s.team.ist_staffel (): staffel.add(s.team)
        
        self.meldungen    = len(meldung)
        self.starter      = len(starter)
        self.vereine      = len(vereine)
        self.ergebnisse   = { v: Ergebnis(v) for v in vereine }
        self.with_staffel = self.check_can_count(staffel) 

        staffel = ''                                            if self.with_staffel is None else (
                  'Staffel-Ergebnisse werden mitgezählt.'       if self.with_staffel         else ( 
                  'Staffel-Ergebnisse werden nicht mitgezählt.' ))
            
        self.info = 'Gold: 3 Punkte, Silber: 2 Punkte, Bronze: 1 Punkt --- Bei Gleichstand entscheidet erst die Anzahl der Goldmedaillen, dann die Anzahl der Silbermedaillen, dann die Bronzemedaillen. '+staffel
        
    def check_can_count(self, staffel):
        if not staffel:
            return None
        for team in staffel:
            if team.wertung:
                if len(set(s.verein for s in team.starter)) != 1:
                    return False
        return True
        
    def register(self, verein, pos):
        if verein in self.ergebnisse.keys():
            if   pos == 1: self.ergebnisse[verein].gold  ()
            elif pos == 2: self.ergebnisse[verein].silber()
            elif pos == 3: self.ergebnisse[verein].bronze()
        else:
            print(f"Unbekannter Verein {verein}")
    
    def sort(self):
        prev   = None
        pos    = 0 
        offset = 1
        values  = [ v for k,v in self.ergebnisse.items() if k.strip() ] # ignore empty verein
        ergebnisse = sorted(                        # 2. sort by medaillen
            sorted(values, key=lambda e: e.verein), # 1. sort by name
            reverse=True)                                            
        self.ergebnisse = []
        for e in ergebnisse:
            if prev is None or e < prev: 
                pos    += offset
                offset  = 1
                e.first = True
            else:
                offset += 1
            self.ergebnisse.append(e.at(pos))
            prev = e
        
        return self

def valid(string):
    return string and string != "" 

def collect_data(source, empty=True, tag=None):
    process_single_lauf = isinstance(source, Lauf)
    wettkampf = source.wettkampf if process_single_lauf else source 
    if tag is None:
        teams = Team.select(lambda t: t.lauf.wettkampf == wettkampf)
    else:
        teams = Team.select(lambda t: t.lauf.wettkampf == wettkampf and t.lauf.wettkampf_tag == tag)    
    klassen   = dict()
    
    # 1. process *all* teams e.g. in order to get correct labels for Vorlauf/Finallauf
    for t in teams:
        titel = t.lauf.titel
        name  = t.lauf.name
        if t.ist_staffel():
            key = titel if valid(titel) else name
        else:
            klasse = t.single().klasse 
            key = klasse if valid(klasse) else (
                  titel  if valid(titel ) else name )

        if key not in klassen:
            klassen[key] = Wertung(key)
        
        klassen[key].add(t)

    wertungen = []
    for wertung in klassen.values():
        if empty is True or not wertung.is_empty():
            wertungen.extend(wertung.maybe_split())

    # 2. maybe restrict to relevant lauf
    if process_single_lauf:
        # here w.laeufe is guaranteed to contain only a single element
        wertungen = [w for w in wertungen if next(iter(w.laeufe())) == source]

    return sorted(wertungen)
        
        
if __name__ == '__main__':    
    from webola.database import db
        
    #db.bind(provider='sqlite', filename='../DM2022_Briesen/Startliste_09_08.sql')
    #db.bind(provider='sqlite', filename='../demo.sql')
    db.bind(provider='sqlite', filename='../Startliste_DM_2023.sql')
    db.generate_mapping()
        
    with orm.db_session:
        wettkampf = Wettkampf.select()[:][0]
        ms = Medaillenspiegel(wettkampf)
