import time
import re

from webola.utils import time2str
from pony.orm.core import Database, Required, Optional, Set, delete, unicode, db_session

db = Database()

class Lauf(db.Entity):
    wettkampf_tag    = Required(int, min=1)
    tab_position     = Required(int, min=0)
    name             = Required(str)
    wettkampf        = Required('Wettkampf')
    titel            = Optional(str)
    startzeit        = Optional(str)
    anzahl_schiessen = Optional(int, min=1, max= 6)
    anzahl_pfeile    = Optional(int, min=1, max= 6)
    auto_start       = Optional(bool)
    start_offset     = Optional(int, min=0)
    team_groesse     = Optional(int, min=0, max= 4)
    teams            = Set("Team")
    finallauf        = Required(bool)

    @staticmethod
    def create(name, pos, wettkampf):
        return Lauf(wettkampf_tag=1, tab_position=pos, name=name, wettkampf=wettkampf, anzahl_schiessen=3, anzahl_pfeile=4, auto_start=True, start_offset=0, team_groesse=1, finallauf=False)

    def update_name_for_wettkampf_tag(self):
        self.cleanup_name_from_wettkampf_tag()
        self.name = self.name+f"'{self.wettkampf_tag}" 

    def cleanup_name_from_wettkampf_tag(self):
        self.name = self.name.removesuffix("'1").removesuffix("'2")

    def make_staffel(self, anzahl):
        self.team_groesse = anzahl
            
    def has_finished(self):
        return any(t.platz for t in self.teams)
        
    def ist_staffel(self):
        return any(t.ist_staffel() for t in self.teams)
        
    def klasse(self):
        if not self.finallauf: return None
        klassen = { t.single().klasse for t in self.teams }
        assert len(klassen) == 1
        return klassen.pop()
        
    def vorlaeufe(self):
        if not self.finallauf: return None
        
        vorlaeufe = set()
        klasse    = self.klasse()
        
        for lauf in self.wettkampf.laeufe:
            if lauf.finallauf or lauf.ist_staffel(): 
                continue
            klassen = { t.single().klasse for t in lauf.teams }
            if klasse in klassen:
                vorlaeufe.add(lauf) 
    
        return vorlaeufe

class Wettkampf(db.Entity):
    name             = Optional(str)
    datum            = Required(str)
    ort              = Optional(str)
    disqualifikation = Optional(int)
    vorlaeufe        = Optional(bool)
    laeufe           = Set('Lauf')
    
    @staticmethod
    def create(name=None):
        if name is None:
            year = time.strftime('%Y', time.gmtime())
            name = '%d. Werderaner Bogenlauf' % (int(year)-2013)
        datum = time.strftime('%d. %B %Y', time.gmtime()).lstrip('0')
        return Wettkampf(name=name, datum=datum)

    def has_day_markers(self):
        return any(l.wettkampf_tag == 2 for l in self.laeufe)

class Wertung(db.Entity):
    name     = Required(unicode, unique=True)
    kurzname = Required(unicode, unique=True)
    teams    = Set('Team')
    
    @staticmethod
    def create():
        Wertung(name = 'Wettkampf'       , kurzname='default' )
        Wertung(name = 'außer Konkurrenz', kurzname='unranked')
        Wertung(name = 'Did Not Start'   , kurzname='DNS'     )
        
