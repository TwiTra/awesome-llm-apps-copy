//+------------------------------------------------------------------+
//|                                                 TridentPanel.mq5 |
//|  Zeichen-Panel: Rechtecke (normal / mit Alarm), Dreizack,        |
//|  Trendlinien und Candle-Countdown mit Minimieren-Taste.          |
//+------------------------------------------------------------------+
#property copyright   "TridentPanel"
#property version     "1.00"
#property description "Panel mit Rechtecken (normal / mit Alarm), Dreizack, Trendlinien und Candle-Countdown"
#property indicator_chart_window
#property indicator_plots 0

//--- Eingaben -------------------------------------------------------
input group "Panel"
input int    InpPanelX           = 10;           // Abstand von links (px)
input int    InpPanelY           = 25;           // Abstand von oben (px)

input group "Rechtecke"
input int    InpRectWidth        = 1;            // Rahmenbreite
input bool   InpFillAlarm        = true;         // Alarm-Rechtecke ausfüllen
input bool   InpFillNormal       = false;        // Normale Rechtecke ausfüllen

input group "Alarm (gilt nur für Alarm-Rechtecke)"
input bool   InpAlarmPopup       = true;         // Popup-Fenster (Alert)
input bool   InpAlarmSound       = false;        // Zusätzlich eigene Sound-Datei abspielen
input string InpAlarmSoundFile   = "alert2.wav"; // Sound-Datei (Ordner MQL5\Sounds bzw. Sounds)
input bool   InpAlarmPush        = false;        // Push-Nachricht aufs Handy
input bool   InpAlarmOnce        = true;         // Nur einmal auslösen (danach Rechteck gestrichelt)
input bool   InpAlarmTimeRange   = false;        // Nur auslösen, solange die Zeit im Rechteck liegt

input group "Dreizack"
input double InpLevel1           = 1.0;          // Ziel 1 (x Impulshöhe ab Extrempunkt)
input double InpLevel2           = 1.5;          // Ziel 2 (x Impulshöhe ab Extrempunkt)
input double InpLevel3           = 2.0;          // Ziel 3 (x Impulshöhe ab Extrempunkt)
input int    InpLevelBars        = 100;          // Länge der Ziellinien (Kerzen)
input int    InpTridentWidth     = 1;            // Linienbreite Dreizack
input int    InpLevelWidth       = 2;            // Linienbreite Ziellinien
input bool   InpShowInfo         = true;         // Info-Text "Kerzen/Punkte" am Extrempunkt

input group "Trendlinien"
input int    InpTrendWidth       = 1;            // Linienbreite
input bool   InpTrendRay         = false;        // Strahl nach rechts

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

#define TXT_ALARM_ON   "Alarm: aktiv"
#define TXT_ALARM_OFF  "Alarm: ausgelöst"

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

//--- Farben (Vorlage aus der Skizze) --------------------------------
color CLR_ALARM[6]  = { C'112,173,71', C'91,155,213', C'237,125,49', C'255,192,0', C'255,0,0', C'112,48,160' };
color CLR_NORMAL[4] = { C'91,155,213', C'146,208,80', C'244,177,131', C'190,90,240' };
color CLR_TRI[4]    = { C'91,155,213', C'112,173,71', C'255,192,110', C'190,90,240' };
color CLR_TREND[4]  = { C'91,155,213', C'112,173,71', C'237,125,49', C'190,90,240' };

//--- Zeichenmodus ---------------------------------------------------
enum ENUM_TP_MODE { TP_NONE = 0, TP_RECT_ALARM, TP_RECT_NORMAL, TP_TRIDENT, TP_TREND };

bool         g_min         = false;     // Panel minimiert?
ENUM_TP_MODE g_mode        = TP_NONE;   // aktive Zeichentaste
int          g_var         = -1;        // Index der aktiven Taste
int          g_step        = 0;         // 0 = wartet auf 1. Klick, 1 = wartet auf 2. Klick
datetime     g_t1          = 0;
double       g_p1          = 0.0;
string       g_obj         = "";        // Vorschau-/Hauptobjekt während des Zeichnens
string       g_base        = "";        // Dreizack: Basisname
bool         g_mouse_saved = false;
long         g_mouse_prev  = 0;
double       g_last_bid    = 0.0;
string       g_last_cd     = "";
ulong        g_seq         = 0;

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

