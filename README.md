***

# The ExpirioBot

## Overview
ExpirioBot is an automated robotic system designed to identify and sort products based on their expiry dates. The system utilizes computer vision to capture images of products, extract expiry dates using Optical Character Recognition (OCR), and control a robotic arm to move expired or valid products to designated locations.

## Features
- Real-time Image Capture: Captures frames from a live camera feed.
- Expiry Date Detection: Uses OCR to extract expiry dates from product images.
- Robotic Arm Control: Moves products based on their expiry status (expired or valid).
- Threaded Processing: Utilizes threading for efficient frame capture and processing.
- Queue Management: Implements a queue system to handle frames and ensure smooth processing.

## Requirements
- Python 3.x
- OpenCV (cv2)
- Pillow (PIL)
- Pytesseract
- Arm_Lib (custom library for controlling the robotic arm)
- Tesseract OCR installed on your system

## Installation
1. Clone the repository:
   git clone https://github.com/yourusername/Expiry-Sort-DofBot.git
   cd Expiry-Sort-DofBot

2. Install the required Python packages:
   pip install opencv-python pillow pytesseract

3. Install Tesseract OCR:
   - For Windows, download the installer from Tesseract at UB Mannheim (https://github.com/UB-Mannheim/tesseract/wiki).
   - For macOS, use Homebrew:
     brew install tesseract
   - For Linux, use your package manager:
     sudo apt-get install tesseract-ocr

4. Ensure that the Arm_Lib is available in your project directory.

## Usage
1. Connect the robotic arm to your computer.
2. Run the script:
   python ExpirioBot.py
3. The camera feed will open, and the system will start capturing frames.
4. The system will process each frame to detect expiry dates and control the robotic arm accordingly.
5. Press 'q' to quit the application.

## Code Structure
- Arm_Lib.py: Contains the Arm_Device class for controlling the robotic arm.
- ExpirioBot.py: Main script that handles image capture, processing, and robotic arm movement.

### Key Functions
- arm_clamp_block(enable): Controls the clamp of the robotic arm.
- arm_move(p, s_time): Moves the arm to specified positions.
- preprocess_image(frame): Prepares the image for OCR processing.
- extract_expiry_date(image_path): Extracts the expiry date from the image using OCR.
- process_frames(frame_queue_container, processing_event, producer_allowed_event): Processes frames from the queue.
- capture_frames(cap, frame_queue_container, producer_allowed_event): Captures frames from the camera.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- OpenCV for computer vision capabilities.
- Tesseract for OCR functionality.
- The community for support and inspiration.

## Contact
For any inquiries or issues, please contact:
- [Sakina](https://github.com/saki3110)
- [Ishan](https://github.com/ishan23310)  
- [Hans](https://github.com/gt663) 
- [Edwin](https://edwinshayo.com)

***