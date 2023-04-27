from ndn.app import NDNApp
from ndn.encoding import Name, Component, NonStrictName
from ndn.encoding.tlv_type import BinaryStr, FormalName
from ndn.types import (InterestCanceled, InterestNack, InterestTimeout,
                       ValidationFailure)
from ndn.app_support.segment_fetcher import segment_fetcher

import sys
sys.dont_write_bytecode = True

import threading
import queue
import time
import csv
from PIL import Image
import logging
from concurrent import futures
import hashlib
import os

import msg_call_svc as mcs


async def my_segment_fetcher(app: NDNApp, name: NonStrictName, timeout=4000, retry_times=3,
                          validator=None, must_be_fresh=True):
    """
    An async-generator to fetch a segmented object. Interests are issued one by one.
    :param app: NDN Application
    :param name: Name prefix of Data
    :param timeout: Timeout value, in milliseconds
    :param retry_times: Times for retry
    :param validator: Validator
    :param must_be_fresh: MustBeFresh field of Interest
    :return: Data segments in order.
    """
    async def retry(first):
        nonlocal name
        trial_times = 0
        while True:
            logging.info('Interest\t'+Name.to_str(name)+'\tOUT')
            future = app.express_interest(name, validator=validator, can_be_prefix=first,
                                          must_be_fresh=must_be_fresh, lifetime=timeout)
            try:
                return await future
            except InterestTimeout:
                trial_times += 1
                if trial_times >= retry_times:
                    raise

    name = Name.normalize(name)
    # First Interest
    name, meta, content = await retry(True)
    # If it's not segmented
    if Component.get_type(name[-1]) != Component.TYPE_SEGMENT:
        yield content
        return
    # If it's segmented
    if Component.to_number(name[-1]) == 0:
        yield content
        if meta.final_block_id == name[-1]:
            return
        seg_no = 1
    else:
        # If it's not segment 0, starting from 0
        seg_no = 0
    # Following Interests
    while True:
        name[-1] = Component.from_segment(seg_no)
        name, meta, content = await retry(False)
        yield content
        if meta.final_block_id == name[-1]:
            return
        seg_no += 1


service_name = '/concatimg'

SEGMENT_SIZE = 4400
FRESHNESS_PERIOD = 100000

q_content = queue.Queue()
q_recent_data = queue.Queue()

app = NDNApp()

# q_get = queue.Queue()
q_put = queue.Queue()

logfile = '/src/relay.csv'

logging.basicConfig(
    filename='/src/concatimg.log',
    level=logging.INFO,
    format='%(asctime)s\t%(message)s'
)


def send_interest(queue: queue.Queue, name: FormalName) -> None:
    async def interest_func(name):
        cnt = 0
        data = b''
        # timestamps = []
        async for seg in my_segment_fetcher(app_thread, name, timeout=4000, retry_times=3):
            data += seg
            name4log = Name.to_str(Name.normalize(name) + [Component.from_segment(cnt)])
            # timestamps.append((str(time.time()), 'relay d-in', Name.to_str(name), str(cnt)))
            logging.info('Data\t'+name4log+'\tIN')
            cnt += 1
        queue.put(data)
        # q_get.put(timestamps)
        app_thread.shutdown()

    if not queue.empty():
        app_thread.shutdown()
        return
    app_thread = NDNApp()
    app_thread.run_forever(after_start=interest_func(name))


def function_relay(data: bytes) -> bytes:
    # just relay
    return data


def save_data(q: queue.Queue, name: str, data: bytes) -> None:
    while not q.empty():
        q.get()
    q.put({'name': name, 'data': data, 'time': time.time()})


def search_data(q: queue.Queue, name: str) -> bytes:
    if q.empty():
        return None
    data = q.get()
    if (time.time() - data['time']) > FRESHNESS_PERIOD:
        return None
    else:
        q.put(data)
        if data['name'] == name:
            return data['data']
        else:
            return None


def parse_intrest(name: FormalName) -> dict:
    # name='/relay/test.jpg/seg=3'
    # --> org='/relay/test.jpg/seg=3', srch='/relay/test.jpg', trm='/test.jpg', seg_no=3
    org = Name.to_str(name)
    if Component.get_type(Name.from_str(org)[-1]) == Component.TYPE_SEGMENT:
        # interest packet has segment number
        seg_no = Component.to_number(Name.from_str(org)[-1])
        srch = org.replace('/seg=' + str(seg_no), '')
    else:
        seg_no = 0
        srch = org
    trm = Name.to_str(srch).replace(service_name + '/', '')
    namelist = trm.split('-')
    return {'org': org, 'srch': srch, 'trm': trm, 'num': seg_no, 'namelist': namelist}