string ModeKind(const ENUM_TP_MODE m)
  {
   if(m == TP_RECT_ALARM)  return "A";
   if(m == TP_RECT_NORMAL) return "N";
   if(m == TP_TRIDENT)     return "T";
   if(m == TP_TREND)       return "L";
   return "";
  }

ENUM_TP_MODE KindToMode(const string k)
  {
   if(k == "A") return TP_RECT_ALARM;
   if(k == "N") return TP_RECT_NORMAL;
   if(k == "T") return TP_TRIDENT;
   if(k == "L") return TP_TREND;
   return TP_NONE;
  }

string BtnName(const string kind, const int idx)
  {
   return NM_BTN + kind + IntegerToString(idx);
  }

double LevelMult(const int k)
  {
   if(k == 1) return InpLevel1;
   if(k == 2) return InpLevel2;
   return InpLevel3;
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

void Panel_Rect(int &ox, int &oy, int &w, int &h)
  {
   w  = g_min ? MIN_W : PANEL_W;
   h  = g_min ? MIN_H : PANEL_H;
   ox = InpPanelX + (g_min ? PANEL_W - MIN_W : 0);   // minimiert: Taste bleibt an derselben Stelle
   oy = InpPanelY;
  }

bool InPanel(const int x, const int y)
  {
   int ox, oy, w, h;
   Panel_Rect(ox, oy, w, h);
   return (x >= ox && x <= ox + w && y >= oy && y <= oy + h);
  }

string StatusText()
  {
   string n = IntegerToString(g_step + 1) + "/2";
   if(g_mode == TP_RECT_ALARM)  return "Alarm-Rechteck: Klick " + n + "  (ESC = Abbruch)";
   if(g_mode == TP_RECT_NORMAL) return "Rechteck: Klick " + n + "  (ESC = Abbruch)";
   if(g_mode == TP_TRIDENT)
      return (g_step == 0 ? "Dreizack: Startpunkt klicken (ESC = Abbruch)"
                          : "Dreizack: Extrempunkt klicken (ESC = Abbruch)");
   if(g_mode == TP_TREND)       return "Trendlinie: Klick " + n + "  (ESC = Abbruch)";
   return "Trident Panel";
  }

void Title_Update()
  {
   string s = g_min ? g_last_cd : StatusText();
   ObjectSetString(0, NM_TITLE, OBJPROP_TEXT, s);
  }

void Buttons_Refresh()
  {
   if(g_min)
      return;
   string kinds[4] = { "A", "N", "T", "L" };
   int    counts[4] = { 6, 4, 4, 4 };
   for(int k = 0; k < 4; k++)
      for(int i = 0; i < counts[k]; i++)
        {
         string nm = BtnName(kinds[k], i);
         bool   on = (g_mode != TP_NONE && kinds[k] == ModeKind(g_mode) && i == g_var);
         ObjectSetInteger(0, nm, OBJPROP_STATE, on);
         ObjectSetInteger(0, nm, OBJPROP_BORDER_COLOR, on ? C'220,0,0' : C'90,90,90');
        }
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

   UiRect(NM_BG, ox, oy, w, h, C'225,225,225', C'150,150,150');
   UiLabel(NM_TITLE, ox + PAD, oy + 4, "Trident Panel", C'40,40,40', 8, "Arial", ANCHOR_LEFT_UPPER);
   UiButton(NM_MIN, ox + w - PAD - 18, oy + 3, 18, 14, C'200,200,200',
            g_min ? "+" : "_", g_min ? "Panel wiederherstellen" : "Panel minimieren");

   if(!g_min)
     {
      // Gruppe 1: Rechtecke mit Alarm (3 x 2)
      for(int i = 0; i < 6; i++)
         UiButton(BtnName("A", i), ox + GX_ALARM + (i % 3) * (BTN + GAP), oy + (i < 3 ? ROW0 : ROW1),
                  BTN, BTN, CLR_ALARM[i], "", "Rechteck MIT Alarm (löst aus, wenn der Preis das Rechteck berührt)");
      UiRect(NM_SEP1, ox + 91, oy + ROW0, 1, 52, C'160,160,160', C'160,160,160');

      // Gruppe 2: normale Rechtecke (2 x 2)
      for(int i = 0; i < 4; i++)
         UiButton(BtnName("N", i), ox + GX_NORMAL + (i % 2) * (BTN + GAP), oy + (i < 2 ? ROW0 : ROW1),
                  BTN, BTN, CLR_NORMAL[i], "", "Rechteck normal (ohne Alarm)");
      UiRect(NM_SEP2, ox + 154, oy + ROW0, 1, 52, C'160,160,160', C'160,160,160');

      // Gruppe 3: Dreizack (2 x 2)
      for(int i = 0; i < 4; i++)
         UiButton(BtnName("T", i), ox + GX_TRI + (i % 2) * (BTN + GAP), oy + (i < 2 ? ROW0 : ROW1),
                  BTN, BTN, CLR_TRI[i], "", "Dreizack: 1. Klick = Start, 2. Klick = Extrempunkt");
      UiRect(NM_SEP3, ox + 217, oy + ROW0, 1, 52, C'160,160,160', C'160,160,160');

      // Gruppe 4: Candle-Timer + Trendlinien
      UiRect(NM_TBG, ox + GX_TIMER, oy + ROW0, GW_TIMER, TIMER_H, C'68,114,196', C'47,82,143');
      UiLabel(NM_TXT, ox + GX_TIMER + GW_TIMER / 2, oy + ROW0 + TIMER_H / 2, "--:--", clrWhite, 14,
              "Arial Bold", ANCHOR_CENTER);
      for(int i = 0; i < 4; i++)
         UiButton(BtnName("L", i), ox + GX_TIMER + i * (TREND_W + GAP), oy + TREND_Y,
                  TREND_W, TREND_H, CLR_TREND[i], "", "Trendlinie");
     }

   Countdown_Refresh(true);
   Buttons_Refresh();
   Title_Update();
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
void CreateRect(const string name, const datetime t, const double p, const color clr, const bool alarm)
  {
   if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t, p, t, p))
      return;
   const bool fill = alarm ? InpFillAlarm : InpFillNormal;
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, InpRectWidth);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
   ObjectSetInteger(0, name, OBJPROP_BACK, fill);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
   if(alarm)
     {
      ObjectSetString(0, name, OBJPROP_TEXT, TXT_ALARM_ON);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, "Alarm-Rechteck");
     }
   else
      ObjectSetString(0, name, OBJPROP_TOOLTIP, "Rechteck");
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
             const int size, const ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
     {
      if(!ObjectCreate(0, name, OBJ_TEXT, 0, t, p))
         return;
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_FONT, "Arial Bold");
     }
   else
      ObjectMove(0, name, 0, t, p);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
  }

