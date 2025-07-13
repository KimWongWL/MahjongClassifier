import subprocess
import argparse
import sys
import re
from enum import Enum

class Tile(Enum):
    b1 = 1
    b2 = 2
    b3 = 3
    b4 = 4
    b5 = 5
    b6 = 6
    b7 = 7
    b8 = 8
    b9 = 9
    c1 = 11
    c2 = 12
    c3 = 13
    c4 = 14
    c5 = 15
    c6 = 16
    c7 = 17
    c8 = 18
    c9 = 19
    d1 = 21
    d2 = 22
    d3 = 23
    d4 = 24
    d5 = 25
    d6 = 26
    d7 = 27
    d8 = 28
    d9 = 29
    dr = 31
    dg = 32
    dw = 33
    we = 41
    ws = 42
    ww = 43
    wn = 44

class Flower(Enum):
    f1 = 1
    f1_s = 1
    f2 = 3
    f2_s = 3
    f3 = 5
    f3_s = 5
    f4 = 7
    f4_s = 7
    s1 = 2
    s1_s = 2
    s2 = 4
    s2_s = 4
    s3 = 6
    s3_s = 6
    s4 = 8
    s4_s = 8

class Meld(Enum):
    CHOW = 1
    PONG = 2
    KONG = 3

# calculation functions
def check_triplets(melds):
    if(melds[Meld.CHOW] >= 1):
        return  False
    return True

def check_ping(melds):
    if melds[Meld.PONG] >= 1 or melds[Meld.KONG] >= 1:
        return False
    return True

def is_dragon(tile):
    return tile > 30 and tile < 34

def is_wind(tile):
    return tile > 40 and tile < 45


# Define and parse user input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--source', help='The image source for mahjong detection, can be image file ("test.jpg"), image folder ("test_dir")', 
                    required=True)
parser.add_argument('--threshold', help='Minimum confidence threshold for displaying detected objects (example: "0.4")',
                    default=0.2)
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
img_source = args.source
min_threshold = args.threshold
roi_x1, roi_y1, roi_x2, roi_y2 = args.ROI
ignore_areas = args.ignore

ROI_args = []
if roi_x1 != -1 and roi_y1 != -1 and roi_x2 != -1 and roi_y2 != -1:
    ROI_args = ["--ROI", str(roi_x1), str(roi_y1), str(roi_x2), str(roi_y2)]

ignore_args = []
if args.ignore:
    ignore_args = ["--ignore"] + [str(coord) for area in ignore_areas for coord in area]

debug = True
debug_args = []
if debug:
    debug_args = ["--showRes", "True", "--resolution", "1280x1280"]

# Call mahjong detect script
result = subprocess.run(
    ["python", "MahjongDetect.py", "--model", "Model/5/my_model.pt", "--source", img_source, "--threshold", min_threshold] + ROI_args + debug_args + ignore_args,
    capture_output=True,
    text=True
)

# Print output
#print("Return code:", result.returncode)
#print("Output:", result.stdout)
#print("Error:", result.stderr)

# Check if the return output contains ERROR prefix
if result.returncode != 0 or "ERROR" in result.stdout:
    print("Error occurred during detection:")
    print(result.stdout)
    sys.exit(0)

# Parse the output to pair array
pattern = r'BBox: \((\d+), (\d+)\), \((\d+), (\d+)\), Class: (\w+)'
matches = re.findall(pattern, result.stdout)

# Create a list of dictionaries to hold the detection results
detections = []
for match in matches:
    xmin, ymin, xmax, ymax, classname = match
    detection = {
        'bbox': [int(xmin), int(ymin), int(xmax), int(ymax)],
        'class': classname
    }
    detections.append(detection)

# Sort the detections by x position
detections.sort(key=lambda x: x['bbox'][0])

detected_tiles = [0] * 34   # non-flower tiles
detected_flowers = [0] * 8
detected_dragon_set = [0] * 2   # pong / kong 
detected_winds_set = [0] * 2    # pong / kong 
melds = [0] * (len(Meld) + 1)
common_eye = -1  # -1: not detected, 0: not common eye, 1: common eye

# extract the melds from the detected tiles
# dont consider the flowers in this step
saved_tiles = []
for i in range(detections.__len__()):
    detection = detections[i]
    class_name = detection['class']
    if class_name in Flower.__members__:
        detected_flowers[Flower[class_name].value] += 1
    elif class_name in Tile.__members__:
        detected_tiles[Tile[class_name].value] += 1
    saved_tiles.append(Tile[class_name].value)

    # check for melds when the len of saved_tiles is 3 or more
    if saved_tiles.__len__() == 3:
        # check for chow melds
        if saved_tiles[-1] - saved_tiles[-2] == 1 and saved_tiles[-2] - saved_tiles[-3] == 1:
            melds[Meld.CHOW.value] += 1
            saved_tiles = []
            continue
        
    if saved_tiles.__len__() > 3:

        # check for kong melds
        if saved_tiles[0] == saved_tiles[1] == saved_tiles[2] == saved_tiles[3]:
            melds[Meld.KONG.value] += 1
            saved_tiles = []
            if is_dragon(saved_tiles[0]):
                detected_dragon_set[1] += 1
            elif is_wind(saved_tiles[0]):
                detected_winds_set[1] += 1

        # check for pong melds
        elif saved_tiles[0] == saved_tiles[1] == saved_tiles[2]:
            melds[Meld.PONG.value] += 1
            saved_tiles = saved_tiles[3:]
            if is_dragon(saved_tiles[0]):
                detected_dragon_set[1] += 1
            elif is_wind(saved_tiles[0]):
                detected_winds_set[1] += 1

#should have 2 tiles left in saved_tiles
if saved_tiles.__len__() == 2:
    if saved_tiles[0] != saved_tiles[1]:
        print("Error: saved_tiles should have 2 identical tiles left, but has", saved_tiles)

    # if its not dragon or wind, it should be common eye
    if not (is_dragon(saved_tiles[0]) or is_wind(saved_tiles[0]) or is_dragon(saved_tiles[1]) or is_wind(saved_tiles[1])):
        common_eye = 1
    else:
        common_eye = 0
else:
    print("Error: saved_tiles should have 2 tiles left, but has", saved_tiles.__len__())
