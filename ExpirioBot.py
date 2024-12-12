#!/usr/bin/env python3

import cv2
import pytesseract
import re
from datetime import datetime
import threading
import queue
import time
from Arm_Lib import Arm_Device
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk

# Initialize the robotic arm (DOFBOT)
Arm = Arm_Device()
time.sleep(0.1)  # Allow the arm to initialize properly

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Arm movement functions
def arm_clamp_block(enable):
    """
    Controls the robotic arm clamp to either hold or release an object.
    Args:
        enable (int): 1 to clamp, 0 to release.
    """
    position = 100 if enable else 10
    Arm.Arm_serial_servo_write(6, position, 400)
    time.sleep(0.5)

def arm_move(positions, s_time=500):
    """
    Moves the robotic arm to specified positions.
    Args:
        positions (list): List of positions for the arm's servos.
        s_time (int): Duration of the movement in milliseconds.
    """
    for i, pos in enumerate(positions):
        servo_id = i + 1
        # Adjust timing for specific servos if necessary
        adjusted_time = (
            int(s_time * 1.2) if servo_id == 5 else
            int(3 * s_time / 4) if servo_id == 1 else
            int(s_time)
        )
        Arm.Arm_serial_servo_write(servo_id, pos, adjusted_time)
        time.sleep(0.01)
    time.sleep(s_time / 1000)

# Predefined arm positions
p_front = [90, 75, 0, 30, 90]
p_right = [0, 75, 0, 30, 90]
p_right_top = [0, 75, 0, 60, 90]
p_left_top = [180, 75, 0, 60, 90]
p_left = [180, 75, 0, 30, 90]
p_top = [90, 80, 50, 50, 90]
p_rest = [90, 90, 0, 5, 90]

# Last processed date to prevent redundant processing
last_processed_date = None

# Queue lock to ensure thread-safe operations
queue_lock = threading.Lock()

def move_object(target, processing_event, producer_allowed_event):
    """
    Moves an object to the specified target location (left or right).
    Args:
        target (str): 'left' or 'right'.
        processing_event (threading.Event): Event to control processing flow.
        producer_allowed_event (threading.Event): Event to control frame capturing.
    """
    processing_event.clear()
    producer_allowed_event.clear()
    try:
        if target not in ['left', 'right']:
            print("Invalid target! Use 'left' or 'right'.")
            return

        # Pick up the object
        arm_clamp_block(0)  # Release to prepare for pickup
        arm_move(p_front, 1000)
        arm_clamp_block(1)  # Clamp the object
        arm_move(p_top, 1000)  # Lift the object

        # Move to the target
        if target == 'left':
            arm_move(p_left, 1000)
            arm_clamp_block(0)  # Release object
            arm_move(p_left_top, 500)
        elif target == 'right':
            arm_move(p_right, 1000)
            arm_clamp_block(0)  # Release object
            arm_move(p_right_top, 500)

        # Return to the rest position
        arm_move(p_top, 1000)
        arm_move(p_rest, 1000)
    except Exception as e:
        print(f"Error during arm movement: {e}")
    finally:
        producer_allowed_event.set()
        processing_event.set()

