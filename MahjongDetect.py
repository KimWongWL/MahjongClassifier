import os
import sys
import argparse
import glob
import time

import cv2
import numpy as np
from ultralytics import YOLO

# Define and parse user input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--model', help='Path to YOLO model file (example: "runs/detect/train/weights/best.pt")',
                    required=True)
parser.add_argument('--source', help='Image source, can be image file ("test.jpg"), image folder ("test_dir")', 
                    required=True)
parser.add_argument('--threshold', help='Minimum confidence threshold for displaying detected objects (example: "0.4")',
                    default=0.2)
parser.add_argument('--resolution', help='Resolution in WxH to display inference results at (example: "640x480"), \
                    otherwise, match source resolution',
                    default=None)
parser.add_argument('--showRes', help='show the result of the dectection in a new window',
                    default=False)
parser.add_argument('--showAll', help='show the result below the threshold with black bounding box',
                    default=False)
parser.add_argument('--ROI', help='Adjust the ROI (example: top-left (100,100), bottom-right (500,400)), \
                    otherwise, detect on the whole image',
                    nargs=4, type=int, metavar=('x1', 'y1', 'x2', 'y2'),
                    default=(-1,-1,-1,-1)) # Default ROI is the whole image
parser.add_argument('--ignore', help='Ignore area: specify as x1 y1 x2 y2. Can be used multiple times.',
                    nargs=4, type=int, metavar=('x1', 'y1', 'x2', 'y2'),
                    action='append',
                    default=[])
args = parser.parse_args()


# Parse user inputs
model_path = args.model
img_source = args.source
min_threshold = args.threshold
user_res = args.resolution
show_res = args.showRes
show_all = args.showAll
roi_x1, roi_y1, roi_x2, roi_y2 = args.ROI
ignore_areas = args.ignore

# validate the ignore area values
for area in ignore_areas:
    if len(area) != 4:
        # delete the area if it is not a valid ignore area
        ignore_areas.remove(area)
    if area[0] >= area[2] or area[1] >= area[3]:
        print('ERROR: Invalid ignore area coordinates specified. Please try again.')
        sys.exit(1)

# sort the ignore areas by x1, y1
if len(ignore_areas) > 2:
    ignore_areas.sort(key=lambda x: (x[0], x[1]))

# Check if model file exists and is valid
if (not os.path.exists(model_path)):
    print('ERROR: Model path is invalid or model was not found. Make sure the model filename was entered correctly.')
    sys.exit(1)

# Load the model into memory and get labemap
model = YOLO(model_path, task='detect')
labels = model.names

# Parse input to determine if image source is a file, folder
img_ext_list = ['.jpg','.JPG','.jpeg','.JPEG','.png','.PNG','.bmp','.BMP']

if os.path.isdir(img_source):
    source_type = 'folder'
elif os.path.isfile(img_source):
    _, ext = os.path.splitext(img_source)
    if ext in img_ext_list:
        source_type = 'image'
    else:
        print(f'ERROR: File extension {ext} is not supported.')
        sys.exit(1)
else:
    print(f'ERROR: Input {img_source} is invalid. Please try again.')
    sys.exit(1)

# Parse user-specified display resolution
resize = False
if user_res:
    resize = True
    resW, resH = int(user_res.split('x')[0]), int(user_res.split('x')[1])

# Load or initialize image source
if source_type == 'image':
    imgs_list = [img_source]
elif source_type == 'folder':
    imgs_list = []
    filelist = glob.glob(img_source + '/*')
    for file in filelist:
        _, file_ext = os.path.splitext(file)
        if file_ext in img_ext_list:
            imgs_list.append(file)

# Set bounding box colors (using the Tableu 10 color scheme)
bbox_colors = [(164,120,87), (68,148,228), (93,97,209), (178,182,133), (88,159,106), 
              (96,202,231), (159,124,168), (169,162,241), (98,118,150), (172,176,184)]

# Initialize control and status variables
img_count = 0

