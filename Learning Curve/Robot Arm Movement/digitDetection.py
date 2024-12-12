import cv2
import numpy as np
from keras.models import load_model
import tensorflow as tf

# Load the pre-trained YOLO model
model = load_model('weights.h5', compile=False)

# Function to preprocess the frame for YOLO
def preprocess_frame(frame, input_size=(416, 416)):
    img = cv2.resize(frame, input_size)
    img = img / 255.0  # Normalize to [0, 1]
    img = np.expand_dims(img, axis=0)  # Add batch dimension
    return img

# Function to draw bounding boxes on the frame
def draw_boxes(frame, boxes, confidences, class_ids, classes):
    for (box, confidence, class_id) in zip(boxes, confidences, class_ids):
        x, y, w, h = box
        label = f"{classes[class_id]}: {confidence:.2f}"
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

# Function to post-process YOLO output
def postprocess_predictions(predictions, frame_shape, confidence_threshold=0.5):
    # Get the height and width of the frame
    h, w = frame_shape[:2]
    
    # List to store bounding boxes, confidences, and class IDs
    boxes, confidences, class_ids = [], [], []
    
    # Assuming YOLO output shape is (batch_size, grid_size, grid_size, num_anchors * (5 + num_classes))
    # Process predictions for each image in the batch
    for pred in predictions[0]:  # Assuming batch_size=1
        for i in range(len(pred)):
            # Extract the class scores (after objectness score)
            scores = pred[i, 5:]  # Class scores are after the 5th element (x, y, w, h, objectness)
            confidence = pred[i, 4]  # Objectness score
            
            # If the confidence score is above the threshold
            if confidence > confidence_threshold:
                class_id = np.argmax(scores)  # Get class with max score
                confidence *= scores[class_id]  # Multiply by class confidence
                
                # Calculate bounding box coordinates (normalize to original image size)
                box = pred[i, :4] * np.array([w, h, w, h])  # Scale to original image size
                bx, by, bw, bh = box.astype("int")
                x = int(bx - (bw / 2))
                y = int(by - (bh / 2))
                
                boxes.append([x, y, int(bw), int(bh)])
                confidences.append(float(confidence))  # Ensure confidence is a float
                class_ids.append(class_id)

    return boxes, confidences, class_ids

# Load the class names (digits 0-9)
classes = [str(i) for i in range(10)]

# Start capturing video from the camera
cap = cv2.VideoCapture(0)

print("Press 'q' to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    input_image = preprocess_frame(frame)
    predictions = model.predict(input_image)

    boxes, confidences, class_ids = postprocess_predictions(predictions, frame.shape)

    # Draw the detected digits on the frame
    draw_boxes(frame, boxes, confidences, class_ids, classes)

    cv2.imshow("Digit Detector", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
