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
parser.add_argument('--game_wind', help='Wind for this game, can be 1, 2, 3, or 4 (1: east, 2: south, 3: west, 4: north)',
                    default=-1)
parser.add_argument('--seat_wind', help='Wind for this seat, can be 1, 2, 3, or 4 (1: east, 2: south, 3: west, 4: north)',
                    default=-1)
parser.add_argument('--seat', help='Seat : 0 1 2 3 seat off to the dealer, in clockwise direction',
                    default=-1)
args = parser.parse_args()

# Parse user inputs
img_source = args.source
min_threshold = args.threshold
roi_x1, roi_y1, roi_x2, roi_y2 = args.ROI
ignore_areas = args.ignore
game_wind = args.game_wind
seat_wind = args.seat_wind
seat = args.seat

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

#################################################################################################################
# prepare for data extraction
#################################################################################################################

detected_tiles = [0] * 34   # non-flower tiles
detected_flowers = [0] * 8
detected_dragon = False
detected_dragon_set = [0] * 2   # pong / kong 
detected_wind = False
detected_winds_set = [0] * 2    # pong / kong 
words_only = True
melds = [0] * (len(Meld) + 1)
eye_type = -1  # -1: not detected, 0: common eye, 1: orphan eye, 2: dragon eye, 3: wind eye
orphan = True
one_suit = True
last_suit = -1
odd_flowers = 0
even_flowers = 0
nice_flowers = 0
cool_wind = 0   
door_free = False # in test

# extract the melds from the detected tiles
# dont consider the flowers in this step
saved_tiles = []
for i in range(detections.__len__()):
    # get the detection
    detection = detections[i]
    class_name = detection['class']
    if class_name in Flower.__members__:
        flower_index = Flower[class_name].value
        detected_flowers[flower_index] += 1
        # flower are seperated into odd and even
        if flower_index % 2 == 1:
            odd_flowers += 1
        else:
            even_flowers += 1
        # flower or season
        if flower_index == seat or flower_index / 2 == seat:
            nice_flowers += 1
        continue

    if class_name in Tile.__members__:
        tile = Tile[class_name].value
        detected_tiles[tile] += 1
    else:
        print(f"Error: Detected unknown tile class '{class_name}'")
        sys.exit(1)
    saved_tiles.append(tile)

    # check if its one suit
    if one_suit and tile < 30:
        if last_suit == -1:
            last_suit = tile / 10
        else:
            if last_suit != tile / 10:
                one_suit = False

    # check if its word
    if tile < 30:
        words_only = False
        # check if its orphan tile
        if orphan and tile % 10 != 1 and tile % 10 != 9:
            orphan = False

    if is_wind(tile):
        detected_wind = True
        if game_wind != -1 and tile == 40 + game_wind:
            cool_wind += 1
        if seat_wind != -1 and tile == 40 + seat_wind:
            cool_wind += 1

    # check for melds when the len of saved_tiles is 3 or more
    if saved_tiles.__len__() == 3:
        # check for chow melds
        if saved_tiles[-1] - saved_tiles[-2] == 1 and saved_tiles[-2] - saved_tiles[-3] == 1:
            melds[Meld.CHOW.value] += 1
            saved_tiles = []
            orphan = False
            continue
        
    if saved_tiles.__len__() > 3:

        # check for kong melds
        if saved_tiles[0] == saved_tiles[1] == saved_tiles[2] == saved_tiles[3]:
            melds[Meld.KONG.value] += 1
            saved_tiles = []
            if is_dragon(saved_tiles[0]):
                detected_dragon_set[1] += 1
                detected_dragon = True
            elif is_wind(saved_tiles[0]):
                detected_winds_set[1] += 1
                detected_wind = True
        # check for pong melds
        elif saved_tiles[0] == saved_tiles[1] == saved_tiles[2]:
            melds[Meld.PONG.value] += 1
            saved_tiles = saved_tiles[3:]
            if is_dragon(saved_tiles[0]):
                detected_dragon_set[0] += 1
                detected_dragon = True
            elif is_wind(saved_tiles[0]):
                detected_winds_set[0] += 1
                detected_wind = True
        elif not orphan:
            print("Error: saved_tiles didn't match any melds, but has", saved_tiles.__len__(), "tiles left:", saved_tiles)
            sys.exit(1)