def preprocess_image(frame):
    """
    Converts a frame to grayscale and applies binary thresholding.
    Args:
        frame: Image frame to preprocess.
    Returns:
        Processed binary image.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

def extract_expiry_date(image_path):
    """
    Extracts expiry date from an image using OCR.
    Args:
        image_path (str): Path to the image file.
    Returns:
        str: Extracted expiry date in DD/MM/YYYY format or None if not found.
    """
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

def process_frames(frame_queue_container, processing_event, producer_allowed_event, expired_count, valid_count):
    """
    Processes frames from the queue to detect expiry dates and take actions.
    Args:
        frame_queue_container (list): Container holding the frame queue.
        processing_event (threading.Event): Event to control processing flow.
        producer_allowed_event (threading.Event): Event to control frame capturing.
        expired_count (tk.IntVar): Counter for expired products.
        valid_count (tk.IntVar): Counter for valid products.
    """
    global last_processed_date
    while True:
        processing_event.wait()
        with queue_lock:
            current_queue = frame_queue_container[0]

        if not current_queue.empty():
            frame = current_queue.get()
            image_path = "image.jpg"
            processed_frame = preprocess_image(frame)
            cv2.imwrite(image_path, processed_frame)
            expiry_date = extract_expiry_date(image_path)
            if expiry_date:
                try:
                    formatted_date = expiry_date.replace('.', '/')
                    expiry_date_obj = datetime.strptime(formatted_date, "%d/%m/%Y")
                    today = datetime.today()
                    if last_processed_date is None or last_processed_date != expiry_date_obj:
                        last_processed_date = expiry_date_obj
                        if expiry_date_obj < today:
                            target = "left"
                            print("The product has expired!")
                            expired_count.set(expired_count.get() + 1)
                        else:
                            target = "right"
                            print("The product is valid.")
                            valid_count.set(valid_count.get() + 1)

                        producer_allowed_event.clear()
                        processing_event.clear()
                        with queue_lock:
                            frame_queue_container[0] = queue.Queue(maxsize=10)
                        move_object(target, processing_event, producer_allowed_event)
                except ValueError:
                    print("Invalid date format. Please check the extracted date.")

def capture_frames(cap, frame_queue_container, producer_allowed_event):
    """
    Continuously captures frames from the camera and adds them to the queue.
    Args:
        cap: OpenCV VideoCapture object.
        frame_queue_container (list): Container holding the frame queue.
        producer_allowed_event (threading.Event): Event to control frame capturing.
    """
    while True:
        producer_allowed_event.wait()
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        with queue_lock:
            current_queue = frame_queue_container[0]
            if current_queue.full():
                try:
                    current_queue.get_nowait()
                except queue.Empty:
                    pass
            current_queue.put(frame)
        time.sleep(0.1)

def main():
    """
    Main function to initialize the system and GUI.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    root = tk.Tk()
    root.title("ExpirioBot Control Panel")
    root.configure(bg="#2e2e2e")

    video_label = Label(root, bg="#2e2e2e")
    video_label.pack()

    expired_count = tk.IntVar(value=0)
    valid_count = tk.IntVar(value=0)

    expired_label = tk.Label(root, textvariable=expired_count, font=("Comfortaa", 14), fg="red", bg="#2e2e2e")
    expired_label.pack()
    tk.Label(root, text="Expired Products", font=("Comfortaa", 12), bg="#2e2e2e", fg="white").pack()

    valid_label = tk.Label(root, textvariable=valid_count, font=("Comfortaa", 14), fg="green", bg="#2e2e2e")
    valid_label.pack()
    tk.Label(root, text="Valid Products", font=("Comfortaa", 12), bg="#2e2e2e", fg="white").pack()

    frame_queue_container = [queue.Queue(maxsize=10)]
    processing_event = threading.Event()
    producer_allowed_event = threading.Event()

    producer_thread = None
    consumer_thread = None

    def start_program():
        """
        Starts the frame capture and processing threads.
        """
        nonlocal producer_thread, consumer_thread
        processing_event.set()
        producer_allowed_event.set()

        if producer_thread is None or not producer_thread.is_alive():
            producer_thread = threading.Thread(target=capture_frames, args=(cap, frame_queue_container, producer_allowed_event))
            producer_thread.daemon = True
            producer_thread.start()

        if consumer_thread is None or not consumer_thread.is_alive():
            consumer_thread = threading.Thread(target=process_frames, args=(frame_queue_container, processing_event, producer_allowed_event, expired_count, valid_count))
            consumer_thread.daemon = True
            consumer_thread.start()

    def stop_program():
        """
        Stops the frame capture and processing threads.
        """
        producer_allowed_event.clear()
        processing_event.clear()

    def update_frame():
        """
        Updates the GUI with the latest video frame from the camera.
        """
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        root.after(10, update_frame)

    # Buttons for controlling the program
    button_frame = tk.Frame(root, bg="#2e2e2e")
    button_frame.pack(pady=10)

    start_button = tk.Button(button_frame, text="Start", command=start_program, bg="#4caf50", fg="white", font=("Comfortaa", 12))
    start_button.grid(row=0, column=0, padx=10)

    stop_button = tk.Button(button_frame, text="Stop", command=stop_program, bg="#f44336", fg="white", font=("Comfortaa", 12))
    stop_button.grid(row=0, column=1, padx=10)

    update_frame()
    root.mainloop()
    cap.release()

if __name__ == "__main__":
    try:
        main()
    finally:
        del Arm
        print("Program Ended")
