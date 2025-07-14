import subprocess
import argparse
import sys
import re
import MahjongTile as Mahjong

# calculation functions
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

debug = False
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

if not detections:
    print("Error: No tiles detected.")
    sys.exit(0)

# Sort the detections by x position 
if detections:
    detections.sort(key=lambda x: (x['bbox'][0]))

# check if there is any weird y position difference
tile_height = detections[0]['bbox'][3] - detections[0]['bbox'][1]
for i in range(0, len(detections) - 1):
    y_curr = detections[i]['bbox'][1]
    y_next = detections[i + 1]['bbox'][1]
    if abs(y_curr - y_next) > tile_height * 0.75:
        # skip flower and season
        if detections[i]['class'].first() == 'f' or detections[i]['class'].first() == 's':
            continue
        # check if there is a tile at right instead
        for j in range(2, min(4, len(detections) - i - 1 - 2)):
            if abs(detections[i + j]['bbox'][1] - y_curr) < tile_height * 0.75 and \
                detections[i + j]['class'].first() == detections[i]['class'].first():
                print("need swap\n")
                # put j tiles after i to i + j
                # if i = 2, j = 2, 3th and 4th -> 5th and 6th | ori 5th and 6th -> 3th and 4th
                for k in range(i, i + j + 1):
                    print(f"Tile {k}: {detections[k]['class']} at {detections[k]['bbox']}")
                # swap the tiles
                detections[i + 1:i + 1 + j], detections[i + j + 1:i + j + 1 + j] = detections[i + j + 1:i + j + 1 + j], detections[i + 1:i + 1 + j]
                # print all detection after swap
                for k in range(i, i + j + 1):
                    print(f"Tile {k}: {detections[k]['class']} at {detections[k]['bbox']}")

                i = i + j + j

#################################################################################################################
# prepare for data extraction
#################################################################################################################

detected_tiles = [0] * 45   # non-flower tiles
detected_flowers = [0] * (8 + 1)
detected_dragon = False
detected_dragon_set = [0] * 2   # pong / kong 
detected_wind = False
detected_winds_set = [0] * 2    # pong / kong 
words_only = True
melds = [0] * (len(Mahjong.Meld) + 1)
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
    if class_name in Mahjong.Flower.__members__:
        flower_index = Mahjong.Flower[class_name].value
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

    if class_name in Mahjong.Tile.__members__:
        tile = Mahjong.Tile[class_name].value
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
        if saved_tiles[0] < 30 and \
           saved_tiles[-1] - saved_tiles[-2] == 1 and saved_tiles[-2] - saved_tiles[-3] == 1:
            melds[Mahjong.Meld.CHOW.value] += 1
            saved_tiles = []
            orphan = False
            continue
        # check for eye
        if saved_tiles[0] == saved_tiles[1] and saved_tiles[1] != saved_tiles[2]:
            # cant have 2 eyes
            if eye_type != -1:
                print("Error: eye already detected, but saved_tiles has 3 tiles left:", saved_tiles)
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

            saved_tiles = saved_tiles[2:]
            continue
    
    if saved_tiles.__len__() > 3:

        # check for kong melds
        if saved_tiles[0] == saved_tiles[1] == saved_tiles[2] == saved_tiles[3]:
            melds[Mahjong.Meld.KONG.value] += 1
            saved_tiles = []
            if is_dragon(saved_tiles[0]):
                detected_dragon_set[1] += 1
                detected_dragon = True
            elif is_wind(saved_tiles[0]):
                detected_winds_set[1] += 1
                detected_wind = True
        # check for pong melds
        elif saved_tiles[0] == saved_tiles[1] == saved_tiles[2]:
            melds[Mahjong.Meld.PONG.value] += 1
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

#################################################################################################################
# Main calculation
#################################################################################################################
Faan = 0

# flower first
if odd_flowers + even_flowers == 0:
    Faan += 1
elif odd_flowers + even_flowers == 7:
    Faan = 3
    print("Success: Calculation completed with Seven Flowers.")
    print("Faan:", Faan)
    sys.exit(0)