# Begin inference loop
while True:

    t_start = time.perf_counter()

    # Load frame from image source
    if img_count >= len(imgs_list):
        print('All images have been processed. Exiting program.')
        sys.exit(0)
    img_filename = imgs_list[img_count]
    frame = cv2.imread(img_filename)
    img_count = img_count + 1

    # Resize frame to desired display resolution
    if resize == True:
        frame = cv2.resize(frame,(resW,resH))
    else:
        resW, resH = frame.shape[1], frame.shape[0]

    # Check if ROI is specified, if so, crop the frame to the ROI
    if roi_x1 >= 0 and roi_y1 >= 0 and roi_x2 >= 0 and roi_y2 >= 0:
        # return error if ROI coordinates are invalid
        if roi_x1 >= roi_x2 or roi_y1 >= roi_y2:
            print('ERROR: Invalid ROI coordinates specified. Please try again.')
            sys.exit(1)

        if resW <= 0 or resH <= 0:
            print('ERROR: Invalid image size. Please check the input image.')
            sys.exit(1)

        # Crop the frame to the specified ROI
        frame = frame[roi_y1:roi_y2, roi_x1:roi_x2]

    # Run inference on frame
    results = model(frame, verbose=False)

    # Extract results
    detections = results[0].boxes

    # Initialize variable for basic object counting example
    object_count = 0

    # Go through each detection and get bbox coords, confidence, and class
    for i in range(len(detections)):

        # count the number of objects in the image
        object_count +=  1

        # Get bounding box coordinates
        # Ultralytics returns results in Tensor format, Converte to a regular Python array
        xyxy_tensor = detections[i].xyxy.cpu() # Detections in Tensor format in CPU memory
        xyxy = xyxy_tensor.numpy().squeeze() # Convert tensors to Numpy array
        xmin, ymin, xmax, ymax = xyxy.astype(int) # Extract individual coordinates and convert to int

        if not user_res:
            resW, resH = frame.shape[1], frame.shape[0] # Default to source resolution

        # Get bounding box confidence
        conf = detections[i].conf.item()
        if conf < float(min_threshold) and not show_all:
            # Skip detections below the confidence threshold
            continue

        # check if the bounding box area is within the ignore areas
        ignore = False
        for area in ignore_areas:
            if not (xmax < area[0] or xmin > area[2] or ymax < area[1] or ymin > area[3]):
                # Bounding box is within the ignore area
                ignore = True
                break
        if ignore:
            continue

        # Get bounding box class ID and name
        classidx = int(detections[i].cls.item())
        classname = labels[classidx]

        # print all detections
        # print(f'Detection {i}: Class: {classname}, Confidence: {conf:.2f}, BBox: ({xmin}, {ymin}), ({xmax}, {ymax})')
        print(f'BBox: ({xmin}, {ymin}), ({xmax}, {ymax}), Class: {classname}')

        if show_res:
            # draw label with class name and confidence in 3 decimal places
            color = bbox_colors[classidx % 10]
            text_color = (0, 0, 0)
            if show_all and conf < float(min_threshold):
                # Draw bounding box for objects below the threshold
                color = (0, 0, 0)
                text_color = (255, 255, 255)
            cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), color, 2)
            s_conf = f'{conf:.3f}' # Format confidence to 3 decimal places
            label = f'{classname} : {s_conf}'
            labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1) # Get font size
            label_ymin = max(ymin, labelSize[1] + 10) # Make sure not to draw label too close to top of window
            cv2.rectangle(frame, (xmin, label_ymin-labelSize[1]-10), (xmin+labelSize[0], label_ymin+baseLine-10), color, cv2.FILLED) # Draw white box to put label text in
            cv2.putText(frame, label, (xmin, label_ymin-7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1) # Draw label text
            # draw ignore areas if specified
            for area in ignore_areas:
                cv2.rectangle(frame, (area[0], area[1]), (area[2], area[3]), (0,0,255), 2)
                cv2.putText(frame, 'Ignore Area', (area[0], area[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

    if show_res:
        # Display detection results
        cv2.putText(frame, f'Number of objects: {object_count}', (10,resH - 10), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,255,255), 2) # Draw total number of detected objects
        cv2.imshow('YOLO detection results',frame) # Display image

    # Get user input
    key = cv2.waitKey()
    if key == ord('q') or key == ord('Q'): # Press 'q' to quit
        break
    elif key == ord('s') or key == ord('S'): # Press 's' to pause inference
        cv2.waitKey()
    elif key == ord('p') or key == ord('P'): # Press 'p' to save a picture of results on this frame
        cv2.imwrite('capture.png',frame)

# Clean up
cv2.destroyAllWindows()
sys.exit(0)