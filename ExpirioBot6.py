import cv2
from PIL import Image
import pytesseract
import re
from datetime import datetime
import threading
import queue
import time
from Arm_Lib import Arm_Device

# Initialize DOFBOT
Arm = Arm_Device()
time.sleep(0.1)

# (Include your arm movement functions here)

# Function to preprocess the image
def preprocess_image(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

# Function to extract text and expiry date
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

# Consumer thread: Processes frames from the queue
def process_frames(frame_queue, processing_event, producer_allowed_event):
    last_processed_date = None  # Initialize last processed date
    while True:
        # Wait until processing is allowed
        processing_event.wait()

        if not frame_queue.empty():
            frame = frame_queue.get()
            image_path = "image.jpg"
            processed_frame = preprocess_image(frame)
            cv2.imwrite(image_path, processed_frame)
            print(f"Saved: {image_path}")
            
            expiry_date = extract_expiry_date(image_path)
            if expiry_date:
                try:
                    formatedDate = expiry_date.replace('.', '/')
                    expiry_date_obj = datetime.strptime(formatedDate, "%d/%m/%Y")
                    today = datetime.today()
                    
                    # Check if the date has changed since last processing
                    if last_processed_date != expiry_date_obj:
                        # Determine the arm movement based on the expiry status
                        if expiry_date_obj < today:
                            target = "left"
                            print("The product has expired!")
                        else:
                            target = "right"
                            print("The product is valid.")
                        
                        # Update the last processed date
                        last_processed_date = expiry_date_obj
                        
                        # Pause producer and consumer, empty the queue
                        producer_allowed_event.clear()
                        processing_event.clear()

                        while not frame_queue.empty():
                            try:
                                discarded_frame = frame_queue.get_nowait()
                                print("Discarded a frame from the queue.")
                            except queue.Empty:
                                break

                        # Call the arm movement function
                        move_object(target, processing_event, producer_allowed_event)
                    else:
                        print("No new date detected. Skipping action.")
                except ValueError:
                    print("Invalid date format. Please check the extracted date.")

# Producer thread: Captures frames and adds to the queue
def capture_frames(cap, frame_queue, producer_allowed_event):
    while True:
        producer_allowed_event.wait()  # Wait until producer is allowed to add frames
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        if frame_queue.full():
            try:
                discarded_frame = frame_queue.get_nowait()
                print("Discarded oldest frame to make space.")
            except queue.Empty:
                pass
        frame_queue.put(frame)
        print("Added a frame to the queue.")
        time.sleep(0.03)  # Slight delay to simulate real-time capture

# Main function
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    frame_queue = queue.Queue(maxsize=10)  # Shared queue for frames
    processing_event = threading.Event()    # Event to control processing
    processing_event.set()                   # Start with processing enabled

    producer_allowed_event = threading.Event()  # Event to control producer
    producer_allowed_event.set()                 # Start with producer allowed

    # Start the producer and consumer threads
    producer_thread = threading.Thread(target=capture_frames, args=(cap, frame_queue, producer_allowed_event))
    consumer_thread = threading.Thread(target=process_frames, args=(frame_queue, processing_event, producer_allowed_event))
    producer_thread.daemon = True
    consumer_thread.daemon = True
    producer_thread.start()
    consumer_thread.start()

    # Display the live camera feed
    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    finally:
        del Arm  # Release DOFBOT object
