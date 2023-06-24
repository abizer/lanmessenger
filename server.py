import concurrent.futures
import socket
import threading
from time import sleep
from copy import deepcopy

shared_pals = []
pals_lock = threading.Lock()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', 31337))
        s.listen(5)
        while True:
            c, addr = s.accept()
            #print(f"DEBUG: Got connection from {addr}")
            while True:
                # receive data from client
                received_data = c.recv(4096)
                if not received_data:
                    break
                print(f"Received from {addr}:", received_data.decode('utf-8'))
            c.close()

def send_message(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))

        message_bytes = message.encode('utf-8')

        # send the message in chunks of 4096 bytes
        for i in range(0, len(message_bytes), 4096):
            chunk = message_bytes[i:i+4096]
            s.sendall(chunk)

def scan_port(ip, port):
    #print(f"trying {ip}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((ip, port))
            return True
        except:
            return False

def discover_pals():
    global shared_pals
    subnet = '192.168.1'
    port = 31337

    new_pals = []
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=256) as executor:
            future_to_ip = {executor.submit(scan_port, f'{subnet}.{i}', port): f'{subnet}.{i}' for i in range(1, 255)}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    data = future.result()
                    if data:
                        #print(f'DEBUG: Port {port} open on {ip}')
                        new_pals.append(ip)
                except Exception as exc:
                    print('%r generated an exception: %s' % (ip, exc))
        with pals_lock:
            #print("DISCOVER: got lock")
            shared_pals = new_pals

        sleep(3)

if __name__ == "__main__":
    listen_thread = threading.Thread(target=start_server, daemon=True)
    discover_thread = threading.Thread(target=discover_pals, daemon=True)
    listen_thread.start()
    discover_thread.start()

    MESSAGE = "hello from DentalPal!"

    while True:
        pals_copy = []
        with pals_lock:
            #print("MAIN: got lock")
            pals_copy = deepcopy(shared_pals)
        for p in pals_copy:
            send_message(p, 31337, MESSAGE)
        sleep(2)
	

