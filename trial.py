import socket
from PIL import Image
from threading import Thread, currentThread
from zlib import compress
from mss import mss
import time

screen_info = mss().monitors[1]
screen_dimensions = (screen_info["width"], screen_info["height"])
rect = {'top': 0, 'left': 0, 'width': screen_dimensions[0], 'height': screen_dimensions[1]}

with mss() as sct:
    while 1:
        step1 = time.time()
        img = sct.grab(rect)
        step2 = time.time()
        print("sct.grab(rect)")
        print(step2 - step1)
        img = img.rgb
        step3 = time.time()
        print("img.rgb")
        print(step3 - step2)
        frame = compress(img, 5)
        step4 = time.time()
        print("compress(img, 9)")
        print(step4 - step3)
        print("Total")
        print(step4 - step1)
        frame_size = len(frame)


