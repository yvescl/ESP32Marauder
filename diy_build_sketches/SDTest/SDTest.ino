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

  sdSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);

  if (!SD.begin(SD_CS, sdSPI)) {
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
