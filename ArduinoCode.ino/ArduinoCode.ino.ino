/*
 * ============================================================
 *  TEMPERATURE MONITOR — Arduino Uno
 * ============================================================
 *  Reads temperature from DHT22 sensor.
 *  Displays name (with horizontal scroll if > 16 chars) on
 *  LCD row 1, and temperature on row 2.
 *  Sends temperature to PC via Serial at 9600 baud.
 *
 *  Libraries needed (install via Arduino IDE Library Manager):
 *    - DHT sensor library  (by Adafruit)
 *    - Adafruit Unified Sensor
 *    - LiquidCrystal I2C   (by Frank de Brabander)
 *
 *  Wiring:
 *    DHT22  DATA  → Arduino pin 7
 *    DHT22  VCC   → 5V
 *    DHT22  GND   → GND
 *    LCD    SDA   → A4
 *    LCD    SCL   → A5
 *    LCD    VCC   → 5V
 *    LCD    GND   → GND
 * ============================================================
 */

#include <DHT.h>
#include <LiquidCrystal_I2C.h>

// ----- Configuration ----------------------------------------
#define DHTPIN   7          // DHT22 data pin
#define DHTTYPE  DHT11

// YOUR NAME — change this string to your name
const String MY_NAME = "NDANYUZWE UHIRWA SHAMI Melissa";   // example: 19 chars → will scroll

// Scroll speed: milliseconds between each shift
const int SCROLL_DELAY_MS = 350;

// How long to pause at the start before scrolling (ms)
const int SCROLL_PAUSE_MS = 1500;

// Temperature read interval (ms)
const unsigned long TEMP_INTERVAL_MS = 1000;
// ------------------------------------------------------------

DHT dht(DHTPIN, DHTTYPE);

// I2C address is usually 0x27 or 0x3F — try 0x27 first
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Scroll state
String  scrollText    = "";   // padded name for scrolling
int     scrollPos     = 0;    // current scroll offset
bool    needsScroll   = false;

// Timing
unsigned long lastTempRead   = 0;
unsigned long lastScroll     = 0;
bool          scrollPaused   = true;
unsigned long pauseStarted   = 0;

float lastTemp = 0.0;

// ---- Build the padded scroll buffer -------------------------
// We add 16 trailing spaces so the text glides fully off screen
void buildScrollBuffer() {
  if (MY_NAME.length() > 16) {
    needsScroll = true;
    // Pad with spaces at both ends for a clean scroll-in / scroll-out
    scrollText = MY_NAME + "                ";  // 16 trailing spaces
  } else {
    needsScroll = false;
  }
}

// ---- Display a 16-char window of the scroll buffer ----------
void showScrollFrame(int pos) {
  lcd.setCursor(0, 0);
  String frame = scrollText.substring(pos, pos + 16);
  // Pad to 16 chars if near the end
  while (frame.length() < 16) frame += " ";
  lcd.print(frame);
}

// ---- Display temperature on row 2 --------------------------
void showTemperature(float t) {
  lcd.setCursor(0, 1);
  lcd.print("Temp: ");
  if (isnan(t)) {
    lcd.print("Err     ");
  } else {
    lcd.print(t, 1);   // one decimal place
    lcd.print((char)223);  // degree symbol °
    lcd.print("C    ");    // trailing spaces clear old chars
  }
}

// ============================================================
void setup() {
  Serial.begin(9600);
  dht.begin();
  delay(2000);        // <-- Add this (important for DHT11)

  lcd.init();
  lcd.backlight();
  lcd.clear();

  buildScrollBuffer();

  // Startup message...
  lcd.setCursor(0, 0);
  lcd.print("Temp Monitor");
  lcd.setCursor(0, 1);
  lcd.print("Starting...");
  delay(1500);
  lcd.clear();

  if (!needsScroll) {
    lcd.setCursor(0, 0);
    lcd.print(MY_NAME);
  } else {
    showScrollFrame(0);
    pauseStarted = millis();
  }

  Serial.println("READY");
}
// ============================================================
void loop() {
  unsigned long now = millis();

  // --- 1. Read temperature every TEMP_INTERVAL_MS -----------
  if (now - lastTempRead >= TEMP_INTERVAL_MS) {
    lastTempRead = now;

    float t = dht.readTemperature();   // Celsius
    float h = dht.readHumidity();

    if (!isnan(t)) {
      lastTemp = t;
      showTemperature(t);

      // Send to PC as a simple line: "TEMP:24.5"
      Serial.print("TEMP:");
      Serial.println(t, 1);
    } else {
      showTemperature(NAN);
      Serial.println("TEMP:ERROR");
    }
  }

  // --- 2. Scroll the name row (only if name > 16 chars) -----
  if (needsScroll) {
    // Initial pause before scrolling begins
    if (scrollPaused) {
      if (now - pauseStarted >= SCROLL_PAUSE_MS) {
        scrollPaused = false;
        lastScroll   = now;
      }
    } else {
      // Advance scroll position
      if (now - lastScroll >= SCROLL_DELAY_MS) {
        lastScroll = now;
        scrollPos++;

        // When the whole name has scrolled off, reset to start
        if (scrollPos > (int)scrollText.length() - 16) {
          scrollPos    = 0;
          scrollPaused = true;
          pauseStarted = now;
        }

        showScrollFrame(scrollPos);
      }
    }
  }
}
