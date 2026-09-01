#include <SPI.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

// Higher / stricter than the library's internal Z_THRESHOLD/2 (175),
// to reject this panel's noise floor and only accept deliberate presses.
#define MY_Z_THRESHOLD 600
#define HOLD_MS 700          // must stay pressed this long, continuously
#define SAMPLES 10           // raw samples averaged once a hold qualifies

struct Corner {
  const char* name;
  int16_t tx, ty;   // text label position
};

Corner corners[4] = {
  { "TOP-LEFT",     10, 10 },
  { "BOTTOM-LEFT",  10, 0 },   // ty set at runtime (needs height)
  { "TOP-RIGHT",    0, 10 },   // tx set at runtime (needs width)
  { "BOTTOM-RIGHT", 0, 0 },
};

int32_t rawX[4], rawY[4];

void drawCorner(uint8_t i) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextFont(4);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setCursor(10, 10);
  tft.print("Corner ");
  tft.print(i + 1);
  tft.print("/4:");
  tft.setCursor(10, 45);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.println(corners[i].name);

  tft.setTextFont(2);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setCursor(10, 90);
  tft.println("Press & hold firmly");
  tft.println("in that corner.");

  // draw a bracket mark at the actual target corner
  int16_t x0, y0;
  switch (i) {
    case 0: x0 = 0; y0 = 0; break;                                   // TL
    case 1: x0 = 0; y0 = tft.height() - 1; break;                    // BL
    case 2: x0 = tft.width() - 1; y0 = 0; break;                     // TR
    case 3: x0 = tft.width() - 1; y0 = tft.height() - 1; break;      // BR
  }
  int8_t sx = (x0 == 0) ? 1 : -1;
  int8_t sy = (y0 == 0) ? 1 : -1;
  for (int k = 0; k < 20; k++) {
    tft.drawPixel(x0 + sx * k, y0, TFT_MAGENTA);
    tft.drawPixel(x0, y0 + sy * k, TFT_MAGENTA);
  }
}

void updateStatus(int z, int heldMs) {
  tft.fillRect(10, 150, tft.width() - 20, 60, TFT_BLACK);
  tft.setTextFont(2);
  tft.setCursor(10, 150);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.print("Z: ");
  tft.print(z);
  tft.setCursor(10, 175);
  if (z > MY_Z_THRESHOLD) {
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.print("Holding... ");
    tft.print(heldMs);
    tft.print("ms");
  } else {
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.print("Waiting for firm press");
  }
}

// Wait for a press held continuously above MY_Z_THRESHOLD for HOLD_MS,
// then average SAMPLES raw readings. Rejects brief noise spikes.
void captureCorner(uint8_t i) {
  uint32_t holdStart = 0;
  bool holding = false;

  while (true) {
    uint16_t z = tft.getTouchRawZ();
    uint32_t now = millis();

    if (z > MY_Z_THRESHOLD) {
      if (!holding) {
        holding = true;
        holdStart = now;
      }
    } else {
      holding = false;
    }

    int heldMs = holding ? (now - holdStart) : 0;
    updateStatus(z, heldMs);

    if (holding && heldMs >= HOLD_MS) break;
    delay(50);
  }

  // Confirmed deliberate press - average several raw samples
  int32_t sx = 0, sy = 0;
  uint8_t got = 0;
  while (got < SAMPLES) {
    if (tft.getTouchRawZ() > MY_Z_THRESHOLD) {
      uint16_t x, y;
      tft.getTouchRaw(&x, &y);
      sx += x;
      sy += y;
      got++;
    }
    delay(15);
  }
  rawX[i] = sx / SAMPLES;
  rawY[i] = sy / SAMPLES;

  Serial.print("Corner ");
  Serial.print(corners[i].name);
  Serial.print(" raw = ");
  Serial.print(rawX[i]);
  Serial.print(", ");
  Serial.println(rawY[i]);

  // wait for release before moving on
  tft.fillRect(10, 150, tft.width() - 20, 60, TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setCursor(10, 150);
  tft.println("Captured! Release now.");
  while (tft.getTouchRawZ() > MY_Z_THRESHOLD / 2) delay(20);
  delay(400);
}

void setup() {
  Serial.begin(115200);

  tft.init();

  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  tft.setRotation(0);

  for (uint8_t i = 0; i < 4; i++) {
    drawCorner(i);
    captureCorner(i);
  }

  // TL=0 BL=1 TR=2 BR=3
  // x0 = average of left corners, x1 = average of right corners
  int32_t x0 = (rawX[0] + rawX[1]) / 2;
  int32_t x1 = (rawX[2] + rawX[3]) / 2;
  int32_t y0 = (rawY[0] + rawY[2]) / 2;
  int32_t y1 = (rawY[1] + rawY[3]) / 2;

  uint8_t invert_x = 0, invert_y = 0;
  if (x0 > x1) { int32_t t = x0; x0 = x1; x1 = t; invert_x = 1; }
  if (y0 > y1) { int32_t t = y0; y0 = y1; y1 = t; invert_y = 1; }

  int32_t xr = x1 - x0;
  int32_t yr = y1 - y0;
  if (x0 == 0) x0 = 1;
  if (xr == 0) xr = 1;
  if (y0 == 0) y0 = 1;
  if (yr == 0) yr = 1;

  uint16_t calData[5] = {
    (uint16_t)x0, (uint16_t)xr,
    (uint16_t)y0, (uint16_t)yr,
    (uint8_t)(0 | (invert_x << 1) | (invert_y << 2))
  };

  Serial.println();
  Serial.println("// Use this calibration code in setup():");
  Serial.print("  uint16_t calData[5] = { ");
  for (uint8_t i = 0; i < 5; i++) {
    Serial.print(calData[i]);
    if (i < 4) Serial.print(", ");
  }
  Serial.println(" };");

  tft.setTouch(calData);

  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextFont(2);
  tft.setCursor(10, 10);
  tft.println("Calibration done!");
  tft.println("Values (read to Claude):");
  tft.println();

  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  for (uint8_t i = 0; i < 5; i++) {
    tft.setCursor(20, 60 + i * 30);
    tft.setTextFont(4);
    tft.print("[");
    tft.print(i);
    tft.print("] ");
    tft.println(calData[i]);
  }

  tft.setTextFont(2);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setCursor(10, 220);
  tft.println("Tap screen to test mapping.");
}

void loop() {
  uint16_t x = 0, y = 0;
  if (tft.getTouch(&x, &y)) {
    tft.fillCircle(x, y, 3, TFT_WHITE);
  }
}
