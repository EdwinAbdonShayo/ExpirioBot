#!/usr/bin/env python3
# coding=utf-8

import time
from Arm_Lib import Arm_Device  # Yahboom Dofbot SDK
import cv2
import numpy as np
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

# Initialize DOFBOT
Arm = Arm_Device()
time.sleep(0.1)

# YOLO Detector for object classification
class YOLODetector:
    """
    A class to handle YOLO-based object detection.
    """
    def __init__(self, config_path, weights_path, names_path):
        self.net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        with open(names_path, 'r') as f:
            self.labels = f.read().strip().split('\n')

    def detect(self, frame):
        """
        Perform object detection on a given frame.
        """
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        layer_names = self.net.getLayerNames()
        output_layers = [layer_names[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]
        outputs = self.net.forward(output_layers)

        h, w = frame.shape[:2]
        detections = []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:  # Threshold for confidence
                    box = detection[0:4] * np.array([w, h, w, h])
                    (center_x, center_y, width, height) = box.astype("int")
                    x = int(center_x - (width / 2))
                    y = int(center_y - (height / 2))
                    detections.append({
                        "label": self.labels[class_id],
                        "confidence": float(confidence),
                        "x": x, "y": y, "width": int(width), "height": int(height)
                    })
        return detections

# Control DOFBOT arm movement and actions
class DofbotController:
    def __init__(self, arm):
        self.arm = arm

        # Predefined positions
        self.p_front = [90, 60, 50, 50, 90]  # Front position
        self.p_right = [0, 60, 50, 50, 90]   # Right position
        self.p_left = [180, 60, 50, 50, 90]  # Left position
        self.p_top = [90, 80, 50, 50, 90]    # Top position
        self.p_rest = [90, 130, 0, 0, 90]    # Rest position

    def arm_clamp(self, enable):
        """
        Control the clamp to pick or release an object.
        """
        if enable == 0:  # Open clamp
            self.arm.Arm_serial_servo_write(6, 60, 400)
        else:  # Close clamp
            self.arm.Arm_serial_servo_write(6, 130, 400)
        time.sleep(0.5)

    def arm_move(self, position, s_time=500):
        """
        Move the arm to a specific position.
        """
        for i in range(5):
            id = i + 1
            if id == 5:
                time.sleep(0.1)
                self.arm.Arm_serial_servo_write(id, position[i], int(s_time * 1.2))
            elif id == 1:
                self.arm.Arm_serial_servo_write(id, position[i], int(3 * s_time / 4))
            else:
                self.arm.Arm_serial_servo_write(id, position[i], int(s_time))
            time.sleep(0.01)
        time.sleep(s_time / 1000)

    def move_object(self, target):
        """
        Perform the pick-and-place operation to move the object to the target position.
        """
        if target not in ['left', 'right']:
            rospy.logerr("Invalid target! Use 'left' or 'right'.")
            return

        # Move to front to pick up the object
        self.arm_clamp(0)  # Open clamp
        self.arm_move(self.p_front, 1000)  # Move to front position
        self.arm_clamp(1)  # Clamp object

        # Move to top position
        self.arm_move(self.p_top, 1000)

        # Move to target position
        if target == 'left':
            self.arm_move(self.p_left, 1000)
        elif target == 'right':
            self.arm_move(self.p_right, 1000)

        # Release the object
        self.arm_clamp(0)

        # Return to rest position
        self.arm_move(self.p_top, 1000)
        self.arm_move(self.p_rest, 1000)

def process_camera_and_move():
    """
    Continuously process the camera stream to detect objects and move them based on their label.
    """
    rospy.init_node('dofbot_object_sorter', anonymous=True)
    bridge = CvBridge()
    cap = cv2.VideoCapture(0)  # Replace with your camera index if not 0

    yolo = YOLODetector("cfg/yolov4.cfg", "weights/yolov4.weights", "data/coco.names")
    controller = DofbotController(Arm)

    while not rospy.is_shutdown():
        ret, frame = cap.read()
        if not ret:
            rospy.logerr("Failed to capture frame from camera!")
            continue

        # Detect objects
        detections = yolo.detect(frame)
        rospy.loginfo(f"Detections: {detections}")

        for detection in detections:
            label = detection["label"]
            confidence = detection["confidence"]

            # Determine movement based on the detected label
            if label == 'expired' and confidence > 0.5:
                rospy.loginfo("Expired product detected. Moving to left.")
                controller.move_object('left')
            elif confidence > 0.5:
                rospy.loginfo("Valid product detected. Moving to right.")
                controller.move_object('right')

        # Show the frame with detections (optional for debugging)
        for detection in detections:
            x, y, w, h = detection['x'], detection['y'], detection['width'], detection['height']
            label = detection['label']
            confidence = detection['confidence']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{label}: {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        process_camera_and_move()
    except rospy.ROSInterruptException:
        pass
    finally:
        del Arm  # Release DOFBOT
