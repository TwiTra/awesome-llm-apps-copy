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
| 4 Tasten (2 × 2) | **Dreizack** |
| blaues Feld rechts | **Candle-Countdown** (Restzeit der aktuellen Kerze) |
| 4 schmale Tasten darunter | **Trendlinie** |
| `_` / `+` oben rechts | Panel minimieren / wiederherstellen |

Zeichnen: Taste anklicken, dann **zwei Klicks auf den Chart**. Die Taste leuchtet rot umrandet und die
Titelzeile zeigt den Schritt. Ein zweiter Klick auf dieselbe Taste oder **ESC** bricht ab. Die Farbe des
Objekts ist die Farbe der Taste. Alle Objekte lassen sich danach wie normale MT5-Objekte verschieben,
ändern und löschen.

Minimiert bleibt nur eine schmale Leiste mit dem Countdown. Die Taste bleibt an derselben Stelle. Der Zustand
bleibt bei Zeitrahmenwechsel und Neustart erhalten.

## Alarm

- Der Alarm gilt **nur für Rechtecke, die mit den 6 Alarm-Tasten gezeichnet wurden** (Objektname `TP_ALR_…`).
  Normale Rechtecke, Trendlinien und von Hand gezeichnete Rechtecke lösen nie aus.
- Ausgelöst wird, wenn der Preis von außen in das Rechteck **eintritt oder es durchquert**. Liegt der Preis
  beim Zeichnen schon im Rechteck, kommt kein Alarm, bis er es verlassen und wieder betreten hat.
- Standard: einmalig. Danach wird das Rechteck gestrichelt und ungefüllt (`InpAlarmOnce = false` löst bei jedem Eintritt aus).
- Kanäle: Popup, eigener Sound, Push aufs Handy (Eingaben unter *Alarm*).
- Standardmäßig zählt nur die Preiszone. Mit `InpAlarmTimeRange = true` löst das Rechteck nur aus, solange die Zeit im Rechteck liegt.

## Dreizack

Aus deinem Screenshot rekonstruiert, weil sich die `.ex5` nicht auslesen lässt. **1. Klick** = Start des
Impulses (A), **2. Klick** = Extrempunkt (B). Dann entstehen automatisch:

- **A–B**: Impulslinie mit Mittelpunkt bei 50 %.
- **B–C**: Rücksetzer auf 50 %. C liegt zeitlich standardmäßig eine Impulsdauer hinter B. Du kannst C in
  der Zeit verschieben, der Preis rastet immer auf 50 % ein.
- **3 Zinken**: verschobene Kopien des Impulses A–B, die bei C beginnen.
- **3 Ziellinien** bei B + **1,0 / 1,5 / 2,0 × Impulshöhe** (Eingaben `InpLevel1–3`), beschriftet mit 1, 2, 3.
  Die Preise stehen im Tooltip. Bei einem Impuls nach unten laufen die Ziele nach unten.
- **Info-Text** am Extrempunkt: `Kerzen/Punkte` (z. B. `9/98`).

Nach dem Verschieben von A, B oder C an der A–B- bzw. B–C-Linie wird der ganze Dreizack neu berechnet.
Löschst du eine der beiden Hauptlinien, verschwindet der ganze Dreizack.

## Hinweise

- Getestet wurde der Code nur mit einem C++-Stub der MQL5-API (Syntax und Typen), **nicht im MetaEditor und nicht
  im Terminal**. Falls beim Kompilieren etwas gemeldet wird, gib mir bitte die Meldung.
- Die Pixelmaße des Panels stehen als `#define` oben im Code (`BTN`, `PANEL_W` …), die Farben in den Arrays `CLR_*`.
- Ein zweiter Aufruf des Indikators auf demselben Chart wird nicht unterstützt (gleiche Objektnamen).
