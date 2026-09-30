//+------------------------------------------------------------------+
//|                                                 TridentPanel.mq5 |
//|  Zeichen-Panel: Rechtecke (normal / mit Alarm), Dreizack,        |
//|  Trendlinien und Candle-Countdown mit Minimieren-Taste.          |
//+------------------------------------------------------------------+
#property copyright   "TridentPanel"
#property version     "1.30"
#property description "Panel mit Rechtecken (normal / mit Alarm), Dreizack, Trendlinien und Candle-Countdown"
#property indicator_chart_window
#property indicator_plots 0

//--- Position des Panels -------------------------------------------
enum ENUM_TP_POSMODE
  {
   TP_POSMODE_FIXED = 0,   // Feste Position (Ecke)
   TP_POSMODE_XY    = 1    // Eingabe X/Y (in % des Chartfensters)
  };

enum ENUM_TP_CORNER
  {
   TP_CORNER_RIGHT_UPPER = 0,   // Oben rechts
   TP_CORNER_LEFT_UPPER  = 1,   // Oben links
   TP_CORNER_RIGHT_LOWER = 2,   // Unten rechts
   TP_CORNER_LEFT_LOWER  = 3    // Unten links
  };

//--- Eingaben -------------------------------------------------------
input group "1 | Position des Panels"
input ENUM_TP_POSMODE InpPosMode   = TP_POSMODE_FIXED;      // Art der Positionierung
input ENUM_TP_CORNER  InpPosCorner = TP_CORNER_RIGHT_UPPER; // Feste Position: Ecke
input int    InpPanelX           = 10;           // Feste Position: Abstand zum seitlichen Rand (px)
input int    InpPanelY           = 25;           // Feste Position: Abstand zum oberen bzw. unteren Rand (px)
input double InpPosX             = 100.0;        // Eingabe X/Y: X in % (0 = ganz links, 100 = ganz rechts)
input double InpPosY             = 3.0;          // Eingabe X/Y: Y in % (0 = ganz oben, 100 = ganz unten)

input group "2 | Farben: Rechtecke mit Alarm (6 Tasten)"
input color  InpClrAlarm1        = C'112,173,71';  // Taste 1 (oben links)
input color  InpClrAlarm2        = C'91,155,213';  // Taste 2 (oben Mitte)
input color  InpClrAlarm3        = C'237,125,49';  // Taste 3 (oben rechts)
input color  InpClrAlarm4        = C'255,192,0';   // Taste 4 (unten links)
input color  InpClrAlarm5        = C'255,0,0';     // Taste 5 (unten Mitte)
input color  InpClrAlarm6        = C'112,48,160';  // Taste 6 (unten rechts)

input group "3 | Farben: Rechtecke normal (4 Tasten)"
input color  InpClrNormal1       = C'91,155,213';  // Taste 1 (oben links)
input color  InpClrNormal2       = C'146,208,80';  // Taste 2 (oben rechts)
input color  InpClrNormal3       = C'244,177,131'; // Taste 3 (unten links)
input color  InpClrNormal4       = C'190,90,240';  // Taste 4 (unten rechts)

input group "4 | Farben: Dreizack (4 Tasten)"
input color  InpClrTri1          = C'0,191,255';   // Taste 1 (oben links)
input color  InpClrTri2          = C'112,173,71';  // Taste 2 (oben rechts)
input color  InpClrTri3          = C'255,192,110'; // Taste 3 (unten links)
input color  InpClrTri4          = C'147,112,219'; // Taste 4 (unten rechts)

input group "5 | Farben: Trendlinien (4 schmale Tasten)"
input color  InpClrTrend1        = C'91,155,213';  // Taste 1 (links)
input color  InpClrTrend2        = C'112,173,71';  // Taste 2
input color  InpClrTrend3        = C'237,125,49';  // Taste 3
input color  InpClrTrend4        = C'190,90,240';  // Taste 4 (rechts)

input group "6 | Rechtecke"
input int    InpRectWidth        = 1;            // Rahmenbreite
input bool   InpFillAlarm        = true;         // Alarm-Rechtecke ausfüllen
input bool   InpFillNormal       = false;        // Normale Rechtecke ausfüllen
input int    InpRectBars         = 30;           // Startbreite neuer Rechtecke (Kerzen)
input int    InpRectHeight       = 60;           // Starthöhe neuer Rechtecke (Pixel)

input group "7 | Alarm (gilt nur für Alarm-Rechtecke)"
input bool   InpAlarmPopup       = true;         // Popup-Fenster (Alert)
input bool   InpAlarmSound       = false;        // Zusätzlich eigene Sound-Datei abspielen
input string InpAlarmSoundFile   = "alert2.wav"; // Sound-Datei (Ordner MQL5\Sounds bzw. Sounds)
input bool   InpAlarmPush        = false;        // Push-Nachricht aufs Handy
input bool   InpAlarmOnce        = true;         // Nur einmal auslösen (danach Rechteck gestrichelt)
input bool   InpAlarmTimeRange   = false;        // Nur auslösen, solange die Zeit im Rechteck liegt

