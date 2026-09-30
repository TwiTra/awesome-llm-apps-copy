# TridentPanel (MetaTrader 5)

Indikator mit Zeichen-Panel nach deiner Skizze: Rechtecke mit und ohne Alarm, Dreizack,
Trendlinien und Candle-Countdown. Oben rechts im Panel sitzt die Minimieren-Taste.

## Installation

1. `TridentPanel.mq5` nach `MQL5\Indicators\` kopieren (MetaTrader: *Datei → Datenordner öffnen*).
2. Im MetaEditor öffnen und mit **F7** kompilieren.
3. Den Indikator `TridentPanel` per Drag & Drop auf den Chart ziehen.

## Bedienung

| Bereich im Panel | Funktion |
|---|---|
| 6 Tasten links (3 × 2) | **Rechteck mit Alarm**, erscheint sofort im Chart |
| 4 Tasten (2 × 2) | **Rechteck normal**, ohne Alarm, erscheint sofort im Chart |
| 4 Tasten (2 × 2) | **Dreizack**, erscheint sofort im Chart |
| blaues Feld rechts | **Candle-Countdown** (Restzeit der aktuellen Kerze) |
| 4 schmale Tasten darunter | **Trendlinie**, erscheint sofort im Chart |
| `_` / `+` oben rechts | Panel minimieren / wiederherstellen |

**Alle Tasten funktionieren gleich:** Ein Tastendruck legt das Objekt **sofort** in den sichtbaren Chart,
ausgewählt mit Anfassern. Du ziehst es dann mit der Maus an die richtige Stelle und in die richtige Größe.
Es sind keine Klicks auf den Chart nötig. Jeder Tastendruck erzeugt ein neues Objekt.

| Objekt | erscheint | Startgröße (einstellbar) |
|---|---|---|
| Rechteck (mit/ohne Alarm) | bei 45 % der Chartbreite, senkrecht mittig | 30 Kerzen × 60 px (`InpRectBars`, `InpRectHeight`) |
| Trendlinie | ab 40 % der Chartbreite, im oberen Drittel | 30 Kerzen lang, 60 px steigend (`InpTrendBars`, `InpTrendRise`) |
| Dreizack | ab 35 % der Chartbreite, im unteren Viertel | Impuls 4 Kerzen × 130 px (`InpTridentBars`, `InpTridentHeight`) |

Die Farbe des Objekts ist die Farbe der Taste. Alle Objekte lassen sich wie normale MT5-Objekte verschieben,
ändern und löschen. Bei einem flachen Chartfenster werden die Starthöhen automatisch verkleinert.

Minimiert bleibt nur eine schmale Leiste mit dem Countdown. Die Taste bleibt an derselben Stelle. Der Zustand
bleibt bei Zeitrahmenwechsel und Neustart erhalten.

## Position

Einstellung *1 | Position des Panels → Art der Positionierung*:

**Feste Position (Ecke)** – Standard
- Ecke wählbar: **oben rechts** (Standard), oben links, unten rechts, unten links.
- `InpPanelX` = Abstand zum seitlichen Rand, `InpPanelY` = Abstand zum oberen bzw. unteren Rand (Pixel).
- Beim Vergrößern oder Verkleinern des Fensters bleibt der Abstand zu dieser Ecke gleich.

**Eingabe X/Y**
- `InpPosX` und `InpPosY` in **Prozent des Chartfensters**: X = 0 ganz links, 100 ganz rechts, Y = 0 ganz oben,
  100 ganz unten. Beispiele: 100/3 = oben rechts, 50/50 = Mitte, 0/100 = unten links.
- Weil die Angabe in Prozent ist, wandert das Panel beim Vergrößern oder Verkleinern mit und behält seine
  relative Lage (bei 50/50 bleibt es in der Mitte). Es bleibt dabei immer ganz sichtbar.

Für beide Arten gilt:
- Minimiert bleibt die Taste `_` / `+` an derselben Stelle. Bei den unteren Ecken schwebt die minimierte Leiste
  daher dort, wo vorher die Oberkante des Panels war.
- Ist das Fenster kleiner als das Panel, klemmt es am linken bzw. oberen Rand.
- Das Panel zieht nach, sobald MetaTrader die neue Fenstergröße meldet (spätestens nach 0,25 s).
- Falls das Panel bei dir die Preisskala am rechten Rand überdeckt, vergrößere `InpPanelX` bzw. verkleinere `InpPosX`.

## Einstellungen (Inputs)

Übersichtlich in nummerierte Gruppen sortiert:

| Gruppe | Inhalt |
|---|---|
| 1 \| Position des Panels | Feste Position (Ecke) oder Eingabe X/Y, Ecke, Abstände, X/Y in % |
| 2 \| Farben: Rechtecke mit Alarm | Farbe jeder der 6 Tasten (Reihenfolge wie im Panel) |
| 3 \| Farben: Rechtecke normal | Farbe jeder der 4 Tasten |
| 4 \| Farben: Dreizack | Farbe jeder der 4 Tasten |
| 5 \| Farben: Trendlinien | Farbe jeder der 4 schmalen Tasten |
| 6 \| Rechtecke | Rahmenbreite, Füllung, Startgröße neuer Rechtecke |
| 7 \| Alarm | Popup, Sound, Push, einmalig, Zeitbereich |
| 8 \| Dreizack | Startgröße, Linienbreite (Standard 2), Info-Text, grüne Zone, Ziellinien |
| 9 \| Trendlinien | Linienbreite, Strahl nach rechts, Startlänge und -anstieg neuer Trendlinien |

Die Farbe einer Taste ist zugleich die Farbe des Objekts, das sie zeichnet. Eine Änderung wirkt für neu
gezeichnete Objekte. Bereits gezeichnete Objekte behalten ihre Farbe.

## Dreizack

Ein Druck auf eine der 4 Dreizack-Tasten legt den Dreizack **sofort** in den sichtbaren Chartbereich, ausgewählt
mit Anfassern wie im Original. Du ziehst ihn dann passend an:

- **A** (unten): Start des Impulses. **B** (oben): Extrempunkt des Impulses. Mit dem mittleren Anfasser der
  Linie A–B verschiebst du den ganzen Dreizack.
- **C**: Rücksetzer. Er sitzt zu Beginn 3 Impulsbreiten hinter B auf 50 % der Impulshöhe und lässt sich frei ziehen.
- Nach dem Loslassen wird alles neu berechnet. Ziehst du A oder B, behält C sein Verhältnis zum Impuls.
- Löschst du die Linie A–B oder B–C, verschwindet der ganze Dreizack. Jeder Tastendruck erzeugt einen neuen.

Aufbau (aus deinen Screenshots auf 1 px genau nachgemessen), mit **L = A→B** und **R = B→C**:

| Teil | von | bis |
|---|---|---|
| linke Zinke | B + L | B + 2·L |
| mittlere Zinke | C | C + 2·L |
| rechte Zinke | B + L + 2·R | B + 2·L + 2·R |
| Diagonale | B + L | B + L + 2·R |
| grüne Zone (gestricheltes Rechteck) | A, zu Beginn 50 Kerzen breit | bis zur Höhe von C |

**Grüne Zone (unterer Teil):** Sie lässt sich anklicken. Ziehst du ihren **rechten Rand nach rechts** (oder
schiebst das ganze Rechteck nach rechts), wird sie länger. Die linke Kante bleibt an A und die Höhe reicht von
A bis C. Die gewählte Breite bleibt erhalten, wenn du A, B oder C bewegst, und auch nach Zeitrahmenwechsel und
Neustart. Ziehst du sie zu weit nach links, bleibt mindestens 1 Kerze. Startbreite: `InpBoxBars`, ausblenden:
`InpShowBox`. A–B und B–C haben beim Anklicken Vorrang, die Zone erreichst du also an ihrer Oberkante oder am
rechten Rand.

Die Linien sind standardmäßig **2 px dick** (`InpTridentWidth`).

Mit C bei 50 % liegen die Zinkenspitzen bei **1,0 / 1,5 / 2,0 × Impulshöhe** über B. Am Extrempunkt steht
`Kerzen/Punkte` des Impulses (z. B. `4/69`).

Optional (`InpShowLevels`) zeichnet der Indikator zusätzlich waagrechte Ziellinien 1, 2, 3 ab den Zinkenspitzen,
wie in deinem ersten Screenshot. Standardmäßig ist das aus, weil die Vorlage sie nicht zeigt.

## Alarm

- Der Alarm gilt **nur für Rechtecke, die mit den 6 Alarm-Tasten gezeichnet wurden** (Objektname `TP_ALR_…`).
  Normale Rechtecke, Trendlinien und von Hand gezeichnete Rechtecke lösen nie aus.
- Ausgelöst wird, wenn der Preis von außen in das Rechteck **eintritt oder es durchquert**. Liegt der Preis
  beim Erzeugen oder Hinziehen schon im Rechteck, kommt kein Alarm, bis er es verlassen und wieder betreten hat.
- Standard: einmalig. Danach wird das Rechteck gestrichelt und ungefüllt (`InpAlarmOnce = false` löst bei jedem Eintritt aus).
- Kanäle: Popup, eigener Sound, Push aufs Handy (Eingaben unter *Alarm*).
- Standardmäßig zählt nur die Preiszone. Mit `InpAlarmTimeRange = true` löst das Rechteck nur aus, solange die Zeit im Rechteck liegt.

## Hinweise

- Der Code wurde nur mit einem Chart-Simulator getestet (C++-Nachbau der verwendeten MQL5-Funktionen), **nicht im
  MetaEditor und nicht im Terminal**. Falls beim Kompilieren etwas gemeldet wird oder sich etwas anders verhält,
  gib mir bitte die Meldung bzw. einen Screenshot.
- Der Dreizack wird beim Loslassen neu berechnet, nicht während des Ziehens.
- Standardfarben: Dreizack-Tasten 1 und 4 wie im Original (DeepSkyBlue, MediumPurple), grüne Zone
  `InpBoxColor`, der Rest nach deiner Skizze. Die Pixelmaße des Panels stehen als `#define` im Code
  (`BTN`, `PANEL_W` …).
- Ein zweiter Aufruf des Indikators auf demselben Chart wird nicht unterstützt (gleiche Objektnamen).