//+------------------------------------------------------------------+
//| Dreizack                                                         |
//|  A-B  = Impuls (Start -> Extrempunkt), Mittelpunkt = 50 %        |
//|  B-C  = Rücksetzer auf 50 % (C rastet auf 50 % ein, Zeit frei)   |
//|  P1-3 = drei Zinken (verschobene Kopien des Impulses A-B)        |
//|  L1-3 = Ziellinien bei B + 1,0 / 1,5 / 2,0 x Impulshöhe          |
//+------------------------------------------------------------------+
void Trident_Rebuild(const string base)
  {
   const string ab = base + "_AB";
   const string bc = base + "_BC";
   if(ObjectFind(0, ab) < 0)
      return;

   color    clr = (color)ObjectGetInteger(0, ab, OBJPROP_COLOR);
   datetime ta  = (datetime)ObjectGetInteger(0, ab, OBJPROP_TIME, 0);
   double   pa  = ObjectGetDouble(0, ab, OBJPROP_PRICE, 0);
   datetime tb  = (datetime)ObjectGetInteger(0, ab, OBJPROP_TIME, 1);
   double   pb  = ObjectGetDouble(0, ab, OBJPROP_PRICE, 1);
   if(tb < ta)   // B soll zeitlich hinter A liegen
     {
      datetime tt = ta;
      ta = tb;
      tb = tt;
      double pp = pa;
      pa = pb;
      pb = pp;
     }

   const int ps = PeriodSeconds();
   long d = (long)(tb - ta);          // Dauer des Impulses in Sekunden
   if(d < ps)
      d = ps;
   const double H  = pb - pa;         // Impulshöhe (mit Vorzeichen)
   const double pc = pa + 0.5 * H;    // 50 %-Rücksetzer

   datetime tc = (datetime)(tb + d);  // Standard: Spiegelung der Impulsdauer
   if(ObjectFind(0, bc) >= 0)
     {
      datetime tcu = (datetime)ObjectGetInteger(0, bc, OBJPROP_TIME, 1);
      if(tcu > tb)
         tc = tcu;
     }
   PutTrend(bc, tb, pb, tc, pc, clr, InpTridentWidth, false, true, false);

   for(int k = 1; k <= 3; k++)
     {
      const double m    = LevelMult(k);
      const string sk   = IntegerToString(k);
      datetime     tbot = (datetime)(tc + (3 - k) * d);
      datetime     ttop = (datetime)(tbot + d);
      double       pbot = pb + (m - 1.0) * H;
      double       ptop = pb + m * H;
      datetime     tend = (datetime)(ttop + (long)InpLevelBars * ps);

      PutTrend(base + "_P" + sk, tbot, pbot, ttop, ptop, clr, InpTridentWidth, false, false, true);
      PutTrend(base + "_L" + sk, ttop, ptop, tend, ptop, clr, InpLevelWidth, false, false, true);
      PutText(base + "_T" + sk, tend, ptop, sk, clr, 10, ANCHOR_LEFT);
      ObjectSetString(0, base + "_L" + sk, OBJPROP_TOOLTIP,
                      "Ziel " + sk + " (" + DoubleToString(m, 2) + " x Impuls): " + DoubleToString(ptop, _Digits));
     }

   if(InpShowInfo)
     {
      int b1   = iBarShift(_Symbol, _Period, ta, false);
      int b2   = iBarShift(_Symbol, _Period, tb, false);
      int bars = (b1 > b2 ? b1 - b2 : b2 - b1);
      long pts = (long)MathRound(MathAbs(H) / _Point);
      PutText(base + "_I", tb, pb, IntegerToString(bars) + "/" + IntegerToString(pts), clr, 8,
              (H >= 0 ? ANCHOR_LOWER : ANCHOR_UPPER));
     }
   else
      ObjectDelete(0, base + "_I");
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
      Trident_Rebuild(list[i]);
  }