input group "8 | Dreizack"
input int    InpTridentBars      = 4;            // Startbreite des Impulses A-B (Kerzen)
input int    InpTridentHeight    = 130;          // Starthöhe des Impulses A-B (Pixel)
input int    InpTridentWidth     = 2;            // Linienbreite
input bool   InpShowInfo         = true;         // Info-Text "Kerzen/Punkte" am Extrempunkt
input bool   InpShowBox          = true;         // Grüne Zone (gestricheltes Rechteck) anzeigen
input int    InpBoxBars          = 50;           // Startbreite der grünen Zone (Kerzen); später per Maus ziehbar
input color  InpBoxColor         = clrMediumSeaGreen; // Farbe der grünen Zone
input bool   InpShowLevels       = false;        // Zusätzlich waagrechte Ziellinien 1/2/3 zeichnen
input int    InpLevelBars        = 100;          // Länge der Ziellinien (Kerzen)
input int    InpLevelWidth       = 2;            // Linienbreite der Ziellinien

input group "9 | Trendlinien"
input int    InpTrendWidth       = 1;            // Linienbreite
input bool   InpTrendRay         = false;        // Strahl nach rechts
input int    InpTrendBars        = 30;           // Startlänge neuer Trendlinien (Kerzen)
input int    InpTrendRise        = 60;           // Startanstieg neuer Trendlinien (Pixel; negativ = fallend)

//--- Objektnamen ----------------------------------------------------
#define PFX_UI      "TP_UI_"
#define PFX_ALARM   "TP_ALR_"
#define PFX_RECT    "TP_RCT_"
#define PFX_TRI     "TP_TRI_"
#define PFX_TREND   "TP_TRD_"
#define NM_STATE    "TP_STATE"
#define NM_BG       "TP_UI_BG"
#define NM_TITLE    "TP_UI_TITLE"
#define NM_MIN      "TP_UI_MIN"
#define NM_TBG      "TP_UI_TBG"
#define NM_TXT      "TP_UI_TXT"
#define NM_BTN      "TP_UI_BTN_"
#define NM_SEP1     "TP_UI_SEP1"
#define NM_SEP2     "TP_UI_SEP2"
#define NM_SEP3     "TP_UI_SEP3"

// Der Alarm-Zustand steht im Tooltip des Rechtecks (nicht im Beschreibungstext, der im Chart erscheinen kann)
#define TT_ALARM_ON   "Alarm-Rechteck (aktiv)"
#define TT_ALARM_OFF  "Alarm-Rechteck (ausgelöst)"

//--- Layout (Pixel, relativ zur linken oberen Panel-Ecke) -----------
#define BTN        24     // Kantenlänge der quadratischen Tasten
#define GAP         4     // Abstand zwischen Tasten
#define PAD         6     // Innenrand
#define TITLE_H    18     // Titelleiste
#define ROW0       22     // y der ersten Tastenreihe
#define ROW1       50     // y der zweiten Tastenreihe
#define PANEL_W   361
#define PANEL_H    80
#define MIN_W     130     // Breite im minimierten Zustand
#define MIN_H      22
#define GX_ALARM    6     // Gruppe 1: Alarm-Rechtecke (3 x 2)
#define GX_NORMAL  97     // Gruppe 2: normale Rechtecke (2 x 2)
#define GX_TRI    160     // Gruppe 3: Dreizack (2 x 2)
#define GX_TIMER  223     // Gruppe 4: Candle-Timer + Trendlinien
#define GW_TIMER  132
#define TIMER_H    34
#define TREND_Y    60
#define TREND_W    30
#define TREND_H    14

//--- Farben der Tasten und Objekte (werden in Colors_Init aus den Eingaben gefüllt)
color CLR_ALARM[6];
color CLR_NORMAL[4];
color CLR_TRI[4];
color CLR_TREND[4];

void Colors_Init()
  {
   CLR_ALARM[0] = InpClrAlarm1;  CLR_ALARM[1] = InpClrAlarm2;  CLR_ALARM[2] = InpClrAlarm3;
   CLR_ALARM[3] = InpClrAlarm4;  CLR_ALARM[4] = InpClrAlarm5;  CLR_ALARM[5] = InpClrAlarm6;
   CLR_NORMAL[0] = InpClrNormal1; CLR_NORMAL[1] = InpClrNormal2;
   CLR_NORMAL[2] = InpClrNormal3; CLR_NORMAL[3] = InpClrNormal4;
   CLR_TRI[0] = InpClrTri1;      CLR_TRI[1] = InpClrTri2;      CLR_TRI[2] = InpClrTri3;   CLR_TRI[3] = InpClrTri4;
   CLR_TREND[0] = InpClrTrend1;  CLR_TREND[1] = InpClrTrend2;  CLR_TREND[2] = InpClrTrend3; CLR_TREND[3] = InpClrTrend4;
  }

bool         g_min         = false;     // Panel minimiert?
double       g_last_bid    = 0.0;
string       g_last_cd     = "";
ulong        g_seq         = 0;
int          g_ox          = -100000;   // aktuelle linke Kante des Panels (für Panel_Follow)
int          g_oy          = -100000;   // aktuelle obere Kante des Panels (für Panel_Follow)

//+------------------------------------------------------------------+
//| Hilfsfunktionen                                                  |
//+------------------------------------------------------------------+
string Pad2(const long v)
  {
   return (v < 10 ? "0" : "") + IntegerToString(v);
  }

string NewBase(const string prefix, const string suffix)
  {
   string id;
   do
     {
      g_seq++;
      id = IntegerToString((long)GetTickCount64()) + IntegerToString((long)g_seq);
     }
   while(ObjectFind(0, prefix + id + suffix) >= 0);
   return prefix + id;
  }

int ClampI(const int v, const int lo, const int hi)
  {
   int r = v;
   if(r > hi)
      r = hi;
   if(r < lo)
      r = lo;   // bei zu kleinem Fenster hat der linke/obere Rand Vorrang
   return r;
  }

