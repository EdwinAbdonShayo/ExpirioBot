import cv2
from PIL import Image
import pytesseract
import re
from datetime import datetime
import threading
import time
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

# Positions for different actions
p_front = [90, 60, 50, 50, 90]  # Front position
p_right = [0, 60, 50, 50, 90]   # Right position
p_left = [180, 60, 50, 50, 90]  # Left position
p_top = [90, 80, 50, 50, 90]    # Top (transition) position
p_rest = [90, 90, 0, 5, 90]     # Rest position

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

# Main function without queue
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    last_processed_date = None  # To track the last processed date

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Preprocess the frame
        processed_frame = preprocess_image(frame)
        image_path = "image.jpg"
        cv2.imwrite(image_path, processed_frame)
        print(f"Saved: {image_path}")

        # Extract expiry date
        expiry_date = extract_expiry_date(image_path)
        if expiry_date:
            try:
                formatted_date = expiry_date.replace('.', '/')
                expiry_date_obj = datetime.strptime(formatted_date, "%d/%m/%Y")
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

                    # Move the object
                    move_object(target, processing_event=None, producer_allowed_event=None)  # Adjust move_object if necessary
                else:
                    print("No new date detected. Skipping action.")
            except ValueError:
                print("Invalid date format. Please check the extracted date.")

        # Display the live camera feed
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
