# -*- coding: utf-8 -*-
import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from keras_retinanet import models
from keras_retinanet.utils.image import preprocess_image, resize_image
# from retina.utils import visualize_boxes  # Ensure this utility is implemented or provided

MODEL_PATH = 'resnet50_full.h5'

def load_inference_model(model_path='snapshots/resnet.h5'):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    model = models.load_model(model_path, backbone_name='resnet50')
    model = models.convert_model(model)
    model.summary()
    return model

def post_process(boxes, original_img, preprocessed_img):
    """Scale boxes to match the original image size."""
    h, w, _ = preprocessed_img.shape
    h2, w2, _ = original_img.shape
    boxes[:, :, 0] = boxes[:, :, 0] / w * w2
    boxes[:, :, 2] = boxes[:, :, 2] / w * w2
    boxes[:, :, 1] = boxes[:, :, 1] / h * h2
    boxes[:, :, 3] = boxes[:, :, 3] / h * h2
    return np.clip(boxes, 0, max(h2, w2))  # Ensure no boxes exceed image dimensions

if __name__ == '__main__':
    try:
        model = load_inference_model(MODEL_PATH)
    except Exception as e:
        print(f"Error loading model: {e}")
        exit()

    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not access the camera.")
        exit()

    print("Press SPACE to capture a frame for detection. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Display the live camera feed
        cv2.imshow("Live Camera Feed", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit the program
            break

        if key == ord(' '):  # Capture frame when SPACE is pressed
            draw = frame.copy()
            draw_rgb = cv2.cvtColor(draw, cv2.COLOR_BGR2RGB)

            # Preprocess the captured frame
            frame_preprocessed = preprocess_image(frame)
            frame_preprocessed, _ = resize_image(frame_preprocessed)

            # Predict on the frame
            start = time.time()
            boxes, scores, labels = model.predict_on_batch(np.expand_dims(frame_preprocessed, axis=0))
            print("Processing time: {:.2f} seconds".format(time.time() - start))

            # Post-process the predictions
            boxes = post_process(boxes, draw, frame_preprocessed)
            visualize_boxes(draw_rgb, boxes[0], labels[0], scores[0], class_labels=['0', '1', ..., '9'])  # Adjust class labels

            # Display the result using matplotlib
            plt.imshow(draw_rgb)
            plt.show()

    cap.release()
    cv2.destroyAllWindows()
