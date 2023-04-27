import json
import base64
import socket
import time
import os

import logging
logging.basicConfig(
    filename='/src/concatimg.log',
    level=logging.INFO,
    format='%(asctime)s\t%(message)s'
)


SERVICE_IP = 'service'
PORT = 1234
RECIEVE_SIZE = 4 * 1024


# t = time.time()
# data1 = os.urandom(1 * 1024 * 1024)
# data2 = os.urandom(1 * 1024 * 1024)
# print('gen data time:'.ljust(20), time.time() - t)

# data_dict = {'img1.png': b'', 'img2.png': b''}
# for data_name in data_dict.keys():
#     with open('/src/' + data_name, 'rb') as f:
#         data_dict[data_name] = f.read()

# data1 = data_dict['img1.png']
# data2 = data_dict['img2.png']


# with open('/data/data1', 'wb') as f:
#     f.write(data1)
# with open('/data/data2', 'wb') as f:
#     f.write(data2)
# for data_name in data_dict.keys():
#     with open('/data/' + data_name, 'wb') as f:
#         f.write(data_dict[data_name])
# send_message = list(data_dict.keys())

def call_service(send_message):
    print('socket start')
    t = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVICE_IP, PORT))

        # SEND TO SERVICE
        if send_message:
            logging.info('Message\tOUT')
            _data = json.dumps(send_message).encode()
            print('sending')
            s.sendall(_data)
            s.shutdown(1)
            print('sent')

        # LISTENING
        print('wait for data')
        recieve_message = b''
        while True:
            _data = s.recv(RECIEVE_SIZE)
            if not _data:
                break
            else:
                recieve_message += _data
        recieve_message = json.loads(recieve_message.decode())
        logging.info('Message\tIN')
        print('recieved')

    print('socket time [ms]:'.ljust(20), (time.time() - t)*1000)

    # recieve_data = []
    # for name in recieve_message:
    #     with open('/data/' + name, 'rb') as f:
    #         recieve_data.append(f.read())

    # for i in range(len(recieve_message)):
    #     with open('/src/' + recieve_message[i], 'wb') as f:
    #         f.write(recieve_data[i])

    # for i in send_message + recieve_message:
    #     os.remove('/data/' + i)

    with open('/data/' + recieve_message, 'rb') as f:
        recieve_data = f.read()

    return recieve_data


# print(f'send_message: {send_message}')
# print(f'recieve_message: {recieve_message}')
# if all([send_message[i] == recieve_message[i] for i in range(len(send_message))]):
#     print('data check OK')


if __name__ == '__main__':
    call_service(send_message)