//+------------------------------------------------------------------+
//| Zeichenmodus                                                     |
//+------------------------------------------------------------------+
void Cancel()
  {
   if(g_step == 1 && g_obj != "")
     {
      if(g_mode == TP_TRIDENT)
         ObjectsDeleteAll(0, g_base + "_");
      else
         ObjectDelete(0, g_obj);
     }
   g_mode = TP_NONE;
   g_var  = -1;
   g_step = 0;
   g_obj  = "";
   g_base = "";
   if(g_mouse_saved)
     {
      ChartSetInteger(0, CHART_EVENT_MOUSE_MOVE, g_mouse_prev);
      g_mouse_saved = false;
     }
   Buttons_Refresh();
   Title_Update();
   ChartRedraw();
  }

void Arm(const ENUM_TP_MODE mode, const int idx)
  {
   Cancel();
   g_mode = mode;
   g_var  = idx;
   g_step = 0;
   if(!g_mouse_saved)
     {
      g_mouse_prev  = ChartGetInteger(0, CHART_EVENT_MOUSE_MOVE);
      g_mouse_saved = true;
     }
   ChartSetInteger(0, CHART_EVENT_MOUSE_MOVE, true);
   Buttons_Refresh();
   Title_Update();
   ChartRedraw();
  }

void StartDrawing(const datetime t, const double p)
  {
   g_t1 = t;
   g_p1 = p;
   switch(g_mode)
     {
      case TP_RECT_ALARM:
         g_obj = NewBase(PFX_ALARM, "");
         CreateRect(g_obj, t, p, CLR_ALARM[g_var], true);
         break;
      case TP_RECT_NORMAL:
         g_obj = NewBase(PFX_RECT, "");
         CreateRect(g_obj, t, p, CLR_NORMAL[g_var], false);
         break;
      case TP_TRIDENT:
         g_base = NewBase(PFX_TRI, "_AB");
         g_obj  = g_base + "_AB";
         PutTrend(g_obj, t, p, t, p, CLR_TRI[g_var], InpTridentWidth, false, false, false);
         break;
      case TP_TREND:
         g_obj = NewBase(PFX_TREND, "");
         PutTrend(g_obj, t, p, t, p, CLR_TREND[g_var], InpTrendWidth, InpTrendRay, false, false);
         break;
      default:
         return;
     }
   g_step = 1;
   Title_Update();
   ChartRedraw();
  }

