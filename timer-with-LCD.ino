#include <LiquidCrystal.h>

LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

const int BUZZER_PIN = 8;            // Buzzer
const int LED_PINS[] = {A0, A1}; // 2 LEDs

bool running = true;     // Start automatically
bool finished = false;
bool onBreak = false;
unsigned long startTime = 0;

// Timers (for testing - change these for actual use)
const unsigned long FOCUS_TIME = 10000UL; // 10s focus (change to 1500000UL for 25 min)
const unsigned long BREAK_TIME = 5000UL;  // 5s break (change to 300000UL for 5 min)

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  for (int i = 0; i < 2; i++) pinMode(LED_PINS[i], OUTPUT);
  
  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Focus starting...");
  startTime = millis();
  
  // Turn LEDs off initially
  for (int i = 0; i < 2; i++) analogWrite(LED_PINS[i], 0);
}

void loop() {
  if (running) {
    unsigned long currentElapsed = millis() - startTime;
    unsigned long totalTime = onBreak ? BREAK_TIME : FOCUS_TIME;
    long remaining = totalTime - currentElapsed;
    if (remaining < 0) remaining = 0;
    
    // Update LCD message
    lcd.setCursor(0, 0);
    if (onBreak) {
      lcd.print("Break Time      ");
    } else {
      lcd.print("Focus Time      ");
    }
    
    displayTime(remaining);
    
    // Timer finished
    if (remaining == 0 && !finished) {
      finished = true;
      running = false;
      
      // Turn all LEDs on
      for (int i = 0; i < 2; i++) analogWrite(LED_PINS[i], 255);
      
      // Show message
      lcd.clear();
      lcd.setCursor(0, 0);
      if (onBreak) lcd.print("Break over!");
      else lcd.print("Focus done!");
      
      // Play gentle wake-up melody
      wakeUpTone();
      
      delay(3000); // Show message for 3 seconds
      
      // Turn LEDs off
      for (int i = 0; i < 4; i++) analogWrite(LED_PINS[i], 0);
      
      // Prepare for next session
      onBreak = !onBreak;
      startTime = millis();
      running = true;
      finished = false;
      
      lcd.clear();
    }
  }
}

void displayTime(unsigned long ms) {
  unsigned long totalSeconds = ms / 1000;
  unsigned int minutes = totalSeconds / 60;
  unsigned int seconds = totalSeconds % 60;
  
  lcd.setCursor(0, 1);
  lcd.print("Time: ");
  if (minutes < 10) lcd.print('0');
  lcd.print(minutes);
  lcd.print(':');
  if (seconds < 10) lcd.print('0');
  lcd.print(seconds);
  lcd.print("   ");
}

// Wake-up melody function
void wakeUpTone() {
  int melody[] = {262, 294, 330, 349, 392, 440, 494, 523}; // C D E F G A B C
  int duration = 200; // 200ms per note
  for (int i = 0; i < 8; i++) {
    tone(BUZZER_PIN, melody[i], duration);
    delay(duration + 50);
  }
  noTone(BUZZER_PIN);
}