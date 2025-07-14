import subprocess
import glob
import sys

# search for all image files name in a specified directory
def find_image_files(img_source):
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'bmp']:
        image_files.extend(glob.glob(f'{img_source}/*.{ext}'))
    return image_files

dir = '.\\Test'
image_files = find_image_files(dir)

for image in image_files:

    # for debug, skip the files that pass the test before
    if image.startswith(dir + '\\_'):
        continue

    result = subprocess.run(
    ["python", "MahjongFaanCalculator.py", "--source", image, "--threshold", str(0.4)],
    capture_output=True,
    text=True
    )

    print("Image:", image)
    print("Output:", result.stdout)
    print("Error:", result.stderr)

sys.exit(0)