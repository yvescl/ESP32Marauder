#include <SPI.h>
#include <SD.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

// Matches Marauder V4 config: SD shares the TFT SPI bus, own CS pin.
#define SD_CS   12
#define SD_SCK  18
#define SD_MOSI 23
#define SD_MISO 19

SPIClass sdSPI(VSPI);

void logLine(const String& s) {
  Serial.println(s);
  tft.println(s);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  tft.init();
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  tft.setRotation(0);
  tft.fillScreen(TFT_BLACK);
  tft.setTextFont(2);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setCursor(5, 5);

  logLine("SD card diagnostic");
  logLine("");

  // Keep the display deselected while the SD card is probed.
  pinMode(TFT_CS, OUTPUT);
  digitalWrite(TFT_CS, HIGH);

  sdSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);

  // Retry at slower clocks: jumper-wire wiring often fails at the default speed.
  const uint32_t speeds[] = {400000, 1000000, 4000000, 20000000};
  bool mounted = false;
  for (uint32_t hz : speeds) {
    SD.end();
    bool ok = SD.begin(SD_CS, sdSPI, hz);
    logLine(String(hz / 1000) + " kHz: " + (ok ? "OK" : "fail"));
    mounted = mounted || ok;
    delay(200);
  }
  // Leave the card mounted at the last speed that worked for the checks below.
  if (mounted) {
    SD.end();
    for (int i = 3; i >= 0 && !SD.begin(SD_CS, sdSPI, speeds[i]); i--) {}
  }
  logLine("");

  if (!mounted) {
    logLine("SD.begin() FAILED.");
    logLine("Card not mounted -");
    logLine("likely unformatted,");
    logLine("wrong filesystem,");
    logLine("or a wiring/power");
    logLine("issue.");
    return;
  }

  uint8_t cardType = SD.cardType();
  if (cardType == CARD_NONE) {
    logLine("No SD card detected");
    logLine("(slot empty or not");
    logLine("making contact).");
    return;
  }

  logLine("Card mounted OK!");
  logLine("");

  switch (cardType) {
    case CARD_MMC:  logLine("Type: MMC"); break;
    case CARD_SD:   logLine("Type: SDSC"); break;
    case CARD_SDHC: logLine("Type: SDHC"); break;
    default:        logLine("Type: UNKNOWN"); break;
  }

  uint64_t cardSizeMB = SD.cardSize() / (1024 * 1024);
  logLine("Size: " + String((unsigned long)cardSizeMB) + " MB");

  uint64_t totalMB = SD.totalBytes() / (1024 * 1024);
  uint64_t usedMB = SD.usedBytes() / (1024 * 1024);
  logLine("FS total: " + String((unsigned long)totalMB) + " MB");
  logLine("FS used: " + String((unsigned long)usedMB) + " MB");

  logLine("");
  logLine("Filesystem is valid");
  logLine("and readable.");
}

void loop() {
  delay(1000);
}
