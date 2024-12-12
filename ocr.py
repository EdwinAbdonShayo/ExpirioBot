import cv2
from PIL import Image
import pytesseract
import re
from datetime import datetime
import threading
import queue
import time

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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

# Function to check if the product is expired
def check_expiry(expiry_date):
    try:
        formatedDate = expiry_date.replace('.', '/')
        expiry_date_obj = datetime.strptime(formatedDate, "%d/%m/%Y")
        today = datetime.today()

        if expiry_date_obj < today:
            state = "left"
            print("The product has expired!")
        else:
            print("The product is valid.")
            state = "right"
        print(state)
    except ValueError:
        print("Invalid date format. Please check the extracted date.")

# Producer thread: Captures frames and adds to the queue
def capture_frames(cap, frame_queue):
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        if not frame_queue.full():
            frame_queue.put(frame)
        time.sleep(0.03)  # Slight delay to simulate real-time capture

# Consumer thread: Processes frames from the queue
def process_frames(frame_queue):
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            image_path = "image.jpg"
            processed_frame = preprocess_image(frame)
            cv2.imwrite(image_path, processed_frame)
            print(f"Saved: {image_path}")
            expiry_date = extract_expiry_date(image_path)
            if expiry_date:
                check_expiry(expiry_date)

# Main function
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    frame_queue = queue.Queue(maxsize=10)  # Shared queue for frames

    # Start the producer and consumer threads
    producer_thread = threading.Thread(target=capture_frames, args=(cap, frame_queue))
    consumer_thread = threading.Thread(target=process_frames, args=(frame_queue,))
    producer_thread.daemon = True
    consumer_thread.daemon = True
    producer_thread.start()
    consumer_thread.start()

    # Display the live camera feed
    print("Press 'q' to quit.")
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
