import cv2
import numpy as np
import tensorflow as tf
from keras.models import load_model

# Load pre-trained model
MODEL = load_model("resnet50_full.h5")

# Initialize webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not access the camera.")
    exit()

print("Press SPACE to capture a frame for prediction. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Display the live camera feed
    cv2.imshow("Live Camera Feed", frame)

    # Check for key presses
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):  # Exit if 'q' is pressed
        break

    if key == ord(' '):  # Capture frame when SPACE is pressed
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Resize to 28x28 for the model
        image_resize = cv2.resize(gray, (28, 28))

        # Normalize the pixel values
        image_resize = image_resize / 255.0

        # Reshape to fit the model's input format
        image_reshape = np.reshape(image_resize, [1, 28, 28])

        # Predict the digit
        prediction = MODEL.predict(image_reshape)
        predicted_digit = np.argmax(prediction)

        # Print the predicted digit to the terminal
        print(f"The Predicted digit is {predicted_digit}")

# Release resources
cap.release()
cv2.destroyAllWindows()
