int last_state;
long start_at;

void setup() {
  Serial.begin(115200);
  Serial.println("");
  pinMode(2, INPUT_PULLUP);
  last_state = digitalRead(2);
}

void on_press() {
  start_at = millis();
}

void on_release() {
  on_press_for(millis() - start_at);
}

void on_press_for(int length) {
  Serial.println(length);
}

void loop() {
  int new_state = digitalRead(2);
  if (last_state != new_state) {
    delay(5);
    if (last_state != new_state) {
      (new_state == 0 ? on_press : on_release)();
      delay(10);
    }
  } else {
    delay(5);
  }
  last_state = new_state;
}