string BtnName(const string kind, const int idx)
  {
   return NM_BTN + kind + IntegerToString(idx);
  }

//--- Kerzenposition: 0 = aktuelle Kerze, negativ = Vergangenheit, positiv = Zukunft.
//    Damit werden Abstände in Kerzen gerechnet (Wochenenden/Lücken stören nicht).
double BarPos(const datetime t)
  {
   const datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == 0)
      return 0.0;
   if(t >= t0)
      return (double)(t - t0) / PeriodSeconds();
   return -(double)iBarShift(_Symbol, _Period, t, false);
  }

datetime PosToTime(const double pos)
  {
   const datetime t0 = iTime(_Symbol, _Period, 0);
   const int      ps = PeriodSeconds();
   if(pos > 0.0)
      return (datetime)((long)t0 + (long)MathRound(pos * ps));
   const int s = (int)MathRound(-pos);
   const datetime t = iTime(_Symbol, _Period, s);
   if(t != 0)
      return t;
   return (datetime)((long)t0 - (long)s * ps);   // vor der ältesten Kerze: extrapolieren
  }

//+------------------------------------------------------------------+
//| UI-Bausteine                                                     |
//+------------------------------------------------------------------+
void UiRect(const string name, const int x, const int y, const int w, const int h,
            const color bg, const color border)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_COLOR, border);
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 0);
  }

void UiButton(const string name, const int x, const int y, const int w, const int h,
              const color bg, const string text, const string tip)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, C'90,90,90');
   ObjectSetInteger(0, name, OBJPROP_COLOR, clrBlack);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetString(0, name, OBJPROP_FONT, "Arial");
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
   ObjectSetInteger(0, name, OBJPROP_STATE, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 1);
  }

void UiLabel(const string name, const int x, const int y, const string text, const color clr,
             const int size, const string font, const ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetString(0, name, OBJPROP_FONT, font);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 2);
  }

//--- Lage des Panels aus der Fenstergröße berechnen (wird bei jeder Größenänderung neu aufgerufen)
void Panel_Rect(int &ox, int &oy, int &w, int &h)
  {
   const int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   const int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);

   int fx, fy;   // linke obere Ecke des vollständigen Panels
   if(InpPosMode == TP_POSMODE_XY)
     {
      // Prozent des freien Platzes: 0 % = linker/oberer Rand, 100 % = rechter/unterer Rand.
      // Dadurch bleibt die relative Lage beim Vergrößern/Verkleinern gleich und das Panel immer ganz sichtbar.
      const double px = MathMax(0.0, MathMin(100.0, InpPosX)) / 100.0;
      const double py = MathMax(0.0, MathMin(100.0, InpPosY)) / 100.0;
      fx = (int)MathRound((cw - PANEL_W) * px);
      fy = (int)MathRound((ch - PANEL_H) * py);
     }
   else
     {
      // feste Ecke: Abstand zu den beiden Rändern dieser Ecke bleibt bei jeder Fenstergröße gleich
      const bool right  = (InpPosCorner == TP_CORNER_RIGHT_UPPER || InpPosCorner == TP_CORNER_RIGHT_LOWER);
      const bool bottom = (InpPosCorner == TP_CORNER_RIGHT_LOWER || InpPosCorner == TP_CORNER_LEFT_LOWER);
      fx = right  ? cw - PANEL_W - InpPanelX : InpPanelX;
      fy = bottom ? ch - PANEL_H - InpPanelY : InpPanelY;
     }
   fx = ClampI(fx, 0, cw - PANEL_W);
   fy = ClampI(fy, 0, ch - PANEL_H);

   w  = g_min ? MIN_W : PANEL_W;
   h  = g_min ? MIN_H : PANEL_H;
   ox = fx;
   oy = fy;
   if(g_min)   // minimiert: rechter Teil der Titelleiste, die Taste bleibt an derselben Stelle
      ox = ClampI(fx + PANEL_W - MIN_W, 0, cw - MIN_W);
  }

void Title_Update()
  {
   ObjectSetString(0, NM_TITLE, OBJPROP_TEXT, g_min ? g_last_cd : "Trident Panel");
  }

//+------------------------------------------------------------------+
//| Candle-Countdown                                                 |
//+------------------------------------------------------------------+
string Countdown_Text()
  {
   datetime open0 = iTime(_Symbol, _Period, 0);
   if(open0 == 0)
      return "--:--";

   datetime next;
   if(_Period == PERIOD_MN1)
     {
      MqlDateTime dt;
      TimeToStruct(open0, dt);
      dt.mon++;
      if(dt.mon > 12)
        {
         dt.mon = 1;
         dt.year++;
        }
      dt.day = 1;
      dt.hour = 0;
      dt.min = 0;
      dt.sec = 0;
      next = StructToTime(dt);
     }
   else
      next = open0 + PeriodSeconds();

   long left = (long)(next - TimeTradeServer());
   if(left < 0)
      left = 0;

   long days = left / 86400;
   left %= 86400;
   long hh = left / 3600;
   long mm = (left % 3600) / 60;
   long ss = left % 60;

   if(days > 0)
      return IntegerToString(days) + "d " + Pad2(hh) + ":" + Pad2(mm) + ":" + Pad2(ss);
   if(hh > 0)
      return Pad2(hh) + ":" + Pad2(mm) + ":" + Pad2(ss);
   return Pad2(mm) + ":" + Pad2(ss);
  }

