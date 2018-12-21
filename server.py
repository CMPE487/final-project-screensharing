import socket, time
from PIL import Image
from threading import Thread, currentThread
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

server_name = ""


def get_IP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.168.1.1', 1))
        IP = s.getsockname()[0]
    except:
        print('Could\'nt get ip with the first way, plan B shall be used.')
        IP = (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [
            [(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in
             [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0]
        print("Server IP is " + IP)
    finally:
        s.close()
    return IP


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
            # sleep(0.03) #for the purpose of 30 fps
            frame_number += 1


def respond_to_discovery_message(server_IP, client_IP):
    global server_name
    # Discovery response protocol ->  1;server_IP;server_name
    response_message = ";".join(["1", server_IP, server_name])

    # print("Discovery response message " +responseMessage)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        s.connect((client_IP, DISCOVERY_BROADCAST_PORT))
        s.sendall(str.encode(response_message))
        s.close()
        print("Discovery response message " + response_message + " complete")


def start_discovery_broadcast_listener(server_IP):
    # Listens for UDP Broadcast messages
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", DISCOVERY_BROADCAST_PORT))
            while True:
                try:
                    message, address = s.recvfrom(1024)

                    message = message.decode()
                    # Discovery protocol ->  0;client_IP
                    messageParsed = message.split(";", 3)
                    if messageParsed[1] == server_IP:
                        # My own broadcast
                        continue
                    if messageParsed[0] == '0':
                        print(messageParsed)
                        client_IP = messageParsed[1]
                        respond_to_discovery_message(server_IP, client_IP)
                except:
                    print("Error during broadcast message receiving")


def startScreenRequestListener(server_IP):
    global screen_dimensions
    streaming_thread = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((server_IP, SCREEN_SHARING_REQUEST_PORT))
        try:
            s.listen()
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
                    streaming_thread.is_run = False
        finally:
            s.close()


if __name__ == '__main__':
    server_IP = get_IP()
    server_name = input('Hello, enter the server display name: ')
    streaming_thread = Thread(target=start_discovery_broadcast_listener, daemon=True, args=(server_IP,)).start()
    startScreenRequestListener(server_IP)
