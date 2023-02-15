import base64
import json
import socket
import time

import sys
sys.dont_write_bytecode = True

import importlib
import app

SIDECAR_IP = 'sidecar'
MY_IP = 'service'
PORT = 1234
RECIEVE_SIZE = 1024


def listen_single_msg():
    print('listening')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((MY_IP, PORT))
        s.listen()

        # recieve from sidecar
        while True:
            recieve_message = b''
            client_sock, client_address = s.accept()

            # LISTENING TO SIDECAR
            while True:
                _message = client_sock.recv(RECIEVE_SIZE)

                if not _message:
                    break
                else:
                    recieve_message += _message
            print(recieve_message.decode())

            # READ DATA ON VOLUME
            data = b''
            with open('/data/' + recieve_message.decode(), 'rb') as f:
                data = f.read()

            # CALL SERVICE FUNCTION
            print('call service function')
            importlib.reload(app)
            t = time.time()
            processed_data = app.function(data)
            print('service time:'.ljust(20), time.time() - t)

            # WRITE PROCESSED DATA ON VOLUME
            send_message = ('processed-' + recieve_message.decode()).encode()
            with open('/data/' + send_message.decode(), 'wb') as f:
                f.write(processed_data)

            # SEND MSG TO SIDECAR
            client_sock.sendall(send_message)
            client_sock.close()


def listen_two_msg():
    print('listening')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((MY_IP, PORT))
        s.listen()

        # recieve from sidecar
        while True:
            recieve_message = b''
            client_sock, client_address = s.accept()

            # LISTENING TO SIDECAR
            while True:
                _message = client_sock.recv(RECIEVE_SIZE)

                if not _message:
                    break
                else:
                    recieve_message += _message
            recieve_message = recieve_message.decode()
            print(recieve_message)

            namelist = json.loads(recieve_message)
            if type(namelist) is not list:
                namelist = list(namelist)

            # READ DATA ON VOLUME
            datalist = []
            for name in namelist:
                with open('/data/' + name, 'rb') as f:
                    datalist.append(f.read())

            # CALL SERVICE FUNCTION
            print('call service function')
            importlib.reload(app)
            t = time.time()
            processed_data = app.function(datalist)
            print('service time [ms]:'.ljust(20), (time.time() - t)*1000)

            # WRITE PROCESSED DATA ON VOLUME
            send_name = 'processed-' + '_'.join(namelist)
            send_message = json.dumps(send_name).encode()
            with open('/data/' + send_name, 'wb') as f:
                f.write(processed_data)

            # SEND MSG TO SIDECAR
            client_sock.sendall(send_message)
            client_sock.close()



if __name__ == '__main__':
    listen_two_msg()
