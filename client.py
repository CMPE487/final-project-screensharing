import socket
from zlib import decompress
import pygame
from threading import Thread
from time import sleep

INITIAL_WIDTH = 720
INITIAL_HEIGHT = 480
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
client_ip = ''
server_ip = '192.168.1.112'

server_dict = {}


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
    # print(len(frame_data))
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
    global server_ip
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((server_ip, SCREEN_SHARING_REQUEST_PORT))
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
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", IMG_TRANSFER_PORT))
        while True:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        send_stop_request()
                        return
                packet = s.recv(PACKET_SIZE)
                process_packet(packet)
                # Thread(target=process_packet, daemon=True, args=(packet,)).start() #Shall be tested later
            except Exception as e:
                print("Error during image receiving:")
                print(e)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.168.1.1', 1))
        ip = s.getsockname()[0]
    except Exception as e:
        print(e)
        print('Could\'nt get ip with the first way, plan B shall be used.')
        ip = (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [
            [(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in
             [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0]
        print("Server IP is " + ip)
    finally:
        s.close()
    return ip


def send_discovery_message():
    global client_ip
    message = '0;{}'.format(client_ip)
    # print(message)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((client_ip, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(str.encode(message), ('<broadcast>', DISCOVERY_BROADCAST_PORT))
    return 0


def get_discovery_message(accepted_socket):
    message = accepted_socket.recv(1024).decode()
    print(message)
    accepted_socket.close()
    message_parsed = message.split(";", 2)
    # print(messageParsed)
    if message_parsed[0] == '1':
        discovered_server_ip = message_parsed[1]
        discovered_server_name = message_parsed[2]
        if discovered_server_ip not in server_dict:
            server_dict[discovered_server_ip] = discovered_server_name


def start_discovery_response_message_listener():
    # Listens for TCP Response messages
    global client_ip
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((client_ip, DISCOVERY_BROADCAST_PORT))
            s.listen(5)
            while True:
                accepted_socket, address = s.accept()
                Thread(target=get_discovery_message, daemon=True, args=(accepted_socket,)).start()


def request_stream():
    global server_ip
    global display_window
    global screen_dimensions
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((server_ip, SCREEN_SHARING_REQUEST_PORT))
            s.send(str.encode("request"))
            dimension_message = s.recv(1024).decode()
            dimensions = [int(i) for i in dimension_message.split(",")]
            screen_dimensions = tuple(dimensions)

            display_window = pygame.display.set_mode(screen_dimensions)
        except Exception as e:
            print(e)
        finally:
            s.close()


def select_server():
    global server_ip
    number_of_servers = len(server_dict)
    server_ip_list = []

    if number_of_servers == 0:
        print("No active server to list at the moment.")
        sleep(3)
        send_discovery_message()
        sleep(2)
        return select_server()
    elif number_of_servers > 1:
        print("This is the list of online servers:")
        i = 0
        for server, name in server_dict.items():
            server_ip_list.append(server)
            i += 1
            print("%{} - {}({})".format(str(i), name, server))
        server_id = input("Select a server to get screen stream by typing its assigned number: ")
        while not server_id.isdigit() or not int(server_id) <= number_of_servers or not int(server_id) > 0:
            server_id = input("Please enter a digit between 1 and %d! " % number_of_servers)
            server_ip = server_ip_list[int(server_id) - 1]
    else:  # Only 1 server case
        for server, name in server_dict.items():
            print("There is only 1 active server named {}({}), it is automatically selected.".format(server, name))
            server_ip = server
    print("Selected server is " + server_dict[server_ip] + "(%s)." % server_ip)
    return True


if __name__ == '__main__':
    client_ip = get_ip()

    # Discover server stage
    Thread(target=start_discovery_response_message_listener, daemon=True).start()
    send_discovery_message()

    # Wait for responses
    sleep(1)

    select_server()

    imageReceiver = Thread(target=start_image_listener, daemon=True)
    imageReceiver.start()
    request_stream()
    imageReceiver.join()
    print("Bye")