void Countdown_Refresh(const bool force)
  {
   string t = Countdown_Text();
   if(!force && t == g_last_cd)
      return;
   g_last_cd = t;
   if(g_min)
      Title_Update();
   else
      ObjectSetString(0, NM_TXT, OBJPROP_TEXT, t);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Panel aufbauen                                                   |
//+------------------------------------------------------------------+
void Panel_Build()
  {
   ObjectsDeleteAll(0, PFX_UI);

   int ox, oy, w, h;
   Panel_Rect(ox, oy, w, h);
   g_ox = ox;
   g_oy = oy;

   UiRect(NM_BG, ox, oy, w, h, C'225,225,225', C'150,150,150');
   UiLabel(NM_TITLE, ox + PAD, oy + 4, "Trident Panel", C'40,40,40', 8, "Arial", ANCHOR_LEFT_UPPER);
   UiButton(NM_MIN, ox + w - PAD - 18, oy + 3, 18, 14, C'200,200,200',
            g_min ? "+" : "_", g_min ? "Panel wiederherstellen" : "Panel minimieren");

   if(!g_min)
     {
      // Gruppe 1: Rechtecke mit Alarm (3 x 2)
      for(int i = 0; i < 6; i++)
         UiButton(BtnName("A", i), ox + GX_ALARM + (i % 3) * (BTN + GAP), oy + (i < 3 ? ROW0 : ROW1),
                  BTN, BTN, CLR_ALARM[i], "", "Rechteck MIT Alarm erzeugen (erscheint sofort im Chart; löst aus, wenn der Preis es berührt)");
      UiRect(NM_SEP1, ox + 91, oy + ROW0, 1, 52, C'160,160,160', C'160,160,160');

      // Gruppe 2: normale Rechtecke (2 x 2)
      for(int i = 0; i < 4; i++)
         UiButton(BtnName("N", i), ox + GX_NORMAL + (i % 2) * (BTN + GAP), oy + (i < 2 ? ROW0 : ROW1),
                  BTN, BTN, CLR_NORMAL[i], "", "Rechteck erzeugen, ohne Alarm (erscheint sofort im Chart)");
      UiRect(NM_SEP2, ox + 154, oy + ROW0, 1, 52, C'160,160,160', C'160,160,160');

      // Gruppe 3: Dreizack (2 x 2)
      for(int i = 0; i < 4; i++)
         UiButton(BtnName("T", i), ox + GX_TRI + (i % 2) * (BTN + GAP), oy + (i < 2 ? ROW0 : ROW1),
                  BTN, BTN, CLR_TRI[i], "", "Dreizack erzeugen (danach A, B und C mit der Maus anpassen)");
      UiRect(NM_SEP3, ox + 217, oy + ROW0, 1, 52, C'160,160,160', C'160,160,160');

      // Gruppe 4: Candle-Timer + Trendlinien
      UiRect(NM_TBG, ox + GX_TIMER, oy + ROW0, GW_TIMER, TIMER_H, C'68,114,196', C'47,82,143');
      UiLabel(NM_TXT, ox + GX_TIMER + GW_TIMER / 2, oy + ROW0 + TIMER_H / 2, "--:--", clrWhite, 14,
              "Arial Bold", ANCHOR_CENTER);
      for(int i = 0; i < 4; i++)
         UiButton(BtnName("L", i), ox + GX_TIMER + i * (TREND_W + GAP), oy + TREND_Y,
                  TREND_W, TREND_H, CLR_TREND[i], "", "Trendlinie erzeugen (erscheint sofort im Chart)");
     }

   Countdown_Refresh(true);
   Title_Update();
  }

// Panel an die aktuelle Fenstergröße anpassen: alle Panel-Objekte um dieselbe Strecke verschieben
void Panel_Follow()
  {
   if(g_ox == -100000)
      return;   // Panel noch nicht aufgebaut
   int ox, oy, w, h;
   Panel_Rect(ox, oy, w, h);
   if(ox == g_ox && oy == g_oy)
      return;
   const int dx = ox - g_ox;
   const int dy = oy - g_oy;
   g_ox = ox;
   g_oy = oy;
   for(int i = ObjectsTotal(0, 0) - 1; i >= 0; i--)
     {
      const string nm = ObjectName(0, i, 0);
      if(StringFind(nm, PFX_UI) != 0)
         continue;
      if(dx != 0)
         ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, ObjectGetInteger(0, nm, OBJPROP_XDISTANCE) + dx);
      if(dy != 0)
         ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, ObjectGetInteger(0, nm, OBJPROP_YDISTANCE) + dy);
     }
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Zustand "minimiert" über Neustart / Zeitrahmenwechsel merken      |
//+------------------------------------------------------------------+
bool LoadMinState()
  {
   return (ObjectFind(0, NM_STATE) >= 0 && ObjectGetString(0, NM_STATE, OBJPROP_TEXT) == "1");
  }

void SaveMinState()
  {
   if(ObjectFind(0, NM_STATE) < 0)
     {
      if(!ObjectCreate(0, NM_STATE, OBJ_LABEL, 0, 0, 0))
         return;
      ObjectSetInteger(0, NM_STATE, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);
      ObjectSetInteger(0, NM_STATE, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, NM_STATE, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, NM_STATE, OBJPROP_TEXT, g_min ? "1" : "0");
  }

//+------------------------------------------------------------------+
//| Zeichen-Objekte                                                  |
//+------------------------------------------------------------------+
void CreateRect(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
                const color clr, const bool alarm)
  {
   if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2))
      return;
   const bool fill = alarm ? InpFillAlarm : InpFillNormal;
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, InpRectWidth);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
   ObjectSetInteger(0, name, OBJPROP_BACK, fill);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, true);   // Anfasser sofort sichtbar
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, alarm ? TT_ALARM_ON : "Rechteck");
  }

