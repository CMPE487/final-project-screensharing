import socket
from PIL import Image
from threading import Thread, currentThread
from zlib import compress
from mss import mss
import time

IMG_TRANSFER_PORT = 7344
SCREEN_SHARING_REQUEST_PORT = 7345
DISCOVERY_BROADCAST_PORT = 7346
PACKET_SIZE = 1500
CHUNK_SIZE = 1450
METADATA_SIZE = PACKET_SIZE - CHUNK_SIZE
screen_dimensions = (0, 0)

server_name = ""
server_key = ""

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


def retrieve_screenshot(address):
    socket_for_image_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_for_image_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    global screen_dimensions
    frame_number = 0
    t = currentThread()
    with mss() as sct:
        # print(sct.monitors)
        while getattr(t, "is_running", True):
            # Capture the screen
            start = time.time()
            rect = {'top': 0, 'left': 0, 'width': screen_dimensions[0], 'height': screen_dimensions[1]}
            img = sct.grab(rect)
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            img = pil_img.resize((720, 480), Image.ANTIALIAS)
            # Tweak the compression level here (0-9)
            frame = compress(img.tobytes(), 9)
            frame_size = len(frame)
            print(frame_size / 1024.0)
            if CHUNK_SIZE < frame_size:
                chunks = [frame[i:i + CHUNK_SIZE] for i in range(0, frame_size, CHUNK_SIZE)]
            else:
                chunks = [frame]
            chunk_number_in_frame = len(chunks)
            # print("%d,%d" %(frame_number,chunk_number_in_frame))
            for i in range(chunk_number_in_frame):
                # Frame.number;chunk_number_in_frame;chunk_number
                meta_data = bytes("%d;%d;%d;" % (frame_number, chunk_number_in_frame, i), "utf-8")
                padding_size = METADATA_SIZE - len(meta_data)
                padding = padding_size * bytes("\0", "utf-8")
                packet = meta_data + padding + chunks[i]
                socket_for_image_send.sendto(packet, (address, IMG_TRANSFER_PORT))
            print(time.time() - start)
            # time.sleep(0.03) #for the purpose of 30 fps
            frame_number += 1


def respond_to_discovery_message(client_ip):
    global server_name
    global server_ip
    # Discovery response protocol ->  1;server_ip;server_name
    response_message = ";".join(["1", server_ip, server_name])

    # print("Discovery response message " +responseMessage)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        s.connect((client_ip, DISCOVERY_BROADCAST_PORT))
        s.sendall(str.encode(response_message))
        s.close()
        print("Discovery response message " + response_message + " complete")


def start_discovery_broadcast_listener():
    # Listens for UDP Broadcast messages
    global server_ip
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", DISCOVERY_BROADCAST_PORT))
            while True:
                try:
                    message, address = s.recvfrom(1024)

                    message = message.decode()
                    # Discovery protocol ->  0;client_ip
                    message_parsed = message.split(";", 3)
                    if message_parsed[1] == server_ip:
                        # My own broadcast
                        continue
                    if message_parsed[0] == '0':
                        print(message_parsed)
                        client_ip = message_parsed[1]
                        respond_to_discovery_message(client_ip)
                except Exception as e:
                    print("Error during broadcast message receiving:")
                    print(e)


def start_screen_request_listener():
    global screen_dimensions
    global server_ip
    streaming_thread = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((server_ip, SCREEN_SHARING_REQUEST_PORT))
        try:
            s.listen(5)
            print('Server started.')
            while True:
                conn, address = s.accept()
                message = conn.recv(1024).decode()
                if message == "request":
                    screen_info = mss().monitors[1]
                    screen_dimensions = (screen_info["width"], screen_info["height"])
                    # screen_dimensions = (720, 480)
                    screen_dimensions_info = '%d,%d' % (720, 480)
                    print(screen_dimensions_info)
                    conn.send(str.encode(screen_dimensions_info))
                    print('Client connected IP:', address)
                    streaming_thread = Thread(target=retrieve_screenshot, daemon=True, args=(address[0],))
                    streaming_thread.is_running = True
                    streaming_thread.start()
                elif message == "stop":
                    streaming_thread.is_running = False
        finally:
            s.close()


if __name__ == '__main__':
    server_ip = get_ip()
    server_name = input('Hello, enter the server display name: ')
    #server_key = input('Enter the server access key: ')
    discovery_listener_thread = Thread(target=start_discovery_broadcast_listener, daemon=True).start()
    start_screen_request_listener()
