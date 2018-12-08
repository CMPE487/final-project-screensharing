import socket
from threading import Thread
from zlib import compress
from mss import mss
from time import sleep

IMG_TRANSFER_PORT = 7344
SCREEN_SHARING_REQUEST_PORT = 7345
DISCOVERY_BROADCAST_PORT = 7346
PACKET_SIZE = 1500
CHUNK_SIZE = 1450
METADATA_SIZE = PACKET_SIZE - CHUNK_SIZE
screen_dimensions = (0, 0)


def getIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.168.1.1', 1))
        IP = s.getsockname()[0]
    except:
        print('Coulnt get ip from socket, localhost shall be used')
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def retreive_screenshot(ip_address):
    socket_for_image_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_for_image_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    global screen_dimensions
    frame_number = 0
    with mss() as sct:
        #print(sct.monitors)
        while 'streaming':
            # Capture the screen
            rect = {'top': 0, 'left': 0, 'width': screen_dimensions[0], 'height': screen_dimensions[1]}
            img = sct.grab(rect)
            # Tweak the compression level here (0-9)
            frame = compress(img.rgb, 9)

            frame_size = len(frame)
            if CHUNK_SIZE < frame_size:
                chunks = [frame[i:i + CHUNK_SIZE] for i in range(0, frame_size, CHUNK_SIZE)]
            else:
                chunks = [frame]
            for i in range(len(chunks)):
                # Frame.number;chunk_number_in_frame;chunk_number
                meta_data = bytes("%d;%d;%d;" % (frame_number, len(chunks), i), "utf-8")
                padding_size = METADATA_SIZE - len(meta_data)
                padding = padding_size * bytes("\0", "utf-8")
                packet = meta_data + padding + chunks[i]
                socket_for_image_send.sendto(packet, (ip_address, IMG_TRANSFER_PORT))
            sleep(1)
            frame_number += 1


def main():
    global screen_dimensions
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((getIP(), SCREEN_SHARING_REQUEST_PORT))
        try:
            s.listen()
            print('Server started.')
            while True:
                conn, ip_address = s.accept()
                screen_info = mss().monitors[1]
                screen_dimensions = (screen_info["width"], screen_info["height"])
                screen_dimensions_info = '%d,%d' % screen_dimensions
                conn.send(str.encode(screen_dimensions_info))
                print('Client connected IP:', ip_address)
                thread = Thread(target=retreive_screenshot, daemon=True, args=(ip_address[0],))
                thread.start()
        finally:
            s.close()


if __name__ == '__main__':
    main()
