import cv2
from PIL import Image, ImageTk
import pytesseract
import re
from datetime import datetime
import threading
import queue
import time
from Arm_Lib import Arm_Device
import customtkinter as ctk

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

# Positions for different actions
p_front = [90, 60, 50, 50, 90]  # Front position
p_right = [0, 60, 50, 50, 90]   # Right position
p_left = [180, 60, 50, 50, 90]  # Left position
p_top = [90, 80, 50, 50, 90]    # Top (transition) position
p_rest = [90, 90, 0, 5, 90]     # Rest position

# Lock and event initialization
last_processed_date = None
queue_lock = threading.Lock()
processing_event = threading.Event()
producer_allowed_event = threading.Event()

def move_object(target, processing_event, producer_allowed_event):
    """
    Move an object from the front to the specified target side.

    Parameters:
    target (str): 'left' or 'right' indicating the movement direction.
    processing_event (threading.Event): Event to pause AI vision processing.
    producer_allowed_event (threading.Event): Event to control frame production.
    """
    # Pause processing and producer
    processing_event.clear()
    producer_allowed_event.clear()

    try:
        if target not in ['left', 'right']:
            print("Invalid target! Use 'left' or 'right'.")
            return

        # Move to front position to pick object
        arm_clamp_block(0)  # Open clamp
        arm_move(p_front, 1000)  # Move to front position
        arm_clamp_block(1)  # Clamp object

        # Transition to top position
        arm_move(p_top, 1000)

        # Move to target position
        if target == 'left':
            arm_move(p_left, 1000)
        elif target == 'right':
            arm_move(p_right, 1000)

        # Release object
        arm_clamp_block(0)

        # Return to rest position
        arm_move(p_top, 1000)
        arm_move(p_rest, 1000)

    except Exception as e:
        print(f"Error during arm movement: {e}")
    finally:
        # Resume processing and producer
        producer_allowed_event.set()
        processing_event.set()

# Preprocess image function
def preprocess_image(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

# Extract expiry date
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

# Consumer thread: Processes frames
def process_frames(frame_queue_container, processing_event, producer_allowed_event):
    global last_processed_date
    while True:
        # Wait until processing is allowed
        processing_event.wait()

        with queue_lock:
            current_queue = frame_queue_container[0]

        if not current_queue.empty():
            frame = current_queue.get()
            image_path = "image.jpg"
            processed_frame = preprocess_image(frame)
            cv2.imwrite(image_path, processed_frame)
            print(f"Saved: {image_path}")
            
            expiry_date = extract_expiry_date(image_path)
            if expiry_date:
                try:
                    formatted_date = expiry_date.replace('.', '/')
                    expiry_date_obj = datetime.strptime(formatted_date, "%d/%m/%Y")
                    today = datetime.today()
                    
                    # Check if the date has changed since last processing
                    if last_processed_date is None or last_processed_date != expiry_date_obj:
                        # Update the last_processed_date
                        last_processed_date = expiry_date_obj

                        # Determine the arm movement based on the expiry status
                        if expiry_date_obj < today:
                            target = "left"
                            print("The product has expired!")
                        else:
                            target = "right"
                            print("The product is valid.")
                        
                        # Pause producer and consumer
                        producer_allowed_event.clear()
                        processing_event.clear()

                        # Replace the frame queue with a new one
                        with queue_lock:
                            frame_queue_container[0] = queue.Queue(maxsize=10)
                            print("Replaced the frame queue with a new one.")

                        # Call the arm movement function
                        move_object(target, processing_event, producer_allowed_event)
                    else:
                        print("No new date detected. Replacing the queue to continue processing.")

                        # Pause producer and consumer
                        producer_allowed_event.clear()
                        processing_event.clear()

                        # Replace the frame queue with a new one
                        with queue_lock:
                            frame_queue_container[0] = queue.Queue(maxsize=10)
                            print("Replaced the frame queue with a new one.")

                        # Reset last_processed_date to None
                        last_processed_date = None
                        # print("Reset last_processed_date to None.")

                        # Resume producer and consumer
                        producer_allowed_event.set()
                        processing_event.set()

                except ValueError:
                    print("Invalid date format. Please check the extracted date.")

# Producer thread: Captures frames
def capture_frames(cap, frame_queue_container):
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
                    discarded_frame = current_queue.get_nowait()
                except queue.Empty:
                    pass

            current_queue.put(frame)

        time.sleep(0.1)

# GUI and main function
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Camera Feed with Control")
        self.geometry("800x600")
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Cannot open camera")
            return

        self.frame_queue_container = [queue.Queue(maxsize=10)]
        processing_event.clear()
        producer_allowed_event.clear()

        self.start_button = ctk.CTkButton(self, text="Start", fg_color="green", command=self.start_processing)
        self.start_button.pack(pady=10)

        self.stop_button = ctk.CTkButton(self, text="Stop", fg_color="red", command=self.stop_processing)
        self.stop_button.pack(pady=10)

        self.video_label = ctk.CTkLabel(self)
        self.video_label.pack(padx=20, pady=20, fill="both", expand=True)

        self.update_camera_feed()

    def start_processing(self):
        processing_event.set()
        producer_allowed_event.set()

    def stop_processing(self):
        processing_event.clear()
        producer_allowed_event.clear()
        # del Arm

    def update_camera_feed(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (800, 600))
            
            # Convert the frame to a PIL image
            img = Image.fromarray(frame)
            
            # Convert the PIL image to a format usable by CustomTkinter
            tk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 600))
            
            self.video_label.configure(image=tk_img)
            self.video_label.image = tk_img  # Keep a reference to avoid garbage collection

        self.after(10, self.update_camera_feed)

    def on_closing(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.destroy()

if __name__ == "__main__":
    app = App()

    producer_thread = threading.Thread(target=capture_frames, args=(app.cap, app.frame_queue_container))
    consumer_thread = threading.Thread(target=process_frames, args=(app.frame_queue_container,))
    producer_thread.daemon = True
    consumer_thread.daemon = True
    producer_thread.start()
    consumer_thread.start()

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