// Grüne Zone des Dreizacks anlegen bzw. verschieben (auswählbar: rechten Rand ziehen)
void PutRect(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
             const color clr, const ENUM_LINE_STYLE style)
  {
   if(ObjectFind(0, name) < 0)
     {
      if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2))
         return;
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_FILL, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTED, false);
     }
   else
     {
      ObjectMove(0, name, 0, t1, p1);
      ObjectMove(0, name, 1, t2, p2);
     }
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 0);   // A-B und B-C haben beim Anklicken Vorrang
   ObjectSetString(0, name, OBJPROP_TOOLTIP, "Grüne Zone: rechten Rand ziehen, um sie zu verlängern");
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
  }

// Trendlinie anlegen bzw. verschieben
void PutTrend(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
              const color clr, const int width, const bool ray, const bool selectable, const bool hidden)
  {
   if(ObjectFind(0, name) < 0)
     {
      if(!ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2))
         return;
      ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, selectable);
      ObjectSetInteger(0, name, OBJPROP_SELECTED, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, hidden);
     }
   else
     {
      ObjectMove(0, name, 0, t1, p1);
      ObjectMove(0, name, 1, t2, p2);
     }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, ray);
  }

void PutText(const string name, const datetime t, const double p, const string text, const color clr,
             const int size, const string font, const ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
     {
      if(!ObjectCreate(0, name, OBJ_TEXT, 0, t, p))
         return;
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   else
      ObjectMove(0, name, 0, t, p);
   ObjectSetString(0, name, OBJPROP_FONT, font);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
  }

//+------------------------------------------------------------------+
//| Dreizack (Vorlage: Screenshot des Originals, auf 1 px genau)     |
//|                                                                  |
//|  A-B  Impuls L (Start -> Extrempunkt), Mittelpunkt bei 50 %      |
//|  B-C  Rücksetzer R; C liegt standardmäßig 3 Impulsbreiten hinter |
//|       B auf 50 % der Impulshöhe                                  |
//|  linke Zinke     B+L     -> B+2L                                 |
//|  mittlere Zinke  C       -> C+2L                                 |
//|  rechte Zinke    B+L+2R  -> B+2L+2R                              |
//|  Diagonale       B+L     -> B+L+2R                               |
//|  grüne Zone: links an A, Höhe A bis C, Breite per Maus ziehbar   |
//|  Info-Text am Extrempunkt: Kerzen/Punkte des Impulses            |
//|                                                                  |
//|  Masterobjekte (auswählbar): <base>_AB und <base>_BC.            |
//|  Alles andere wird bei jedem Verschieben daraus neu berechnet.   |
//|  Gespeichert wird nur die Lage von C relativ zum Impuls          |
//|  (rt = Zeitversatz / Impulsbreite, rp = Preisversatz / Höhe)     |
//|  und die Breite der grünen Zone in Kerzen (bw).                  |
//+------------------------------------------------------------------+
void Trident_LoadState(const string base, double &rt, double &rp, double &bw)
  {
   rt = 3.0;
   rp = -0.5;
   bw = MathMax(1, InpBoxBars);
   const string nm = base + "_S";
   if(ObjectFind(0, nm) < 0)
      return;
   const string s  = ObjectGetString(0, nm, OBJPROP_TEXT);
   const int    k1 = StringFind(s, ";");
   if(k1 <= 0)
      return;
   const int    k2 = StringFind(s, ";", k1 + 1);
   rt = StringToDouble(StringSubstr(s, 0, k1));
   if(k2 < 0)
      rp = StringToDouble(StringSubstr(s, k1 + 1));
   else
     {
      rp = StringToDouble(StringSubstr(s, k1 + 1, k2 - k1 - 1));
      bw = StringToDouble(StringSubstr(s, k2 + 1));
     }
   if(bw < 1.0)
      bw = 1.0;
  }

void Trident_SaveState(const string base, const double rt, const double rp, const double bw)
  {
   const string nm = base + "_S";
   if(ObjectFind(0, nm) < 0)
     {
      if(!ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0))
         return;
      ObjectSetInteger(0, nm, OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS);   // unsichtbar
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, nm, OBJPROP_TEXT,
                   DoubleToString(rt, 6) + ";" + DoubleToString(rp, 6) + ";" + DoubleToString(bw, 3));
  }

// Waagrechte Ziellinie (optional) mit Nummer am rechten Ende
void Trident_Level(const string base, const int k, const double x, const double p, const color clr)
  {
   const string sk = IntegerToString(k);
   const datetime t1 = PosToTime(x);
   const datetime t2 = PosToTime(x + InpLevelBars);
   PutTrend(base + "_L" + sk, t1, p, t2, p, clr, InpLevelWidth, false, false, true);
   PutText(base + "_T" + sk, t2, p, sk, clr, 10, "Arial Bold", ANCHOR_LEFT);
   ObjectSetString(0, base + "_L" + sk, OBJPROP_TOOLTIP, "Ziel " + sk + ": " + DoubleToString(p, _Digits));
  }

