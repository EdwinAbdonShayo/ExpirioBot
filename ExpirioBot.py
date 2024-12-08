
# ExpirioBot with AI Vision & Servo Movement
# Author: Expirio   
# Date: 2024-12-09
# Version: 1.0

#!/usr/bin/env python3
#coding=utf-8

import cv2
from PIL import Image
import pytesseract
import re
from datetime import datetime
import time
from threading import Thread
from Arm_Lib import Arm_Device

# Initialize DOFBOT
Arm = Arm_Device()
time.sleep(0.1)

# Tesseract setup (Windows only; comment for Linux/macOS)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Arm functions
def arm_clamp_block(enable):
    if enable == 0:  # Release
        Arm.Arm_serial_servo_write(6, 60, 400)
    else:  # Clamp
        Arm.Arm_serial_servo_write(6, 130, 400)
    time.sleep(0.5)

def arm_move(p, s_time=500):
    for i in range(5):
        id = i + 1
        if id == 5:
            time.sleep(0.1)
            Arm.Arm_serial_servo_write(id, p[i], int(s_time * 1.2))
        elif id == 1:
            Arm.Arm_serial_servo_write(id, p[i], int(3 * s_time / 4))
        else:
            Arm.Arm_serial_servo_write(id, p[i], int(s_time))
        time.sleep(0.01)
    time.sleep(s_time / 1000)

# Arm positions
p_front = [90, 60, 50, 50, 90]  # Front position
p_right = [0, 60, 50, 50, 90]   # Right position
p_left = [180, 60, 50, 50, 90]  # Left position
p_top = [90, 80, 50, 50, 90]    # Top (transition) position
p_rest = [90, 130, 0, 0, 90]    # Rest position

def move_object(target):
    if target not in ['left', 'right']:
        print("Invalid target! Use 'left' or 'right'.")
        return

    arm_clamp_block(0)  # Open clamp
    arm_move(p_front, 1000)  # Move to front position
    arm_clamp_block(1)  # Clamp object
    arm_move(p_top, 1000)  # Transition to top position

    if target == 'left':
        arm_move(p_left, 1000)
    elif target == 'right':
        arm_move(p_right, 1000)

    arm_clamp_block(0)  # Release object
    arm_move(p_top, 1000)
    arm_move(p_rest, 1000)

# OCR and expiry date functions
def preprocess_image(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

def extract_expiry_date(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    print("Extracted Text:\n", text)

    pattern = r'\b\d{2}[./]\d{2}[./]\d{4}\b'
    match = re.search(pattern, text)
    if match:
        expiry_date = match.group(0)
        print("Expiry Date Found:", expiry_date)
        return expiry_date
    else:
        print("Expiry date not found in the text")
        return None

def check_expiry(expiry_date):
    try:
        formatted_date = expiry_date.replace('.', '/')
        expiry_date_obj = datetime.strptime(formatted_date, "%d/%m/%Y")
        today = datetime.today()

        if expiry_date_obj < today:
            print("The product has expired!")
            return 'left'
        else:
            print("The product is valid.")
            return 'right'
    except ValueError:
        print("Invalid date format. Please check the extracted date.")
        return None

# Camera and arm control integration
def capture_and_process(cap):
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        time.sleep(5)  # Capture every 5 seconds
        image_path = "image.jpg"
        processed_frame = preprocess_image(frame)
        cv2.imwrite(image_path, processed_frame)
        print(f"Image saved as {image_path}")

        expiry_date = extract_expiry_date(image_path)
        if expiry_date:
            state = check_expiry(expiry_date)
            if state:
                move_object(state)

# Main function
def main():
    cap = cv2.VideoCapture(0)

    thread = Thread(target=capture_and_process, args=(cap,))
    thread.daemon = True
    thread.start()

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
            break

    cap.release()
    cv2.destroyAllWindows()
    del Arm  # Release DOFBOT object

if __name__ == "__main__":
    main()
