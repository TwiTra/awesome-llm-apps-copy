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
| 6 Tasten links (3 × 2) | **Rechteck mit Alarm** |
| 4 Tasten (2 × 2) | **Rechteck normal**, ohne Alarm |
| 4 Tasten (2 × 2) | **Dreizack**, erscheint sofort im Chart |
| blaues Feld rechts | **Candle-Countdown** (Restzeit der aktuellen Kerze) |
| 4 schmale Tasten darunter | **Trendlinie** |
| `_` / `+` oben rechts | Panel minimieren / wiederherstellen |

**Rechtecke und Trendlinien:** Taste anklicken, dann **zwei Klicks auf den Chart**. Die Taste ist rot umrandet
und die Titelzeile zeigt den Schritt. Ein zweiter Klick auf dieselbe Taste oder **ESC** bricht ab. Die Farbe
des Objekts ist die Farbe der Taste. Alle Objekte lassen sich danach wie normale MT5-Objekte verschieben,
ändern und löschen.

**Dreizack:** siehe unten. Ein Tastendruck genügt, es sind keine Klicks auf den Chart nötig.

Minimiert bleibt nur eine schmale Leiste mit dem Countdown. Die Taste bleibt an derselben Stelle. Der Zustand
bleibt bei Zeitrahmenwechsel und Neustart erhalten.

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
| gestricheltes Rechteck (grün) | A, 50 Kerzen breit | bis zur Höhe von C |

Mit C bei 50 % liegen die Zinkenspitzen bei **1,0 / 1,5 / 2,0 × Impulshöhe** über B. Am Extrempunkt steht
`Kerzen/Punkte` des Impulses (z. B. `4/69`).

Optional (`InpShowLevels`) zeichnet der Indikator zusätzlich waagrechte Ziellinien 1, 2, 3 ab den Zinkenspitzen,
wie in deinem ersten Screenshot. Standardmäßig ist das aus, weil die Vorlage sie nicht zeigt.

## Alarm

- Der Alarm gilt **nur für Rechtecke, die mit den 6 Alarm-Tasten gezeichnet wurden** (Objektname `TP_ALR_…`).
  Normale Rechtecke, Trendlinien und von Hand gezeichnete Rechtecke lösen nie aus.
- Ausgelöst wird, wenn der Preis von außen in das Rechteck **eintritt oder es durchquert**. Liegt der Preis
  beim Zeichnen schon im Rechteck, kommt kein Alarm, bis er es verlassen und wieder betreten hat.
- Standard: einmalig. Danach wird das Rechteck gestrichelt und ungefüllt (`InpAlarmOnce = false` löst bei jedem Eintritt aus).
- Kanäle: Popup, eigener Sound, Push aufs Handy (Eingaben unter *Alarm*).
- Standardmäßig zählt nur die Preiszone. Mit `InpAlarmTimeRange = true` löst das Rechteck nur aus, solange die Zeit im Rechteck liegt.

## Hinweise

- Der Code wurde nur mit einem Chart-Simulator getestet (C++-Nachbau der verwendeten MQL5-Funktionen), **nicht im
  MetaEditor und nicht im Terminal**. Falls beim Kompilieren etwas gemeldet wird oder sich etwas anders verhält,
  gib mir bitte die Meldung bzw. einen Screenshot.
- Der Dreizack wird beim Loslassen neu berechnet, nicht während des Ziehens.
- Farben: Dreizack-Tasten blau und lila wie im Original (DeepSkyBlue, MediumPurple), gestricheltes Rechteck grün
  (`InpBoxColor`). Die übrigen Farben stehen im Code in den Arrays `CLR_*`, die Pixelmaße des Panels als `#define`
  (`BTN`, `PANEL_W` …).
- Ein zweiter Aufruf des Indikators auf demselben Chart wird nicht unterstützt (gleiche Objektnamen).
