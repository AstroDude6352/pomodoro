import cv2
import mediapipe as mp
import serial
import time

# ----- MediaPipe Hands -----
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# ----- Camera Setup -----
cap = None
for i in range(5):
    test_cap = cv2.VideoCapture(i)
    if test_cap.isOpened():
        cap = test_cap
        print(f"Using camera {i}")
        break
if cap is None:
    raise RuntimeError("No camera found!")

# ----- Arduino Serial -----
arduino_port = '/dev/cu.usbmodem14201'
baud_rate = 115200
try:
    arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
    time.sleep(2)
    print("Arduino connected!")
except Exception as e:
    print(f"Could not connect to Arduino: {e}")
    arduino = None

# ----- Timer State Tracking -----
timer_state = "STOPPED"  # STOPPED, RUNNING, PAUSED, BREAK
timer_start_time = None
timer_duration = 0
paused_elapsed = 0

POMODORO_DURATION = 10  # 10 seconds
BREAK_DURATION = 5      # 5 seconds

# ----- Gesture State Management -----
last_command_sent = None
gesture_hold_frames = 0
gesture_hold_required = 15
last_detected_gesture = None
gesture_command_sent = False  # NEW: Track if command was sent for current gesture

def update_timer_from_serial():
    """Read Arduino serial output to sync timer state"""
    global timer_state, timer_start_time, timer_duration, paused_elapsed
    
    if arduino and arduino.in_waiting:
        try:
            line = arduino.readline().decode('utf-8').strip()
            if line:
                print(f"Arduino: {line}")
                
                if "Timer STARTED" in line and "Pomodoro" in line:
                    timer_state = "RUNNING"
                    timer_start_time = time.time()
                    timer_duration = POMODORO_DURATION
                    paused_elapsed = 0
                    
                elif "BREAK Started" in line:
                    timer_state = "BREAK"
                    timer_start_time = time.time()
                    timer_duration = BREAK_DURATION
                    paused_elapsed = 0
                    
                elif "Timer PAUSED" in line:
                    if timer_state in ["RUNNING", "BREAK"]:
                        paused_elapsed = time.time() - timer_start_time
                        timer_state = "PAUSED"
                        
                elif "Timer STOPPED" in line:
                    timer_state = "STOPPED"
                    timer_start_time = None
                    
                elif "COMPLETE" in line:
                    timer_state = "STOPPED"
                    timer_start_time = None
        except:
            pass

def get_timer_display():
    """Calculate and format timer display"""
    if timer_state == "STOPPED":
        return "Ready", (200, 200, 200)
    
    elif timer_state == "PAUSED":
        remaining = timer_duration - paused_elapsed
        if remaining < 0:
            remaining = 0
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        return f"PAUSED {mins:02d}:{secs:02d}", (255, 165, 0)  # Orange
    
    elif timer_state in ["RUNNING", "BREAK"]:
        if timer_start_time:
            elapsed = time.time() - timer_start_time
            remaining = timer_duration - elapsed
            if remaining < 0:
                remaining = 0
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            
            if timer_state == "RUNNING":
                return f"Focus: {mins:02d}:{secs:02d}", (0, 255, 0)  # Green
            else:
                return f"Break: {mins:02d}:{secs:02d}", (0, 200, 255)  # Cyan
    
    return "Ready", (200, 200, 200)

# ----- Finger Counting Function -----
def count_fingers(hand_landmarks, handedness):
    """Count extended fingers"""
    fingers_up = []
    
    # Thumb
    if handedness == "Right":
        if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
            fingers_up.append(1)
        else:
            fingers_up.append(0)
    else:
        if hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x:
            fingers_up.append(1)
        else:
            fingers_up.append(0)
    
    # Other four fingers
    tip_ids = [8, 12, 16, 20]
    for tip_id in tip_ids:
        if hand_landmarks.landmark[tip_id].y < hand_landmarks.landmark[tip_id - 2].y:
            fingers_up.append(1)
        else:
            fingers_up.append(0)
    
    return sum(fingers_up), fingers_up

def is_hand_centered(hand_landmarks, frame_width, frame_height):
    """Check if hand is in center area of frame"""
    wrist = hand_landmarks.landmark[0]
    x, y = wrist.x * frame_width, wrist.y * frame_height
    
    center_margin_x = frame_width * 0.2
    center_margin_y = frame_width * 0.2
    
    return (center_margin_x < x < frame_width - center_margin_x and
            center_margin_y < y < frame_height - center_margin_y)