#should have 2 tiles left in saved_tiles, but maybe its 13 orphan or other special case
if saved_tiles.__len__() == 2:
    # eyes must be identical
    if saved_tiles[0] != saved_tiles[1]:
        print("Error: saved_tiles should have 2 identical tiles left, but has", saved_tiles)
        sys.exit(1)

    # if its dragon or wind, it is not common eye
    if is_dragon(saved_tiles[0]) :
        eye_type = 2
    elif is_wind(saved_tiles[0]):
        eye_type = 3
    elif saved_tiles[0] % 10 == 1 or saved_tiles[0] % 10 == 9:
        eye_type = 1
    else:
        eye_type = 0
# else:
    # print("Error: saved_tiles should have 2 tiles left, but has", saved_tiles.__len__())

#################################################################################################################
# Main calculation
#################################################################################################################
Faan = 0

# flower first
if odd_flowers + even_flowers == 0:
    Faan += 1
elif odd_flowers + even_flowers == 7:
    Faan == 3
    print("Success: Calculation completed with Seven Flowers.")
    print("Faan:", Faan)
    sys.exit(0)
elif odd_flowers + even_flowers == 8:
    Faan == 8
    print("Success: Calculation completed with All Flowers.")
    print("Faan:", Faan)
    sys.exit(0)
elif odd_flowers == 4 or even_flowers == 4:
    Faan += 2

# special case
if saved_tiles.__len__() != 2:
    # Thirteen Orphans Pog champ
    total_orphans = 0
    total_orphans += detected_tiles[1] + detected_tiles[9] + \
                    detected_tiles[11] + detected_tiles[19] + \
                    detected_tiles[21] + detected_tiles[29] + \
                    detected_tiles[31] + detected_tiles[32] + detected_tiles[33] + \
                    detected_tiles[41] + detected_tiles[42] + detected_tiles[43] + detected_tiles[44]

    # for i in range(0, 3):
    #     total_orphans += detected_tiles[10 * i + 1]
    #     total_orphans += detected_tiles[10 * i + 9]
    #     total_orphans += detected_tiles[30 + i]
    #     total_orphans += detected_tiles[40 + i]
    # total_orphans += detected_tiles[44]
    
    if total_orphans == 14:
        Faan = 13
        print("Success: Calculation completed with Thirteen Orphans.")
        print("Faan:", Faan)
        sys.exit(0)
    else:
         print("Error: invalid number of tiles :", saved_tiles.__len__())
if words_only:
    Faan == 10
    print("Success: Calculation completed with words only.")
    print("Faan:", Faan)
    sys.exit(0)
if orphan:
    if eye_type == 3 and check_triplets(melds) and not detected_dragon and not detected_wind:
        Faan == 10
        print("Success: Calculation completed with all orphan.")
        print("Faan:", Faan)
        sys.exit(0)
    if one_suit and door_free and detected_tiles[last_suit * 10 + 1] >= 3 and detected_tiles[last_suit * 10 + 9] >= 3:
        owned_tile = True
        for i in range(2 , 9):
            if detected_tiles[last_suit * 10 + i] == 0:
                owned_tile == False
                break
        if owned_tile:
            Faan == 10
            print("Success: Calculation completed with Nine Gates.")
            print("Faan:", Faan)
            sys.exit(0)
if melds[1] == 4:
    Faan == 13
    print("Success: Calculation completed with All Kongs.")
    print("Faan:", Faan)
    sys.exit(0)
# end special case

# wind
Faan += cool_wind

# orphan
if orphan and eye_type == 3 and (detected_dragon or detected_wind ):
    Faan += 1

# suit
if one_suit:
    if detected_dragon or detected_wind or eye_type == 2 or eye_type == 3:
        Faan += 3
    else:
        Faan += 7

# dragon / wind set
if detected_dragon_set[0] + detected_dragon_set[1] >= 2:
    if eye_type == 2:
        Faan += 5
    else:
        Faan += 8

if detected_winds_set[0] + detected_winds_set[1] >= 2:
    if eye_type == 3:
        Faan += 6
    else:
        Faan == 13
        print("Success: Calculation completed with Great Winds.")
        print("Faan:", Faan)
        sys.exit(0)

# door free
if door_free:
    Faan += 1

# melds
if check_ping(melds):
    Faan += 1
elif check_triplets(melds):
    if door_free:
        Faan += 4   # 1 Faan for door free is calculated before
    else:
        Faan += 3

if Faan < 1:
    print("Error: Invaild Faan calculated")
    print("Faan:", Faan)
    sys.exit(1)

print("Success: Calculation completed")
print("Faan:", Faan)
sys.exit(0)
    