elif odd_flowers + even_flowers == 8:
    Faan = 8
    print("Success: Calculation completed with All Flowers.")
    print("Faan:", Faan)
    sys.exit(0)
elif odd_flowers == 4 or even_flowers == 4:
    Faan += 2

# special case
if orphan:
    # Thirteen Orphans Pog champ
    total_orphans = 0
    have_all_orphans = True
    # total_orphans += detected_tiles[1] + detected_tiles[9] + \
    #                 detected_tiles[11] + detected_tiles[19] + \
    #                 detected_tiles[21] + detected_tiles[29] + \
    #                 detected_tiles[31] + detected_tiles[32] + detected_tiles[33] + \
    #                 detected_tiles[41] + detected_tiles[42] + detected_tiles[43] + detected_tiles[44]

    for i in range(0, 3):
        if(detected_tiles[10 * i + 1] < 1):
            have_all_orphans = False
            break
        if(detected_tiles[10 * i + 9] < 1):
            have_all_orphans = False
            break
        if(detected_tiles[30 + i + 1] < 1):
            have_all_orphans = False
            break
        if(detected_tiles[40 + i + 1] < 1):
            have_all_orphans = False
            break

        total_orphans += detected_tiles[10 * i + 1]
        total_orphans += detected_tiles[10 * i + 9]
        total_orphans += detected_tiles[30 + i + 1]
        total_orphans += detected_tiles[40 + i + 1]

    total_orphans += detected_tiles[44]
    if(detected_tiles[44] < 1):
        have_all_orphans = False
    
    if total_orphans == 14 and have_all_orphans:
        Faan = 13
        print("Success: Calculation completed with Thirteen Orphans.")
        print("Faan:", Faan)
        sys.exit(0)

    if eye_type == 1 and melds[Mahjong.Meld.CHOW.value] == 0 and not detected_dragon and not detected_wind:
        Faan = 10
        print("Success: Calculation completed with all orphan.")
        print("Faan:", Faan)
        sys.exit(0)
    if one_suit and door_free and detected_tiles[last_suit * 10 + 1] >= 3 and detected_tiles[last_suit * 10 + 9] >= 3:
        owned_tile = True
        for i in range(2 , 9):
            if detected_tiles[last_suit * 10 + i] == 0:
                owned_tile = False
                break
        if owned_tile:
            Faan = 10
            print("Success: Calculation completed with Nine Gates.")
            print("Faan:", Faan)
            sys.exit(0)

if words_only:
    Faan = 10
    print("Success: Calculation completed with words only.")
    print("Faan:", Faan)
    sys.exit(0)

if melds[Mahjong.Meld.KONG.value] == 4:
    Faan = 13
    print("Success: Calculation completed with All Kongs.")
    print("Faan:", Faan)
    sys.exit(0)
# end special case

# orphan
if orphan and eye_type == 1 and (detected_dragon or detected_wind):
    Faan += 1

# suit
if one_suit:
    if detected_dragon or detected_wind or eye_type == 2 or eye_type == 3:
        Faan += 3
    else:
        Faan += 7

# dragon / wind set
if detected_dragon_set[0] + detected_dragon_set[1] == 3:
        Faan += 8
if detected_dragon_set[0] + detected_dragon_set[1] == 2 and eye_type == 2:
        Faan += 5

if detected_winds_set[0] + detected_winds_set[1] == 4:
        Faan = 13
        print("Success: Calculation completed with Great Winds.")
        print("Faan:", Faan)
        sys.exit(0)
if detected_winds_set[0] + detected_winds_set[1] == 3 and eye_type == 3:
        Faan += 6

# door free
if door_free:
    Faan += 1
# wind
Faan += cool_wind
# dragon
if detected_dragon:
    Faan += detected_dragon_set[0] + detected_dragon_set[1]

# melds
if melds[Mahjong.Meld.PONG.value] == 0 and melds[Mahjong.Meld.KONG.value] == 0: # common
    Faan += 1
elif melds[Mahjong.Meld.CHOW.value] == 0:
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
    