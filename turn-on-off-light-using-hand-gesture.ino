#define LED_PIN 3

// Timer states
enum TimerState {
  STOPPED,
  RUNNING,
  PAUSED,
  BREAK
};

TimerState currentState = STOPPED;
unsigned long timerStart = 0;
unsigned long timerDuration = 0;
unsigned long pausedTime = 0;
unsigned long lastBlinkTime = 0;
bool ledState = LOW;

const unsigned long POMODORO_TIME = 25UL * 60 * 1000;  // 25 minutes in ms
const unsigned long BREAK_5_TIME = 5UL * 60 * 1000;    // 5 minutes
const unsigned long BREAK_10_TIME = 10UL * 60 * 1000;  // 10 minutes
const unsigned long BREAK_15_TIME = 15UL * 60 * 1000;  // 15 minutes

String inputString = "";

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  Serial.println("Pomodoro Timer Ready!");
  Serial.println("Commands: START, STOP, PAUSE, BREAK5, BREAK10, BREAK15");
}

void loop() {
  // Read serial input
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      handleCommand();
      inputString = "";
    } else {
      inputString += c;
    }
  }
  
  // Update LED based on state
  updateLED();
}

void handleCommand() {
  inputString.trim();
  
  if (inputString == "START") {
    startTimer(POMODORO_TIME);
    Serial.println("Timer STARTED - 25 min Pomodoro");
    
  } else if (inputString == "STOP") {
    stopTimer();
    Serial.println("Timer STOPPED");
    
  } else if (inputString == "PAUSE") {
    pauseTimer();
    Serial.println("Timer PAUSED");
    
  } else if (inputString == "BREAK5") {
    startTimer(BREAK_5_TIME);
    currentState = BREAK;
    Serial.println("BREAK Started - 5 minutes");
    
  } else if (inputString == "BREAK10") {
    startTimer(BREAK_10_TIME);
    currentState = BREAK;
    Serial.println("BREAK Started - 10 minutes");
    
  } else if (inputString == "BREAK15") {
    startTimer(BREAK_15_TIME);
    currentState = BREAK;
    Serial.println("BREAK Started - 15 minutes");
  }
}

void startTimer(unsigned long duration) {
  if (currentState == PAUSED) {
    // Resume from pause
    timerStart = millis() - pausedTime;
    currentState = RUNNING;
  } else {
    // Start new timer
    timerStart = millis();
    timerDuration = duration;
    currentState = RUNNING;
  }
}

void stopTimer() {
  currentState = STOPPED;
  digitalWrite(LED_PIN, LOW);
  pausedTime = 0;
}

void pauseTimer() {
  if (currentState == RUNNING || currentState == BREAK) {
    currentState = PAUSED;
    pausedTime = millis() - timerStart;
  }
}

void updateLED() {
  unsigned long currentTime = millis();
  
  switch (currentState) {
    case STOPPED:
      // LED off
      digitalWrite(LED_PIN, LOW);
      break;
      
    case RUNNING:
      // Solid ON during work session
      digitalWrite(LED_PIN, HIGH);
      
      // Check if timer completed
      if (currentTime - timerStart >= timerDuration) {
        Serial.println("Pomodoro COMPLETE!");
        blinkComplete();
        currentState = STOPPED;
      }
      break;
      
    case BREAK:
      // Slow blink during break
      if (currentTime - lastBlinkTime >= 1000) {
        ledState = !ledState;
        digitalWrite(LED_PIN, ledState);
        lastBlinkTime = currentTime;
      }
      
      // Check if break completed
      if (currentTime - timerStart >= timerDuration) {
        Serial.println("Break COMPLETE!");
        blinkComplete();
        currentState = STOPPED;
      }
      break;
      
    case PAUSED:
      // Fast blink when paused
      if (currentTime - lastBlinkTime >= 250) {
        ledState = !ledState;
        digitalWrite(LED_PIN, ledState);
        lastBlinkTime = currentTime;
      }
      break;
  }
}

void blinkComplete() {
  // Blink rapidly 5 times when timer completes
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
}