class Team(db.Entity):
    nummer    = Required(int, min=1)#, max=20)
    platz     = Optional(int, min=1, max=20)
    lauf      = Required(Lauf)
    name      = Optional(str)
    klasse    = Optional('Klasse')
    starter   = Set("Starter") 
    schiessen = Optional(int, min=0)
    schiessen_time = Optional(float)
    running   = Optional(int)
    wertung   = Required(Wertung)
    
    def key_nummer  (self): return self.nummer % 100
    def zeit        (self): return sum( s.zeit()   for s in self.starter if s.zeit()   is not None )
    def laufzeit    (self): return sum( s.laufzeit for s in self.starter if s.laufzeit is not None )
    def anzahl      (self): return len(self.starter)
    def ist_staffel (self): return self.anzahl() > 1
    def has_finished(self): return self.platz is not None  
    def schuss_str  (self): return "" if self.schiessen is None else self.schiessen * "."
    def data_missing(self): return any(s.data_missing() for s in self.starter) 
    def liste       (self): return list(sorted(self.starter, key=lambda s: s.nummer))
    def platz_str   (self): 
        if   self.is_dsq():
            return ("-%2d-" % self.platz) if self.has_finished() else "-"
        elif self.has_finished():
            return "(%2d)" % self.platz if  self.is_ranked() else "/%2d/" % self.platz
        else:
            return " "                  if  self.is_ranked() else "/"
              
    def fehler      (self): 
        liste = [ s.fehler for s in self.starter if s.fehler is not None ]
        return sum( liste ) if liste else 0
    
    def is_ranked(self):
        return self.wertung.name == 'Wettkampf'
        
    def is_dsq(self):
        strafen = max( starter.strafen for starter in self.starter)
        return strafen >= self.lauf.wettkampf.disqualifikation > 0
    
    def strafen(self,sec='s'):
        strafen = dict()
        for starter in self.starter:
            if starter.einheit() not in strafen:
                strafen[starter.einheit()] = 0
            strafen[starter.einheit()] += starter.strafen
            
        if strafen:
            strafe = sum(n*e for e,n in strafen.items())
            if strafe > 0:
                unit = '' if sec=='s' else 'min'
                return "+".join(f"{n}x{e}{sec}" for e,n in strafen.items()) + f" = {time2str(strafe,zehntel=False)}{unit}"
        
        return ""
    
    def single      (self): 
        assert len(self.starter) == 1
        return list(self.starter)[0]
    
    def next_shooting(self, limit, add, elapsed=0):
        n = (self.schiessen or 0) + add
        old = self.schiessen
        self.schiessen = max(min(limit,n),0)
        if old != self.schiessen:
            self.schiessen_time = elapsed

    def get_name(self, w=None):
        name, _ = self.get_name_verein()
        return name[:w-3]+'...' if w is not None and len(name) > w else name      

    def get_name_verein(self):
        if self.ist_staffel():
            name = "Team Nummer %d"     % self.nummer if self.name          == "" else self.name
            # collect vereine removing duplicates but keeping original order
            verein = ", ".join(list(dict.fromkeys(s.verein for s in self.liste()))) 
        else:
            name = "Startnummer %d" % self.nummer if self.single().name == "" else self.single().name
            verein = self.single().verein
        return name, verein

    def update_anzahl(self, n):
        for num in range(self.anzahl(), n): 
            s = Starter(team=self, nummer=num+1,strafen=0)
            s.einheit = s.get_einheit()
        delete( s for s in Starter if s.team == self and s.nummer > n)
      
    def get_abstand(self, first):
        assert self.has_finished() and first
        abstand = self.zeit() - first.zeit()
        return "" if abstand == 0 else time2str(abstand)

    def current(self,w=None):
        idx     = self.running or 0
        starter = sorted(self.starter, key=lambda s: s.nummer)
        arrow   = ' > '#'\u21e8'
        namen   = arrow.join(s.get_name() for s in starter[idx:])
            
        return namen[:w-3]+'...' if w is not None and len(namen) > w else namen      

    def string(self, first=None, current=False, parts=False):
        abstand = self.get_abstand(first) if first and self.has_finished() else self.schuss_str()
        if any( s.fehler is None for s in self.starter ):
            fehler = None
        else: 
            fehler = self.fehler()

        prefix = "  ".join([ 
                 "%s"    % '*' if self.data_missing() else ' ',
                 "%s"    % self.platz_str(),
                 "%2d"   % self.nummer]) 
        stem   = self.current() if current else self.get_name() 
        suffix = "  ".join([
                 "%8s"   % time2str(self.zeit()), ##time.strftime('%H:%M', self.zeit()), 
                 "%-8s"  % abstand, 
                 "[%2s]" % ("--" if fehler is None else str(fehler)) ])
        if parts:
            return prefix, stem, suffix
        else:
            w    = 20
            stem = stem[:w-3]+'...' if len(stem) > w else stem
            return " ".join([prefix, f"{stem:<20}", suffix])
     
    def info(self, current=None, parts=None):
        if self.ist_staffel():
            n = self.anzahl()
            times  = ",  ".join([ "%d/%d: %s" % (idx+1,n,s.string()) for idx,s in enumerate(self.liste()) ])
            suffix = self.current() if current else self.get_name()
            if parts:
                return times, suffix
            else:
                return times+', '+suffix
        else:
            klasse = self.single().klasse
            verein = self.single().verein
            
            data = ( '%s, %s' % (klasse.name, verein) if klasse and verein != "" else
                   ( '%s'     %  klasse.name          if klasse                  else
                   ( '%s'     %               verein  if            verein != "" else '' )))
            if parts:
                return data, ""
            else:
                return data

    def stop(self, elapsed=0):
        idx = self.running
        assert idx is not None
        if idx+1 < self.anzahl():
            self.running += 1
            self.schiessen = None
            self.schiessen_time = elapsed
            return False
        else:
            self.running  = None
            return True

    def reset(self):
        self.platz     = None
        self.schiessen = None
        self.running   = None
        for s in self.starter:
            s.reset()

    def tooltip_summary(self):
        info = " > ".join(s.get_name() for s in self.liste())
        return info 

    def is_empty(self): return all( s.is_empty() for s in self.starter )

    @staticmethod
    def sortiere(teams):
        # this works since Python sorts are guaranteed to be stable
        # see wiki.python.org/moin/HowTo/Sorting#Sortingbykeys
        finished = lambda t: "n" if t.platz_str().strip() in ("", "/") else "j"
                
        return sorted( sorted( sorted(teams, 
                                      key=lambda t: t.nummer),    # tertiary  sort
                                      key=lambda t: t.zeit()),    # secondary sort
                                      key=lambda t: finished(t))  # primary   sort