def concatimg(data_list):
    # concat 2 images
    dlist = []
    for i, data in enumerate(data_list):
        with open('data' + str(i), 'wb') as f:
            f.write(data)

    for i in range(len(data_list)):
        dlist.append(Image.open('data' + str(i)))

    baseimg = dlist[0]
    for i in range(len(dlist)):
        if i == 0:
            pass
        else:
            baseimg = get_concat_h(baseimg, dlist[i])
    baseimg.save('putdata.png')
    with open('putdata.png', 'rb') as f:
        put_data = f.read()
    os.remove('putdata.png')
    return put_data


def get_concat_h(im1, im2):
    dst = Image.new('RGB', (im1.width + im2.width, im1.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    return dst


async def main():
    print(f'My service name: {service_name}')

    @app.route(service_name)
    def on_interest(name, param, _app_param):
        # print('interest received: ', Name.to_str(name))
        logging.info('Interest\t'+Name.to_str(name)+'\tIN')
        interest = parse_intrest(name)

        # search recently saved data
        res = search_data(q_recent_data, interest['srch'])
        if res is not None:
        # if False:
            # hit
            put_data = res
        else:
            # send interest thread
            if len(interest['namelist']) > 1:
                send_dict = {}
            ### FOR LOOP ###
            #     for i in interest['namelist']:
            #         print(f'sending interest {i}')
            #         thread_send_interest = threading.Thread(target=send_interest, args=(q_content, i, ))
            #         thread_send_interest.start()
            #         thread_send_interest.join()
            #         data = q_content.get()
            #         send_dict[i] = data
            #         with open(i, 'wb') as f:
            #             f.write(data)
            #         ### log (get contents)
            #         with open(logfile, 'a') as f:
            #             writer = csv.writer(f)
            #             writer.writerows(q_get.get())
            #     put_data = mcs.call_service(list(send_dict.keys()))
            ################
            ### THREADPOOL ###
                data_q = queue.Queue()
                future_list = []
                print('sending interest: ', interest['namelist'])
                with futures.ThreadPoolExecutor() as executor:
                    for n in interest['namelist']:
                        future = executor.submit(send_interest, queue=data_q, name=n)
                        future_list.append(future)
                    _ = futures.as_completed(fs=future_list)
                data_list = []
                if data_q.empty():
                    logging.debug('failed to get contents')
                    exit()
                _cnt = 0
                while not data_q.empty():
                    _d = data_q.get()
                    # data_list.append(_d)
                    # send_dict[hashlib.sha256(_d).hexdigest()[:10]] = _d
                    send_dict[interest['namelist'][_cnt]] = _d
                    _cnt += 1
                print(send_dict.keys())
                for k, v in send_dict.items():
                    with open('/data/' + k, 'wb') as f:
                        f.write(v)
                put_data = mcs.call_service(list(send_dict.keys()))
            ##################

                ### concatimg ###
                # l = []
                # for name in send_dict.keys():
                #     with open('/data/' + name, 'rb') as f:
                #         l.append(f.read())

                # t_func = time.time()
                # put_data = concatimg(l)
                # print('service time [ms]:'.ljust(20), (time.time() - t_func)*1000)

                ### pick one ###
                # l = []
                # for name in send_dict.keys():
                #     with open('/data/' + name, 'rb') as f:
                #         l.append(f.read())
                # t_func = time.time()
                # put_data = l[0]
                # print('service time [ms]:'.ljust(20), (time.time() - t_func)*1000)
            else:
                thread_send_interest = threading.Thread(target=send_interest, args=(q_content, i, ))
                thread_send_interest.start()
                thread_send_interest.join()
                data = q_content.get()
                put_data = function_relay

                ### log (get contents)
                # with open(logfile, 'a') as f:
                #     writer = csv.writer(f)
                #     writer.writerows(q_get.get())

            # call service function
            # svc = time.time()
            # put_data = function_relay(data)
            # print(f'service time: {time.time() - svc}')

            # save data
            save_data(q_recent_data, interest['srch'], put_data)
            # print('Saved as {}'.format(interest['srch']))

        # put a data packet
        seg_cnt = (len(put_data) + SEGMENT_SIZE - 1) // SEGMENT_SIZE
        if interest['num'] < seg_cnt:
            app.put_data(Name.from_str(interest['srch']) + [Component.from_segment(interest['num'])],
                         put_data[interest['num']*SEGMENT_SIZE:(interest['num']+1)*SEGMENT_SIZE],
                         freshness_period=100,
                         final_block_id=Component.from_segment(seg_cnt-1))

            #logging.info('Data\t'+Name.to_str(interest['org'])+'\tOUT')
            logging.info('Data\t'+Name.to_str(name)+'\tOUT')
            q_put.put([interest['num'], time.time()])

        ### log
        #if interest['num'] == seg_cnt - 1:
        #    timestamps = []
        #    while not q_put.empty():
        #        n, t = q_put.get()
        #        timestamps.append((t, 'relay d-out', Name.to_str(interest['srch']), n))
        #    with open(logfile, 'a') as f:
        #        csv.writer(f).writerows(timestamps)


        # print('Restart receiver ...')



if __name__ == '__main__':
    app.run_forever(after_start=main())
