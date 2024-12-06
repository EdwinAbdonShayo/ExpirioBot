import cv2
import numpy as np
from tensorflow.keras.models import load_model

# Initialize the model
def initializePredictionModel():
    model = load_model('myModel.h5')
    return model

# Preprocess the image (grayscale, blur, threshold)
def preProcess(img):
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Convert image to grayscale
    imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)  # Apply Gaussian blur
    imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, 1, 1, 11, 2)  # Apply adaptive threshold
    return imgThreshold

# Get predictions for the digits in the image
def getPrediction(img, model):
    # Ensure the image is resized to 28x28
    img = cv2.resize(img, (28, 28))  # Resize to 28x28
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Convert to grayscale if not already
    img = img / 255.0  # Normalize the pixel values
    
    # Reshape the image to match the model input shape
    img = img.reshape(1, 28, 28, 1)  # Reshape to (1, 28, 28, 1) for model input

    # Get the prediction
    predictions = model.predict(img)
    classIndex = np.argmax(predictions)  # Get the index of the highest predicted value
    probabilityValue = np.max(predictions)  # Get the highest probability

    if probabilityValue > 0.8:  # Only consider predictions with high confidence
        return classIndex
    else:
        return None  # Return None if the prediction is not confident enough

# Main function to capture video and process frames
def main():
    # Load the model
    model = initializePredictionModel()
    
    # Start capturing from the camera
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()  # Read a frame from the camera
        if not ret:
            break
        
        # Preprocess the frame for digit detection
        imgThreshold = preProcess(frame)
        
        # Find contours in the thresholded image
        contours, _ = cv2.findContours(imgThreshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 100:  # Filter out small contours that are unlikely to be digits
                x, y, w, h = cv2.boundingRect(cnt)  # Get the bounding box of the contour
                
                # Extract the region of interest (ROI) for digit recognition
                roi = frame[y:y+h, x:x+w]
                
                # Get the predicted digit from the model
                digit = getPrediction(roi, model)
                
                if digit is not None:
                    # Print the recognized digit to the terminal
                    print(f'Recognized digit: {digit}')
        
        # Display the thresholded image (for debugging)
        cv2.imshow('Thresholded Image', imgThreshold)
        
        # Break the loop on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release the camera and close all windows
    cap.release()
    cv2.destroyAllWindows()

# Run the main function
if __name__ == "__main__":
    main()