class Klasse(db.Entity):
    name    = Required(unicode, unique=True)
    strafe  = Optional(int) 
    pdf     = Optional(unicode, unique=True)
    teams   = Set('Team')
    starter = Set('Starter')

    @staticmethod
    def get_or_create(name):
        if klasse := Klasse.get(name=name):
            return klasse
        else:
            return Klasse(name=name).update()

    def update(self):
        self.strafe = 45 if re.match(r'u1[0-6]', self.name, re.IGNORECASE)                    else (
                      45 if self.name.startswith('Cadet') or self.name.startswith('Aspirant') else (
                      90 ))
        return self 

class Starter(db.Entity): 
    name      = Optional(str)
    klasse    = Optional(Klasse)
    team      = Required(Team)
    nummer    = Required(int, min=1)
    verein    = Optional(str)
    laufzeit  = Optional(float)
    fehler    = Optional(int, min=0)
    strafen   = Optional(int, min=0)

    def einheit(self):
        return self.klasse.strafe if self.klasse else 90

    def strafzeit(self, sec='s'):
        if self.strafen:
            unit = '' if sec=='s' else 'min'
            fac  = self.klasse.strafe
            return f"{self.strafen}x{fac}{sec} = {time2str(self.strafen*fac, zehntel=False)}{unit}"
        else:
            return ""
    
    def data_missing(self): return not all((self.name, self.verein, self.klasse))
    
    def get_name(self, w=None):
        name = self.name                                           if self.name else (
               "Starter %d/%d"  % (self.nummer, self.team.anzahl()) if self.team.ist_staffel() else (
               "Startnummer %d" %  self.team.nummer ))
    
        return name[:w-3]+'...' if w is not None and len(name) > w else name
    
    def reset(self):
        self.laufzeit = None
        self.fehler   = None
        self.strafen  = 0
    
    def string(self):
        if self.laufzeit is None or self.laufzeit <= 0:
            return " "*12
        else:
            return "%s [%2s]" % (time2str(self.zeit()), '--' if self.fehler is None else "%2d" % self.fehler) 
    
    def is_empty(self): return all(e is None or e == "" for e in (self.name, self.klasse, self.verein))

    def zeit(self):
        return None if self.laufzeit is None else (
               0    if self.laufzeit <= 0    else (
               self.laufzeit + self.strafen*self.einheit()))


if __name__ == '__main__':    
    db.bind(provider='sqlite', filename=':memory:')
    db.generate_mapping(create_tables=True)

    with db_session:
        wettkampf = Wettkampf.create('Test')
        Wertung.create()
        lauf      = Lauf(name='Werder', wettkampf=wettkampf, wettkampf_tag = 1, tab_position=1, anzahl_schiessen=3, anzahl_pfeile=3, 
                                  auto_start=True, start_offset=0, team_groesse=1, finallauf=False)
        team      = Team(nummer = 3, lauf = lauf, name = "Werder", wertung=Wertung.get(kurzname='default'))
        cadet     = Klasse(name='Cadet (M) standard' ).update()
        senior    = Klasse(name='Senior (W) standard').update()
        Starter(name='AA', verein='WB', team=team, nummer=1, laufzeit=72, fehler=2, strafen=2, klasse=cadet)
        Starter(name='AB', verein='WB', team=team, nummer=2, laufzeit=56, fehler=3, strafen=1, klasse=senior)
        Starter(team=team, nummer=3, strafen=0)

        print(team.fehler(),team.strafen())
