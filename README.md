# Webola -- *We*rderaner *Bo*gen*la*uf     (2025.4.26)

<!-- toc -->

- [Einleitung](#einleitung)
- [Installation](#installation)
- [Verwendung](#verwendung)
  * [Vorbereitung](#vorbereitung)
  * [Zeitmessung](#zeitmessung)
    + [Registerkarten und Läufe](#registerkarten-und-laufe)
    + [Starter/Teams editieren](#starterteams-editieren)
    + [Einen Lauf durchführen](#einen-lauf-durchfuhren)
    + [Strafrunden erfassen](#strafrunden-erfassen)
  * [Ergebnisse auswerten](#ergebnisse-auswerten)
  * [Staffeln](#staffeln)
- [Tipps zum GUI](#tipps-zum-gui)

<!-- tocstop -->

## Einleitung

**webola** ist eine Software zur Zeitmessung bei Bogenläufen und ähnlichen Veranstaltungen. Dabei werden Einzel- und Staffelwettkämpfe unterstützt. Meldungen werden aus speziell formatierten XLSX-Dateien eingelesen. In jedem Lauf können maximal 20 Starter/Teams starten. Starter/Teams können auch *außer Konkurrenz* gewertet werden, so dass Zeiten gemessen, aber keine Platzierungen vergeben werden. 

Das Hauptfenster ist für jeden Lauf zweigeteilt: Zunächst werden alle Starter/Teams in der linken Hälfte sortiert nach Startnummer angezeigt. Personenbezogene Daten wie Name, Verein, Bogenklasse, Wertung, usw. können editiert werden. Nachdem der Lauf gestartet wurde, werden gelaufene Runden farblich markiert. Die aktuelle Reihenfolge wird entsprechend angepasst. Mit den Funktionstasten werden Zieleinläufe erfasst. Die Zeiten werden gestoppt und die Starter/Teams auf die rechte Seite des Fensters sortiert. 

Während des Laufes oder nach Abschluss des Laufen können Strafrunden und ggf. Strafzeiten eingetragen werden. Ergebislisten mit Zeiten und Abständen werden automatisch erstellt. Die Daten können als XLSX-Datei exportiert werden. Wenn LaTeX vorhanden ist, können auch Urkunden automatisch als PDF-Dateien erstellt werden.

![Webola GUI](resources/screenshot-notes.pdf)


## Installation

**webola** wurde mit **python** und **pyqt** entwickelt. Eine aktuelle Version von **python** kann unter

> https://www.python.org

heruntergeladen und installiert werden. Dabei ist darauf zu achten, dass **pip** mitinstalliert wird und dass **python** zur Pfadvariablen hinzugefügt wird. 

Neben **python** wird noch **git** benötigt, um auf das Repository von **webola** zugreifen zu können. Beim Installieren von **git** können alle voreingestellten Optionen unverändert bleiben:

> https://git-scm.com

Jetzt kann **webola** direkt von der Eingabeaufforderung installiert werden:

    pip install git+https://github.com/svoigtmann/webola.git

## Verwendung

Beim Einsatz von **webola** gibt es drei Phasen: Vorbereitung, Zeitnahme und Auswertung.

### Vorbereitung

Vor Beginn des Wettkampfs werden alle Meldungen in einer Startliste gesammelt. Damit die Daten direkt mit **webola** eingelesenw werden können, muss die Startliste ein definiertes Format haben. Als Vorlage können 

> startliste_dummy.xlsx oder
> startliste_bunt.xlsx

verwendet werden. **webola** wird dann mit 

    python -m webola <startliste.xlsx>

gestartet. Während des Wettkampfes werden alle Ergebnisse werden alle Ergebnisse in eine zugehörige Datei *startliste.sql* geschrieben. Die Zeitnahme kann jederzeit unterbrochen werden. Wenn **webola** mit 

    python -m webola <startliste.sql>

neu gestartet wird, dann kann der Wettkampf mit den aktuellen Daten direkt fortgesetzt werden. 

Zusätzlich zur Startliste können einige wenige Kommandozeilenparameter verwendet werden. Ein typischer Aufruf sieht wie folgt aus:

    python -m webola -f <startliste.sql> -o zielliste.xlsx

| Kurz | Lang        |           | Beschreibung                                                 |
| ---- | :---        | ---       | :------------                                                |
| -f   | --force     |           | Überschreibe die SQL-Datei / Zielliste ohne Nachfrage.       |
| -p   | --pfeile    |  n        | Verwende n Pfeile pro Schießen (default: 4)                  |
| -s   | --schiessen |  n        | Verwende n Schießen pro Lauf (default: 3)                    |
| -v   | --vorlaeufe |           | Verwende Vor- und Finalläufe (experimentell)                 |
| -o   | --output    | file.xlsx | Schreibe alle Auswertungsergebnisse in die Datei *file.xlsx* |
| -dm  | --dm-mode   |           | Starter mit 'Team Poland', 'Czech Team', 'Archery Club ...' starten außer Konkurrenz |

### Zeitmessung

Wenn alle Informationen der Startliste eingelesen wurden, startet **webola** mit einer separaten Registerkarte pro Lauf.

#### Registerkarten und Läufe

Die Registerkarten (Läufe) können durch Mausklicks bzw. mit den Tasten *Bild hoch* bzw. *Bild herunter* gewechselt werden. Mit *Klick'n'Drag* können die Läufe beliebig sortiert werden. Neue Läufe können mit dem *+*-Symbol angelegt werden. Im Kontextmenü (*Rechtsklick*) gibt es eine Option, um einzelne Läufe zu löschen. Mit dem Kontextmenü kann auch eine Tag-Markierung gesetzt werden, damit bei Wettkämpfen, die sich über zwei Tage erstrecken, Läufe des ersten/zweiten Tages unterschieden werden können. 

Für jeden Lauf kann ein Titel vergeben werden. Die geplante Startzeit wird später mit der tatsächlichen Startzeit überschrieben. Die Anzahl Schießen/Pfeile kann pro Lauf variiert werden.

Mit der Combobox *Starter* können weitere Starter hinzugefügt/gelöscht werden. Außerdem können im Toolbar der Startmodus und/oder der Staffelmodus umgeschaltet werden. Neben dem Button *Lauf starten* ist eine Akku-Anzeige eingeblendet, so dass z.B. eine fehlende Stromversorgung während des Wettkampfes schnell erkannt wird.

#### Starter/Teams editieren

Für jeden Starter, für jedes Team, wird die Startnummer, der Name, die Bogenklasse und der Verein angezeigt. Mit einem Klick können diese Daten bearbeitet werden. 

Die Startnummer kann aktuell *nicht* geändert werden. Im Zweifel müssen z.B. leere Starter:innen angelegt werden, um die richtige Reihenfolge der Starter zu erreichen. 

Wichtig ist, z.B. bei der Deutschen Meisterschaft bei einzelnen Startern/Teams ggf. den Modus von *Wettkampf* auf *außer Konkurrenz* zu ändern, weil nur deutsche Vereine Medaillen erreichen können. Dazu muss der Button des Starters/Teams angeklickt werden, so dass die entsprechenden Daten editiert werden können. 

Über das Kontextmenü können neue Starter hinzugefügt oder gelöscht werden. Das Hinzufügen kann oberhalb oder unterhalb des aktuellen Eintrags erfolgen. 

In jedem Lauf können maximal 20 Starter/Teams starten. 

#### Einen Lauf durchführen

Mit einem Klick auf *Lauf starten* wird der aktuelle Lauf gestartet. Alle Starter/Teams werden für 10 Sekunden grün markiert, um einen erfolgreichen Start zu bestätigen. Die aktuelle Registerkarte wird mit einem * markiert.

Mit den normalen Zifferntasten können Runden für einzelne Starter/Teams markiert werden. Die Anzahl der bereits durchgeführten Schießen wird dann mit jeweils einem Punkt angezeigt. Die Reihenfolge der Starter/Teams wird während des Laufes entsprechend der Rundenmarkierungen/Zeiten angepasst. Der Starter / das Team wird grün/gelb/rot markiert, wenn noch zwei, eins oder kein Schießen mehr offen sind. Die Farbkodierung sichert, dass kein Zieleinlauf verpasst wird. 

| Team Nummer | Schießen markieren | Markierung zurücknehmen  | Starten / stoppen |
| :---------: | :----------------: | :----------------------: | :---------------: | 
|      1      |          1         |          Shift+1         |       F1          |
|      2      |          2         |          Shift+2         |       F2          |
|      3      |          3         |          Shift+3         |       F3          |
|      4      |          4         |          Shift+4         |       F4          |
|      5      |          5         |          Shift+5         |       F5          |
|      6      |          6         |          Shift+6         |       F6          |
|      7      |          7         |          Shift+7         |       F7          |
|      8      |          8         |          Shift+8         |       F8          |
|      9      |          9         |          Shift+9         |       F9          |
|     10      |          0         |          Shift+0         |       F10         |
|     11      |     Strg+1         |     Strg+Shift+1         |  Strg+F1 oder F11 |
|     12      |     Strg+2         |     Strg+Shift+2         |  Strg+F2 oder F12 |
|     13      |     Strg+3         |     Strg+Shift+3         |  Strg+F3 oder F13 |
|     14      |     Strg+4         |     Strg+Shift+4         |  Strg+F4 oder F14 |
|     15      |     Strg+5         |     Strg+Shift+5         |  Strg+F5          |
|     16      |     Strg+6         |     Strg+Shift+6         |  Strg+F6          |
|     17      |     Strg+7         |     Strg+Shift+7         |  Strg+F7          |
|     18      |     Strg+8         |     Strg+Shift+8         |  Strg+F8          |
|     19      |     Strg+9         |     Strg+Shift+9         |  Strg+F9          |
|     20      |     Strg+0         |     Strg+Shift+0         |  Strg+F10         |

Beim Zieldurchgang wird der Starter / das Team mit der entsprechenden Funktionstaste *F1* bis *F14* abgestoppt. Mit *Strg+F1* bis *Strg+F10* werden die Nummern 11 bis 20 ausgewählt. Beim Drücken der Funktionstaste wird die Zeit genommen und der Starter / das Team auf die rechte Seite des Fensters verschoben. Somit ist klar zu erkennen, wie viele Starter/Teams noch auf der Strecke sind. Die Starter/Teams können auch mit einem einfachen Klick abgestoppt werden. 

Sollte das falsche Team gestoppt worden sein, kann der Wettkampf durch Anklicken oder durch Drücken der entsprechenden Funktionstaste wieder aufgenommen werden.

Starter/Teams, die das Ziel erreicht haben, werden auf der rechten Seite in der Reihenfolge des Zieleinlaufs angezeigt. Die Patzierung innerhalb des Laufs wird in runden Klammern angezeigt: (1), (2), ... Starter/Teams, die *außer Konkurrenz* starten, werden mit /2/, /3/, ... markiert.

Der Lauf wird durch Klicken auf *Lauf beenden* beendet. Starter/Teams, die das Ziel nicht erreicht haben, verbleiben auf der linken Seite des Fensters und werden später als *DNF* markiert (*did not finish*). Nach Anklicken des Buttons kann *DNF* auch durch *DNS* ersetzt werden (*did not start*).

#### Strafrunden erfassen

Strafrunden und Zeitstrafen können während des Laufes oder nach dem Lauf erfasst werden. Entweder wird jeder Starter / jedes Teams einzeln bearbeitet, oder alle Strafrunden werden werden gesammelt eingetragen, indem auf den Button *Strafrunden eintragen* geklickt wird (im Toolbar zwischen *Startzeit* und *Schießen*). Der Dialog kann auch mit *Strg+S* gestartet werden.

Bei zu wenig gelaufenen Strafrunden erhalten Kinder 45 Sekunden und Erwachsene 90 Sekunden Strafzeit. Diese Strafzeiten können nur einzeln erfasst werden, indem der Starter / das Team bearbeit wird. 

### Ergebnisse auswerten

Alle Zwischenergebnisse (Zeiten, Abstände, Strafrunden und -zeiten) werden sortiert nach der Bogenklasse fortlaufend in der Registerkarte *Ergebnis* aktualisiert. Dort kann auch der aktuelle Medaillenspiegel eingesehen werden.

Wichtig ist, in der die Registerkarte *Ergebnis* den Namen des Wettkampfes und das Datum anzupassen.

Durch Klick auf den *Export* Button werden die Ergebnisse als XLSX-Datei in die sog. Zielliste geschrieben. 

> **Achtung:** Unter Windows kann *nicht* in bereits geöffnete Dateien geschrieben werden. Wenn die Zielliste also bereits geöffnet ist, dann liefert **webola** beim Export einen Fehler. Deshalb muss vor dem Export die Zielliste geschlossen werden.

Die Tabelle *Ergebnis* entspricht der Registerkarte *Ergebnis*. Die weiteren Tabellen umfassen den Medaillenspiegel und die Ergebnisse für jeden einzelnen Lauf. Diese Tabellen können z.B. verwendet werden, um während des Wettkampfs Zwischenergebnisse für die Teilnehmenden auszuhängen. 

Schließlich gibt es noch Serienbrief-Tabellen für Einzel- und Staffelrennen. Dort sind alle Ergebnisse detailliert aufgeführt, so dass z.B. mit Hilfe von Serienbriefen Urkunden automatisiert gedruckt werden können. 

Wenn das Textsatz-System LaTeX verfügbar ist, können Urkunden auch direkt mit **webola** erzeugt werden. Es werden unterschiedliche Vorlagen und viele Konfigurationsmöglichkeiten unterstützt.

Auch wenn LaTeX nicht verfügbar ist, können die entsprechenden TEX-Dateien dennoch erzeugt werden. Dort sind ebenfalls alle Daten verfügbar.

### Staffeln

Wenn Staffeln durchgeführt werden sollen, ist wie folgt vorzugehen:

  * Mit *+* wird ein neuer Lauf (Registerkarte) angelegt.
  * Im Toolbar wird mir dem Button *Staffel* der Staffelmodus eingeschaltet. Gleichzeit muss die Anzahl der Starter pro Team gesetzt werden.
  * Für jedes Staffelrennen muss ein Name (Titel) vergeben werden (z.B. *u17* oder *ab u20*). Außerdem müssen die Anzahlen Schießen / Pfeile ggf. angepasst werden. Bei der Anzahl der Pfeile werden Nachlader *nicht* mitgezählt.
    Sollten 3 Schießen korrekt sein, kann mit den Pfeiltasten hoch/runter die rote Markierung entfernt werden.
  * Teams werden über die Combobox *Starter* mit dem *Pfeil hoch* angelegt. Das zweite und weitere Teams können auch über das Kontextmenü (*Rechtsklick*) bereits vorhandener Teams angelegt werden.
  * Wie üblich werden Teams mit einem einfachen Klick bearbeitet. Beim Eingeben der Namen kann die Auto-Vervollständigung verwendet werden.

Staffelrennen werden wie üblich gestartet und durchgeführt. Rundenmarkierungen werden wiederum mit den normalen Zifferntasten gesetzt. Allerdings werden die Funktionstasten jetzt verwendet, um Wechsel innerhalb des Teams zu markieren. Erst beim letzten Starter eines Teams bedeutet die Funktionstaste den Zieldurchlauf. 

Es können maximal 20 Staffeln gleichzeitig starten. Alle Staffeln eines Laufes werden gleichzeitig gewertet.

## Tipps zum GUI

Das **webola**-GUI ist (hoffentlich) weitestgehend selbsterklärend. Deshalb nur ein paar Hinweise:

 * Mit *Strg+-* bzw *Strg++* wird die Schriftgröße verkleinert/vergrößert. 
 * Mit *Strg+F* kann in den Vollbildmodus gewechselt werden. Es gibt dafür auch einen Button links unten neben dem *Export* Button.
 * Starter/Teams können mit dem Suchfeld unten rechts gesucht wurden. Bei Auswahl des Starters/Teams springt **webola** zur entsprechenden Registerkarte. 
 * Bei Staffelläufen kann der Anzeigemodus mit dem Button rechts neben *Staffel* im Toolbar umgeschaltet werden: Entweder wird der Teamname oder direkt die Starter angezeigt. 



Copyright 2019-2025 <steffen.voigtmann@web.de> GPLv3
