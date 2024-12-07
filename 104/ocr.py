
# ExpirioBot

import cv2
from PIL import Image
import pytesseract
import re
from datetime import datetime
import time

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Function to preprocess the image
def preprocess_image(frame):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply thresholding
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    return binary

# Function to extract text and expiry date
def extract_expiry_date(image_path):
    # Load the image using PIL
    image = Image.open(image_path)
    # Perform OCR
    text = pytesseract.image_to_string(image)
    print("Extracted Text:\n", text)
    
    # Extract expiry date using regex
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
            print("The product has expired!")
            state = 'left'
        else:
            print("The product is valid.")
            state = 'right'
        print(state)
    except ValueError:
        print("Invalid date format. Please check the extracted date.")

# Main function to capture and process the image
def main():
    cap = cv2.VideoCapture(0)

    print("Press 's' to capture an image or 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Display the live camera feed
        cv2.imshow("Camera", frame)

        start_time = time.time()
        while time.time() - start_time < 5:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
            

        # key = cv2.waitKey(1) & 0xFF
        # if key == ord('s'):  # Press 's' to capture
        
        # Save the captured frame
        image_path = "image.jpg"
        processed_frame = preprocess_image(frame)
        cv2.imwrite(image_path, processed_frame)
        print(f"Image saved as {image_path}")

        # Extract expiry date and check validity
        expiry_date = extract_expiry_date(image_path)
        if expiry_date:
            check_expiry(expiry_date)

        # elif key == ord('q'):  # Press 'q' to quit
        #     break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()