from webola.finals import create_finallauf
import re


class Wertung():
    
    def __init__(self, klasse, teams=None):
        self.klasse = klasse
        self.teams  = teams or set()
        
    def add(self, team):
        self.teams.add(team)

    def laeufe(self):
        return { t.lauf for t in self.teams }

    def is_empty(self):
        return not any(l.has_finished() for l in self.laeufe())

    def split_wertungen(self, laeufe):
        wertungen   = []
        num_vorlauf = 0
        for lauf in sorted(laeufe, key=lambda l: l.tab_position):
            teams = { t for t in self.teams if t.lauf == lauf }
            t = next(iter(teams))
            if t.lauf.finallauf:
                head = 'Finallauf'
            else:
                num_vorlauf += 1                
                head = f'{num_vorlauf}. Vorlauf'
                
            wertungen.append(Wertung(self.klasse+f' ({head})', teams))

        return wertungen
        
    def maybe_split(self):
        
        use_vorlaeufe = list(self.teams)[0].lauf.wettkampf.vorlaeufe if self.teams else False
        
        if not use_vorlaeufe:
            # KEINE Vorläufe ... alle Starter:innen einer KLasse werden gemeinsam gewertet
            return [self]
        
        # MIT Vor- und Finalläufen ... gleiche Klasse in zwei Läufen erzwingt Finallauf
        laeufe = self.laeufe()
        
        if len(laeufe) == 1:
            # alle Ergebnisse aus dem gleichen Lauf ... kein Split nötig
            return [self]
        else:
            # Ergebnisse verschiedener Läufe müssen separat angezeigt werden (Vorläufe, Finallauf)
            wertungen = self.split_wertungen(laeufe)
            
            if any(l.finallauf for l in laeufe):
                # OK, Finallauf already created
                pass
            elif any(not l.has_finished() for l in laeufe):
                # OK, no need to create Finallauf (yet)
                pass
            else:
                # all Vorläufe finished => create Finallauf
                create_finallauf(wertungen, laeufe, self.klasse)
                
            return wertungen        
        
    def data(self):
        return min(t.lauf.tab_position for t in self.teams), min(t.nummer for t in self.teams)

    def key(self):
        tag = max(t.lauf.wettkampf_tag for t in self.teams)
        return self.sort_key(tag, self.klasse)
        
    @staticmethod
    def sort_key(tag, klasse):
        klasse = klasse.lower()
        alter  = 1 if klasse.startswith('cadet')    else ( 
                 2 if klasse.startswith('aspirant') else ( 
                 3 if klasse.startswith('junior')   else ( 
                 4 if klasse.startswith('u')        else (   # u15 
                 6 if klasse.startswith('senior')   else (   # u15 
                 7 if klasse.startswith('master')   else ( 
                 8 if klasse.startswith('ü')        else (   # ü35 
                 9 if klasse.startswith('s')        else (   # staffel 
                 5 ))))))))                                  # Herren/Damen
        m = re.match(r'[uü](\d+)', klasse)
        num = m.group(1) if m else '00'
        typ   = 1 if 'w' in klasse else (
                2 if 'm' in klasse else (
                3 ))
        return f"{tag}_{alter}_{num}_{typ}"

    def __lt__(self, other):
        pos , nummer  = self .data()
        opos, onummer = other.data()
        key , okey    = self.key(), other.key()
        return key <  okey or (
               key == okey and self.klasse < other.klasse or (
               key == okey and self.klasse == other.klasse and pos <  opos or ( 
               key == okey and self.klasse == other.klasse and pos == opos and nummer < onummer )))


if __name__ == '__main__':
    
    print(Wertung.sort_key(1, 'ü50 w Standard'))
    print(Wertung.sort_key(1, 'ü35m Standard'))
    
    
    
    