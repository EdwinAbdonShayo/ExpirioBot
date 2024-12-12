import cv2
from PIL import Image
import pytesseract
import re
from datetime import datetime
import threading
import queue
import time
import customtkinter as ctk
from Arm_Lib import Arm_Device

# Initialize DOFBOT
Arm = Arm_Device()
time.sleep(0.1)

# Arm movement functions
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

# Positions
p_front = [90, 60, 50, 50, 90]  # Front position
p_right = [0, 80, 0, 5, 90]   # Right position
p_left = [180, 80, 0, 5, 90]  # Left position
p_top = [90, 80, 50, 50, 90]    # Top (transition) position
p_rest = [90, 90, 0, 5, 90]     # Rest position

# Synchronization tools
queue_lock = threading.Lock()
stop_event = threading.Event()
stop_event.set()

# Last processed date
last_processed_date = None

# Function to preprocess the image
def preprocess_image(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

# Function to extract expiry date
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

# Movement functions
def move_object(target, processing_event, producer_allowed_event):
    processing_event.clear()
    producer_allowed_event.clear()
    try:
        if target not in ['left', 'right']:
            print("Invalid target! Use 'left' or 'right'.")
            return

        arm_clamp_block(0)
        arm_move(p_front, 1000)
        arm_clamp_block(1)
        arm_move(p_top, 1000)

        if target == 'left':
            arm_move(p_left, 1000)
        elif target == 'right':
            arm_move(p_right, 1000)

        arm_clamp_block(0)
        arm_move(p_top, 1000)
        arm_move(p_rest, 1000)
    except Exception as e:
        print(f"Error during arm movement: {e}")
    finally:
        producer_allowed_event.set()
        processing_event.set()

# Frame processing function
def process_frames(frame_queue_container, processing_event, producer_allowed_event):
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
                        target = "left" if expiry_date_obj < today else "right"
                        print("Moving object to", target)
                        
                        producer_allowed_event.clear()
                        processing_event.clear()

                        with queue_lock:
                            frame_queue_container[0] = queue.Queue(maxsize=10)

                        move_object(target, processing_event, producer_allowed_event)
                except ValueError:
                    print("Invalid date format.")

# Frame capturing function
def capture_frames(cap, frame_queue_container, producer_allowed_event):
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

        time.sleep(0.03)

# Main thread
def main_thread(frame_queue_container, processing_event, producer_allowed_event, cap):
    if not cap.isOpened():
        print("Cannot open camera")
        return

    producer_thread = threading.Thread(target=capture_frames, args=(cap, frame_queue_container, producer_allowed_event))
    consumer_thread = threading.Thread(target=process_frames, args=(frame_queue_container, processing_event, producer_allowed_event))
    producer_thread.daemon = True
    consumer_thread.daemon = True
    producer_thread.start()
    consumer_thread.start()

    while stop_event.is_set():
        time.sleep(0.1)

    cap.release()
    cv2.destroyAllWindows()

# GUI setup
def run_gui():
    app = ctk.CTk()
    app.title("ExpirioBot")
    app.geometry("800x650")

    frame_queue_container = [queue.Queue(maxsize=10)]
    processing_event = threading.Event()
    processing_event.set()

    producer_allowed_event = threading.Event()
    producer_allowed_event.set()

    cap = cv2.VideoCapture(0)

    def update_camera_feed():
        """ Continuously update the camera feed in the GUI """
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # Convert the frame to an image compatible with tkinter
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ctk.CTkImage(light_image=img, size=(540, 380))
                camera_label.configure(image=imgtk)
                camera_label.image = imgtk
        # Call this function again after 10 milliseconds
        camera_label.after(10, update_camera_feed)

    def start_button_command():
        threading.Thread(target=main_thread, args=(frame_queue_container, processing_event, producer_allowed_event, cap)).start()

    def stop_button_command():
        stop_event.clear()

    ctk.CTkLabel(app, text="ExpirioBot Control Panel", font=("Comfortaa", 20)).pack(pady=20)

    # Camera feed label
    camera_label = ctk.CTkLabel(app, text="ExpirioBot Camera Feed", font=("Comfortaa", 18))
    camera_label.pack(pady=20)

    # Start updating the camera feed
    update_camera_feed()

    # Create a frame to center the buttons
    button_frame = ctk.CTkFrame(app)
    button_frame.pack(pady=20)

    # Add buttons to the frame
    start_button = ctk.CTkButton(button_frame, text="Start", command=start_button_command, width=100, fg_color="green")
    start_button.pack(side="left", padx=10, pady=5)

    stop_button = ctk.CTkButton(button_frame, text="Stop", command=stop_button_command, width=100, fg_color="red")
    stop_button.pack(side="left", padx=10, pady=5)

    resume_button = ctk.CTkButton(app, text="Resume", width=100, fg_color="orange")
    resume_button.pack(side="top", padx=10, pady=5)

    app.mainloop()

if __name__ == "__main__":
    try:
        run_gui()
    finally:
        del Arm  # Release DOFBOT object