// cFromObject   = true : Lage von C aus dem Objekt <base>_BC lesen (C wurde gezogen / Neuaufbau)
//               = false: Lage von C aus dem gespeicherten Verhältnis (A oder B wurden gezogen)
// boxFromObject = true : Breite der grünen Zone aus dem Objekt <base>_BX lesen (Zone wurde gezogen)
void Trident_Rebuild(const string base, const bool cFromObject, const bool boxFromObject)
  {
   const string ab = base + "_AB";
   const string bc = base + "_BC";
   const string bx = base + "_BX";
   if(ObjectFind(0, ab) < 0)
      return;

   const color clr = (color)ObjectGetInteger(0, ab, OBJPROP_COLOR);
   double xa = BarPos((datetime)ObjectGetInteger(0, ab, OBJPROP_TIME, 0));
   double pa = ObjectGetDouble(0, ab, OBJPROP_PRICE, 0);
   double xb = BarPos((datetime)ObjectGetInteger(0, ab, OBJPROP_TIME, 1));
   double pb = ObjectGetDouble(0, ab, OBJPROP_PRICE, 1);
   if(xb < xa)   // B soll zeitlich hinter A liegen
     {
      double tx = xa;
      xa = xb;
      xb = tx;
      double tp = pa;
      pa = pb;
      pb = tp;
     }

   double d = xb - xa;           // Impulsbreite in Kerzen
   if(d < 1.0)
      d = 1.0;
   const double H = pb - pa;     // Impulshöhe (mit Vorzeichen)

   double rt, rp, bw;
   Trident_LoadState(base, rt, rp, bw);
   if(cFromObject && ObjectFind(0, bc) >= 0)
     {
      const double xc0 = BarPos((datetime)ObjectGetInteger(0, bc, OBJPROP_TIME, 1));
      const double pc0 = ObjectGetDouble(0, bc, OBJPROP_PRICE, 1);
      rt = (xc0 - xb) / d;
      if(MathAbs(H) >= _Point)
         rp = (pc0 - pb) / H;
     }
   if(boxFromObject && ObjectFind(0, bx) >= 0)
     {
      // rechter Rand der Zone (egal ob der Rand gezogen oder das ganze Rechteck verschoben wurde)
      const double x1 = BarPos((datetime)ObjectGetInteger(0, bx, OBJPROP_TIME, 0));
      const double x2 = BarPos((datetime)ObjectGetInteger(0, bx, OBJPROP_TIME, 1));
      bw = MathMax(x1, x2) - xa;
      if(bw < 1.0)
         bw = 1.0;
     }
   Trident_SaveState(base, rt, rp, bw);

   const double e  = rt * d;     // C relativ zu B: Zeit (Kerzen)
   const double r  = rp * H;     // C relativ zu B: Preis
   const double xc = xb + e;
   const double pc = pb + r;

   // Rücksetzer B-C (Masterobjekt); A-B und B-C haben beim Anklicken Vorrang vor der Zone
   PutTrend(bc, PosToTime(xb), pb, PosToTime(xc), pc, clr, InpTridentWidth, false, true, false);
   ObjectSetInteger(0, ab, OBJPROP_ZORDER, 5);
   ObjectSetInteger(0, bc, OBJPROP_ZORDER, 5);

   // Zinken und Diagonale
   PutTrend(base + "_PA", PosToTime(xb + d), pb + H, PosToTime(xb + 2 * d), pb + 2 * H,
            clr, InpTridentWidth, false, false, true);                               // links:  B+L -> B+2L
   PutTrend(base + "_PB", PosToTime(xc), pc, PosToTime(xc + 2 * d), pc + 2 * H,
            clr, InpTridentWidth, false, false, true);                               // Mitte:  C -> C+2L
   PutTrend(base + "_PC", PosToTime(xb + d + 2 * e), pb + H + 2 * r,
            PosToTime(xb + 2 * d + 2 * e), pb + 2 * H + 2 * r,
            clr, InpTridentWidth, false, false, true);                               // rechts: B+L+2R -> B+2L+2R
   PutTrend(base + "_DG", PosToTime(xb + d), pb + H, PosToTime(xb + d + 2 * e), pb + H + 2 * r,
            clr, InpTridentWidth, false, false, true);                               // Diagonale

   // Grüne Zone: links an A, Höhe A bis C, Breite bw (per Maus ziehbar)
   if(InpShowBox)
      PutRect(bx, PosToTime(xa), pa, PosToTime(xa + bw), pc, InpBoxColor, STYLE_DASH);
   else
      ObjectDelete(0, bx);

   // Info-Text "Kerzen/Punkte" am Extrempunkt
   if(InpShowInfo)
     {
      const long bars = (long)MathRound(xb - xa);
      const long pts  = (long)MathRound(MathAbs(H) / _Point);
      PutText(base + "_I", PosToTime(xb), pb, IntegerToString(bars) + "/" + IntegerToString(pts), clr, 8,
              "Arial", (H >= 0 ? ANCHOR_LOWER : ANCHOR_UPPER));
     }
   else
      ObjectDelete(0, base + "_I");

   // Optionale Ziellinien: 1 = niedrigstes Ziel (rechte Zinke), 3 = höchstes (linke Zinke)
   if(InpShowLevels)
     {
      Trident_Level(base, 1, xb + 2 * d + 2 * e, pb + 2 * H + 2 * r, clr);
      Trident_Level(base, 2, xc + 2 * d, pc + 2 * H, clr);
      Trident_Level(base, 3, xb + 2 * d, pb + 2 * H, clr);
     }
   else
      for(int k = 1; k <= 3; k++)
        {
         ObjectDelete(0, base + "_L" + IntegerToString(k));
         ObjectDelete(0, base + "_T" + IntegerToString(k));
        }

   // Reste der Vorgängerversion (Zinken _P1.._P3) entfernen
   for(int k = 1; k <= 3; k++)
      ObjectDelete(0, base + "_P" + IntegerToString(k));
  }

