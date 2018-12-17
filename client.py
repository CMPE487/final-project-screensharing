import socket
from zlib import decompress
import pygame
from threading import Thread

INITIAL_WIDTH = 1280
INITIAL_HEIGHT = 720
IMG_TRANSFER_PORT = 7344
SCREEN_SHARING_REQUEST_PORT = 7345
DISCOVERY_BROADCAST_PORT = 7346
PACKET_SIZE = 1500
CHUNK_SIZE = 1450
METADATA_SIZE = PACKET_SIZE - CHUNK_SIZE

screen_dimensions = (0, 0)
display_window = None
clock = None
frames = {}
displayed_frame_number = -1
destination_ip='192.168.1.112'

class Frame(object):
    chunk_number_in_frame = 0
    chunks = {}

    def __init__(self, chunk_number_in_frame):
        self.chunk_number_in_frame = chunk_number_in_frame
        self.chunks = {}

    def __del__(self):
        del self.chunks

    def add_chunk(self, chunk_number, chunk):
        self.chunks[chunk_number] = chunk
        return self.check_all_chunks_received()

    def check_all_chunks_received(self):
        return self.chunk_number_in_frame == len(self.chunks)

    def get_data(self):
        data = b""
        for i in range(self.chunk_number_in_frame):
            data += self.chunks[i]
        return data


def process_packet(packet):
    global frames
    meta_data = packet[:METADATA_SIZE].decode("utf-8").split(";")
    # Frame.number;chunk_number_in_frame;chunk_number
    frame_number = int(meta_data[0])
    chunk_number_in_frame = int(meta_data[1])
    chunk_number = int(meta_data[2])
    chunk = packet[METADATA_SIZE:]  # last CHUNK_SIZE bytes is file chunk
    if frame_number in frames:
        is_all_chunks_received = frames[frame_number].add_chunk(chunk_number, chunk)
        if is_all_chunks_received:
            display_frame(frame_number)
    else:
        new_frame = Frame(chunk_number_in_frame)
        new_frame.add_chunk(chunk_number, chunk)
        frames[frame_number] = new_frame


def display_frame(frame_number):
    global frames
    global screen_dimensions
    global clock
    frame = frames[frame_number]
    frame_data = frame.get_data()
    #print(len(frame_data))
    pixels = decompress(frame_data)

    # Create the Surface from raw pixels
    img = pygame.image.fromstring(pixels, screen_dimensions, 'RGB')

    # Display the picture
    display_window.blit(img, (0, 0))
    pygame.display.flip()
    clock.tick(10)

    # Remove frame
    frames.pop(frame_number, None)


def send_stop_request():
    # Inform server to stop it sending stream
    global destination_ip
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((destination_ip, SCREEN_SHARING_REQUEST_PORT))
            s.send(str.encode("stop"))
        except Exception as e:
            print(e)
        finally:
            s.close()


def start_image_listener():
    # Listen for UDP Image streams
    global screen_dimensions
    global display_window
    global clock

    pygame.init()
    display_window = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.iconify()
    clock = pygame.time.Clock()
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", IMG_TRANSFER_PORT))
            while True:
                try:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                            send_stop_request()
                            return
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if event.button == 1:  # left mouse button?
                                print(pygame.mouse.get_pos())
                    packet = s.recv(PACKET_SIZE)
                    process_packet(packet)
                    # Thread(target=process_packet, daemon=True, args=(packet,)).start() #Shall be tested later
                except Exception as e:
                    print("Error during image receiving:")
                    print(e)


def request_stream():
    global display_window
    global screen_dimensions
    global destination_ip
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((destination_ip, SCREEN_SHARING_REQUEST_PORT))
            s.send(str.encode("request"))
            dimension_message = s.recv(1024).decode()
            dimensions = [int(i) for i in dimension_message.split(",")]
            screen_dimensions = tuple(dimensions)

            display_window = pygame.display.set_mode(screen_dimensions)
        except Exception as e:
            print(e)
        finally:
            s.close()


if __name__ == '__main__':
    imageReceiver = Thread(target=start_image_listener, daemon=True)
    imageReceiver.start()
    request_stream()
    imageReceiver.join()
