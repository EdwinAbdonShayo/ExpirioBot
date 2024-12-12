import cv2
import base64
from inference_sdk import InferenceHTTPClient

# Create an inference client to interact with the Roboflow API
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="xOq95WwD7YPT7VB1F9KD"
)

# Function to convert image to base64 format
def image_to_base64(image):
    _, img_encoded = cv2.imencode('.jpg', image)  # Encode image as JPEG
    return base64.b64encode(img_encoded).decode('utf-8')  # Convert to base64 and decode as string

# Function to send the base64 image to Roboflow API and get predictions
def get_prediction_from_roboflow(image):
    img_base64 = image_to_base64(image)
    response = CLIENT.infer(img_base64, model_id="fruits-opg9g/1")
    return response

# Open the front camera (webcam)
cap = cv2.VideoCapture(0)

# Check if the webcam is opened properly
if not cap.isOpened():
    print("Error: Could not access the camera.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Get predictions from Roboflow API for the current frame
    predictions = get_prediction_from_roboflow(frame)

    # Display the predicted classes and confidence scores
    if 'predictions' in predictions:
        predicted_classes = predictions['predicted_classes']
        y_offset = 50  # Initial vertical position for displaying text

        for fruit in predicted_classes:
            confidence = predictions['predictions'][fruit]['confidence']
           
            # Add + for ripe, - for rotten based on the class name
            if "ripe" in fruit.lower():
                status = "+"
            elif "rotten" in fruit.lower():
                status = "-"
            else:
                status = ""

            label = f"{fruit} {status}: {confidence:.2f}"
            cv2.putText(frame, label, (50, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += 30  # Move the text down for each prediction
    else:
        # If no predictions are made, display a message
        cv2.putText(frame, "No fruits detected. Try again!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Show the frame with predictions
    cv2.imshow("Real-Time Fruit Detection", frame)

    # Exit the loop when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close any open OpenCV windows
cap.release()
cv2.destroyAllWindows()
