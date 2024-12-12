#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import cv2
import numpy as np
from Arm_Lib import Arm_Device

# --- Initialize Yahboom Dofbot ---
dofbot = Arm_Device()
time.sleep(0.1)  # Allow initialization

# --- Define Dofbot Movement Functions ---
# Clamp the object (open or close clamp)
def arm_clamp(enable):
    """
    Controls the clamp to pick up or release an object.
    :param enable: 0 to release, 1 to clamp.
    """
    dofbot.Arm_serial_servo_write(6, 130 if enable else 60, 400)
    time.sleep(0.5)

# Move the robotic arm to a specified position
def arm_move(position, duration=500):
    """
    Moves the robotic arm to a specific position.
    :param position: List of servo angles for the position.
    :param duration: Duration of the movement in milliseconds.
    """
    for i, angle in enumerate(position):
        servo_id = i + 1
        dofbot.Arm_serial_servo_write(servo_id, angle, duration)
        time.sleep(0.01)
    time.sleep(duration / 1000.0)

# --- Define Predefined Positions ---
p_front = [90, 60, 50, 50, 90]  # Picking position (front)
p_left = [180, 60, 50, 50, 90]  # Left bin position
p_right = [0, 60, 50, 50, 90]   # Right bin position
p_top = [90, 80, 50, 50, 90]    # Transition position
p_rest = [90, 130, 0, 0, 90]    # Rest/idle position

def move_object(target):
    """
    Executes the pick-and-place operation to move an object.
    :param target: 'left' or 'right' indicating where to place the object.
    """
    if target not in ['left', 'right']:
        print("Invalid target! Use 'left' or 'right'.")
        return

    # Pick the object
    arm_clamp(0)  # Open clamp
    arm_move(p_front, 1000)  # Move to the front position
    arm_clamp(1)  # Clamp the object

    # Transition to top position
    arm_move(p_top, 1000)

    # Move to the target position
    if target == 'left':
        arm_move(p_left, 1000)
    elif target == 'right':
        arm_move(p_right, 1000)

    # Release the object
    arm_clamp(0)  # Open clamp to release
    arm_move(p_top, 1000)  # Return to top position
    arm_move(p_rest, 1000)  # Move to rest position

# --- YOLO Object Detection ---
class YOLODetector:
    def __init__(self, config_file, weights_file, labels_file):
        """
        Initializes the YOLO detector with model files.
        :param config_file: Path to the YOLO config file.
        :param weights_file: Path to the YOLO weights file.
        :param labels_file: Path to the labels file.
        """
        self.net = cv2.dnn.readNetFromDarknet(config_file, weights_file)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        with open(labels_file, 'r') as file:
            self.labels = file.read().strip().split('\n')
        self.confidence_threshold = 0.5

    def detect_objects(self, frame):
        """
        Detects objects in a given frame.
        :param frame: Input image for detection.
        :return: List of detected objects with labels and bounding boxes.
        """
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        layer_names = [self.net.getLayerNames()[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]
        outputs = self.net.forward(layer_names)

        detections = []
        h, w = frame.shape[:2]
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > self.confidence_threshold:
                    box = detection[:4] * np.array([w, h, w, h])
                    (center_x, center_y, width, height) = box.astype('int')
                    x = int(center_x - (width / 2))
                    y = int(center_y - (height / 2))
                    detections.append({
                        "label": self.labels[class_id],
                        "confidence": float(confidence),
                        "x": x,
                        "y": y,
                        "width": int(width),
                        "height": int(height)
                    })
        return detections

# --- Main Loop ---
def main():
    """
    Main function to process the camera feed, detect objects, and control the robotic arm.
    """
    yolo = YOLODetector("cfg/yolov4.cfg", "weights/yolov4.weights", "data/coco.names")
    cap = cv2.VideoCapture(0)  # Initialize camera feed

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera feed not accessible!")
            break

        # Perform object detection
        detections = yolo.detect_objects(frame)

        for detection in detections:
            label = detection["label"].lower()
            if label == "expired":
                print("Expired product detected. Moving to the left bin.")
                move_object("left")
            else:
                print("Valid product detected. Moving to the right bin.")
                move_object("right")

        # Display the camera feed with bounding boxes
        for detection in detections:
            x, y, w, h = detection['x'], detection['y'], detection['width'], detection['height']
            label = detection['label']
            confidence = detection['confidence']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} ({confidence:.2f})", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Dofbot Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Quit on 'q' key press
            break

    cap.release()
    cv2.destroyAllWindows()
    del dofbot  # Release the Dofbot resources

if __name__ == "__main__":
    main()