void Trident_RefreshAll()
  {
   string list[];
   int    n = 0;
   for(int i = ObjectsTotal(0, 0, OBJ_TREND) - 1; i >= 0; i--)
     {
      string nm = ObjectName(0, i, 0, OBJ_TREND);
      int    L  = StringLen(nm);
      if(StringFind(nm, PFX_TRI) == 0 && L > 3 && StringSubstr(nm, L - 3) == "_AB")
        {
         ArrayResize(list, n + 1);
         list[n++] = StringSubstr(nm, 0, L - 3);
        }
     }
   for(int i = 0; i < n; i++)
      Trident_Rebuild(list[i], true, true);   // C und Zone bleiben, wo sie sind; nur Kerzenzahl/Längen werden aktualisiert
  }

// Dreizack sofort im sichtbaren Chartbereich erzeugen; Punkte A, B, C sind ausgewählt
void Trident_Create(const int idx)
  {
   const int w = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   const int h = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   int hpx = MathMin(InpTridentHeight, h / 5);
   if(hpx < 20)
      hpx = 20;
   const int xa = (int)(w * 0.35);
   const int ya = (int)(h * 0.75);

   int      sub;
   datetime ta, tdummy;
   double   pa, pb;
   if(!ChartXYToTimePrice(0, xa, ya, sub, ta, pa) || sub != 0)
      return;
   if(!ChartXYToTimePrice(0, xa, ya - hpx, sub, tdummy, pb))
      return;

   const double xA   = BarPos(ta);
   const string base = NewBase(PFX_TRI, "_AB");
   PutTrend(base + "_AB", PosToTime(xA), pa, PosToTime(xA + MathMax(1, InpTridentBars)), pb,
            CLR_TRI[idx], InpTridentWidth, false, true, false);
   Trident_SaveState(base, 3.0, -0.5, MathMax(1, InpBoxBars));
   Trident_Rebuild(base, false, false);
   ObjectSetInteger(0, base + "_AB", OBJPROP_SELECTED, true);   // Anfasser sofort sichtbar
   ObjectSetInteger(0, base + "_BC", OBJPROP_SELECTED, true);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Rechtecke und Trendlinien sofort im sichtbaren Chart erzeugen     |
//| (wie der Dreizack: ausgewählt, danach mit der Maus anpassen)      |
//+------------------------------------------------------------------+
bool ChartPoint(const int x, const int y, datetime &t, double &p)
  {
   int sub;
   return (ChartXYToTimePrice(0, x, y, sub, t, p) && sub == 0);
  }

void Rect_Create(const bool alarm, const int idx)
  {
   const int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   const int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   int hpx = MathMin(InpRectHeight, ch / 3);
   if(hpx < 10)
      hpx = 10;
   const int x  = (int)(cw * 0.45);
   const int y1 = ch / 2 - hpx / 2;   // senkrecht mittig im Chart

   datetime t1, tdummy;
   double   p1, p2;
   if(!ChartPoint(x, y1, t1, p1) || !ChartPoint(x, y1 + hpx, tdummy, p2))
      return;
   const double x1   = BarPos(t1);
   const string name = NewBase(alarm ? PFX_ALARM : PFX_RECT, "");
   CreateRect(name, PosToTime(x1), p1, PosToTime(x1 + MathMax(1, InpRectBars)), p2,
              alarm ? CLR_ALARM[idx] : CLR_NORMAL[idx], alarm);
  }

void Trend_Create(const int idx)
  {
   const int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   const int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   int rise = InpTrendRise;
   if(rise > ch / 3)
      rise = ch / 3;
   if(rise < -ch / 3)
      rise = -ch / 3;
   const int x  = (int)(cw * 0.40);
   const int y1 = (int)(ch * 0.40) + rise / 2;   // Startpunkt; Endpunkt liegt "rise" Pixel höher

   datetime t1, tdummy;
   double   p1, p2;
   if(!ChartPoint(x, y1, t1, p1) || !ChartPoint(x, y1 - rise, tdummy, p2))
      return;
   const double x1   = BarPos(t1);
   const string name = NewBase(PFX_TREND, "");
   PutTrend(name, PosToTime(x1), p1, PosToTime(x1 + MathMax(1, InpTrendBars)), p2,
            CLR_TREND[idx], InpTrendWidth, InpTrendRay, true, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, true);   // Anfasser sofort sichtbar
   ObjectSetString(0, name, OBJPROP_TOOLTIP, "Trendlinie");
  }

void OnPanelObject(const string name)
  {
   string s = StringSubstr(name, StringLen(PFX_UI));
   if(s == "MIN")
     {
      g_min = !g_min;
      SaveMinState();
      Panel_Build();
      ChartRedraw();
      return;
     }
   if(StringSubstr(s, 0, 4) != "BTN_")
      return;
   ObjectSetInteger(0, name, OBJPROP_STATE, false);   // Taste springt sofort wieder heraus

   const string kind = StringSubstr(s, 4, 1);
   const int    idx  = (int)StringToInteger(StringSubstr(s, 5));
   if(kind == "A" && idx >= 0 && idx < 6)
      Rect_Create(true, idx);
   else if(kind == "N" && idx >= 0 && idx < 4)
      Rect_Create(false, idx);
   else if(kind == "T" && idx >= 0 && idx < 4)
      Trident_Create(idx);
   else if(kind == "L" && idx >= 0 && idx < 4)
      Trend_Create(idx);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Alarm (nur Objekte mit Präfix TP_ALR_)                            |
//+------------------------------------------------------------------+
void FireAlarm(const string name, const double bid, const double zl, const double zh)
  {
   string tf  = StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period), 7);
   string msg = _Symbol + " " + tf + ": Preis " + DoubleToString(bid, _Digits) +
                " hat Alarm-Rechteck erreicht (" + DoubleToString(zl, _Digits) + " - " +
                DoubleToString(zh, _Digits) + ")";
   Print(msg);
   if(InpAlarmPopup)
      Alert(msg);
   if(InpAlarmSound)
      PlaySound(InpAlarmSoundFile);
   if(InpAlarmPush)
      SendNotification(msg);

   if(InpAlarmOnce)
     {
      ObjectSetString(0, name, OBJPROP_TOOLTIP, TT_ALARM_OFF);
      ObjectSetInteger(0, name, OBJPROP_FILL, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
     }
  }

void CheckAlarms()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      bid = SymbolInfoDouble(_Symbol, SYMBOL_LAST);
   if(bid <= 0.0)
      return;
   if(g_last_bid <= 0.0)
     {
      g_last_bid = bid;
      return;
     }

   const double   prev = g_last_bid;
   const double   lo   = MathMin(prev, bid);
   const double   hi   = MathMax(prev, bid);
   const datetime now  = TimeTradeServer();
   g_last_bid = bid;

   for(int i = ObjectsTotal(0, 0, OBJ_RECTANGLE) - 1; i >= 0; i--)
     {
      string name = ObjectName(0, i, 0, OBJ_RECTANGLE);
      if(StringFind(name, PFX_ALARM) != 0)
         continue;   // nur echte Alarm-Rechtecke, alle anderen Rechtecke ignorieren
      if(InpAlarmOnce && ObjectGetString(0, name, OBJPROP_TOOLTIP) == TT_ALARM_OFF)
         continue;

      double zl = MathMin(ObjectGetDouble(0, name, OBJPROP_PRICE, 0), ObjectGetDouble(0, name, OBJPROP_PRICE, 1));
      double zh = MathMax(ObjectGetDouble(0, name, OBJPROP_PRICE, 0), ObjectGetDouble(0, name, OBJPROP_PRICE, 1));

      if(InpAlarmTimeRange)
        {
         datetime t1 = (datetime)ObjectGetInteger(0, name, OBJPROP_TIME, 0);
         datetime t2 = (datetime)ObjectGetInteger(0, name, OBJPROP_TIME, 1);
         if(now < MathMin(t1, t2) || now > MathMax(t1, t2))
            continue;
        }

      const bool touching    = (hi >= zl && lo <= zh);       // Preisweg seit dem letzten Check berührt die Zone
      const bool wasOutside  = (prev < zl || prev > zh);     // vorher außerhalb -> "Eintritt"
      if(touching && wasOutside)
         FireAlarm(name, bid, zl, zh);
     }
  }