def is_hand_facing_camera(hand_landmarks):
    """Check if palm is facing camera"""
    wrist_z = hand_landmarks.landmark[0].z
    middle_base_z = hand_landmarks.landmark[9].z
    return abs(wrist_z - middle_base_z) < 0.1

def detect_gesture(finger_count, fingers_up, hand_landmarks, frame_width, frame_height):
    """Detect specific deliberate gestures"""
    
    if not is_hand_centered(hand_landmarks, frame_width, frame_height):
        return None, "Hand not centered"
    
    # Fist - START (must be centered and facing camera)
    if finger_count == 0:
        if is_hand_facing_camera(hand_landmarks):
            return "START", "✊ Fist: Start Pomodoro"
    
    # Palm - PAUSE (4 or 5 fingers up, more lenient)
    elif finger_count >= 4:
        # Check if at least 4 fingers are up (more forgiving)
        four_fingers_up = sum(fingers_up[1:])  # Count index, middle, ring, pinky
        if four_fingers_up >= 4:
            return "PAUSE", "✋ Palm: Pause Timer"
    
    # Thumbs up - BREAK (only thumb)
    elif finger_count == 1 and fingers_up[0] == 1 and sum(fingers_up[1:]) == 0:
        return "BREAK5", "👍 Thumbs Up: Start Break"
    
    return None, f"{finger_count} fingers"

def send_command(command):
    """Send command to Arduino"""
    global last_command_sent
    
    if arduino:
        arduino.write(f"{command}\n".encode())
        print(f"\n>>> Sent: {command}")
    last_command_sent = command

# ----- Main Setup -----
print("\n" + "="*50)
print("POMODORO HAND GESTURE CONTROLS")
print("="*50)
print("✊ FIST: Start 10-second Pomodoro")
print("✋ PALM (5 fingers): Pause timer")
print("👍 THUMBS UP: Start 5-second break")
print("\nHold gesture in CENTER for 0.5s")
print("Press 'q' to quit\n")
print("="*50 + "\n")

# ----- Main Loop -----
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Update timer state from Arduino
    update_timer_from_serial()

    # Flip for mirror effect
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    
    action_msg = "Show hand gesture in center"
    current_gesture = None

    # Draw center zone guide
    margin_x, margin_y = int(w * 0.2), int(h * 0.2)
    cv2.rectangle(frame, (margin_x, margin_y), (w - margin_x, h - margin_y), 
                  (100, 100, 100), 2)
    cv2.putText(frame, "Gesture Zone", (margin_x + 10, margin_y + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            hand_type = handedness.classification[0].label
            
            # Count fingers
            finger_count, fingers_up = count_fingers(hand_landmarks, hand_type)
            
            # Detect gesture
            command, description = detect_gesture(finger_count, fingers_up, hand_landmarks, w, h)
            
            # Draw landmarks if in valid zone
            if is_hand_centered(hand_landmarks, w, h):
                mp_drawing.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
            
            # NEW: Gesture hold logic with one-time send
            if command:
                if command == last_detected_gesture:
                    # Same gesture continues
                    if not gesture_command_sent:
                        gesture_hold_frames += 1
                        
                        if gesture_hold_frames >= gesture_hold_required:
                            # Send command once
                            send_command(command)
                            gesture_command_sent = True
                            action_msg = f"✓ {description}"
                        else:
                            action_msg = f"Hold... ({gesture_hold_frames}/{gesture_hold_required})"
                    else:
                        # Already sent, just show completion
                        action_msg = f"✓ {description}"
                else:
                    # New gesture detected
                    gesture_hold_frames = 1
                    last_detected_gesture = command
                    gesture_command_sent = False
                    action_msg = f"Hold... (1/{gesture_hold_required})"
            else:
                # No valid gesture
                gesture_hold_frames = 0
                last_detected_gesture = None
                gesture_command_sent = False
                action_msg = description
    else:
        # No hand detected
        gesture_hold_frames = 0
        last_detected_gesture = None
        gesture_command_sent = False

    # Display gesture feedback at top
    cv2.putText(frame, action_msg, (10, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Display timer in BOTTOM LEFT with background
    timer_text, timer_color = get_timer_display()
    
    # Create semi-transparent background for timer
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, h - 60), (250, h - 5), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    # Draw timer text
    cv2.putText(frame, timer_text, (15, h - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, timer_color, 2)
    
    cv2.imshow("Pomodoro Hand Control", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("\n" + "="*50)
print("Session ended. Goodbye!")
print("="*50)