void FinishDrawing(const datetime t, const double p)
  {
   ObjectMove(0, g_obj, 1, t, p);
   ObjectSetInteger(0, g_obj, OBJPROP_SELECTABLE, true);
   if(g_mode == TP_TRIDENT)
     {
      Trident_Rebuild(g_base);
      ObjectSetInteger(0, g_base + "_AB", OBJPROP_SELECTED, true);   // Anfasser sofort sichtbar
      ObjectSetInteger(0, g_base + "_BC", OBJPROP_SELECTED, true);
     }
   g_step = 0;     // Objekt bleibt stehen -> Cancel() löscht nichts
   Cancel();
  }

void OnChartClickXY(const int x, const int y)
  {
   if(g_mode == TP_NONE || InPanel(x, y))
      return;
   int      sub;
   datetime t;
   double   p;
   if(!ChartXYToTimePrice(0, x, y, sub, t, p) || sub != 0)
      return;
   if(g_step == 0)
      StartDrawing(t, p);
   else
      FinishDrawing(t, p);
  }

void OnMouseMoveXY(const int x, const int y)
  {
   if(g_mode == TP_NONE || g_step != 1 || g_obj == "")
      return;
   int      sub;
   datetime t;
   double   p;
   if(!ChartXYToTimePrice(0, x, y, sub, t, p) || sub != 0)
      return;
   ObjectMove(0, g_obj, 1, t, p);
   ChartRedraw();
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
   ENUM_TP_MODE m   = KindToMode(StringSubstr(s, 4, 1));
   int          idx = (int)StringToInteger(StringSubstr(s, 5));
   if(m == TP_NONE)
      return;
   if(g_mode == m && g_var == idx)
      Cancel();       // zweiter Klick auf dieselbe Taste = Abbruch
   else
      Arm(m, idx);
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
      ObjectSetString(0, name, OBJPROP_TEXT, TXT_ALARM_OFF);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, "Alarm-Rechteck (ausgelöst)");
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
      if(InpAlarmOnce && ObjectGetString(0, name, OBJPROP_TEXT) == TXT_ALARM_OFF)
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
   Cancel();
   ObjectsDeleteAll(0, PFX_UI);
   if(reason == REASON_REMOVE)
      ObjectDelete(0, NM_STATE);
   ChartRedraw();
  }

void OnTimer()
  {
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
   else if(id == CHARTEVENT_CLICK)
      OnChartClickXY((int)lparam, (int)dparam);
   else if(id == CHARTEVENT_MOUSE_MOVE)
      OnMouseMoveXY((int)lparam, (int)dparam);
   else if(id == CHARTEVENT_KEYDOWN)
     {
      if(lparam == 27 && g_mode != TP_NONE)   // ESC
         Cancel();
     }
   else if(id == CHARTEVENT_OBJECT_DRAG || id == CHARTEVENT_OBJECT_CHANGE)
     {
      int L = StringLen(sparam);
      if(StringFind(sparam, PFX_TRI) == 0 && L > 3)
        {
         string suf = StringSubstr(sparam, L - 3);
         if(suf == "_AB" || suf == "_BC")
           {
            Trident_Rebuild(StringSubstr(sparam, 0, L - 3));
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