//+------------------------------------------------------------------+
//| Indikator-Events                                                 |
//+------------------------------------------------------------------+
int OnInit()
  {
   Colors_Init();
   g_min = LoadMinState();
   ChartSetInteger(0, CHART_EVENT_OBJECT_DELETE, true);
   Panel_Build();
   Trident_RefreshAll();
   EventSetMillisecondTimer(250);
   ChartRedraw();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, PFX_UI);
   if(reason == REASON_REMOVE)
      ObjectDelete(0, NM_STATE);
   ChartRedraw();
  }

void OnTimer()
  {
   Panel_Follow();     // falls ein Größen-Ereignis ausgeblieben ist
   Countdown_Refresh(false);
   CheckAlarms();
  }

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
  {
   CheckAlarms();
   return rates_total;
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id == CHARTEVENT_OBJECT_CLICK)
     {
      if(StringFind(sparam, PFX_UI) == 0)
         OnPanelObject(sparam);
     }
   else if(id == CHARTEVENT_CHART_CHANGE)
      Panel_Follow();   // Fenster wurde größer/kleiner: Panel behält seine Position
   else if(id == CHARTEVENT_OBJECT_DRAG || id == CHARTEVENT_OBJECT_CHANGE)
     {
      int L = StringLen(sparam);
      if(StringFind(sparam, PFX_TRI) == 0 && L > 3)
        {
         string suf  = StringSubstr(sparam, L - 3);
         string base = StringSubstr(sparam, 0, L - 3);
         if(suf == "_AB")
           {
            Trident_Rebuild(base, false, false);   // A oder B (oder die ganze Linie) bewegt: C folgt dem Verhältnis
            ChartRedraw();
           }
         else if(suf == "_BC")
           {
            Trident_Rebuild(base, true, false);    // C bewegt: neue Lage von C übernehmen
            ChartRedraw();
           }
         else if(suf == "_BX")
           {
            Trident_Rebuild(base, false, true);    // grüne Zone gezogen: neue Breite übernehmen
            ChartRedraw();
           }
        }
     }
   else if(id == CHARTEVENT_OBJECT_DELETE)
     {
      int L = StringLen(sparam);
      if(StringFind(sparam, PFX_TRI) == 0 && L > 3)
        {
         string suf = StringSubstr(sparam, L - 3);
         if(suf == "_AB" || suf == "_BC")   // Hauptlinie gelöscht -> ganzen Dreizack entfernen
            ObjectsDeleteAll(0, StringSubstr(sparam, 0, L - 3) + "_");
        }
     }
  }
//+------------------------------------------------------------------+
