from ndn.app import NDNApp
from ndn.app_support.segment_fetcher import segment_fetcher
from ndn.encoding import Name, Component, NonStrictName
from ndn.types import InterestTimeout

import time
import csv
import logging

logging.basicConfig(
    filename='/src/consumer.log',
    level=logging.INFO,
    format='%(asctime)s\t%(message)s'
)


app = NDNApp()

relay = False
if relay:
    target_name = '/relay/' + target_name

filepath = '/src/'
ext = '.jpg'

# target_name = '/concatimg/img1'+ext+'-img2'+ext
target_name = '/concatimg/img1_org'+ext+'-img2_org'+ext

target_name = Name.normalize(target_name)
fetchedfile = 'fetched' + Name.to_str(target_name).replace('/', '-')
fetchedfile = fetchedfile.replace('.', '').replace(',', '') + ext


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



async def main():
    get = time.time()
    cnt = 0
    data = b''
    async for seg in my_segment_fetcher(app, target_name, timeout=40000):
        name4log = Name.to_str(Name.normalize(target_name) + [Component.from_segment(cnt)])
        data += seg
        cnt += 1
        logging.info('Data\t'+Name.to_str(name4log)+'\tIN')
    with open(filepath + fetchedfile, 'wb') as f:
        f.write(data)
    get = time.time() - get
    print('DataSize [KB]:'.ljust(20), len(data)/1024)
    print('GetTime [ms]:'.ljust(20), get*1000)
    print()

    app.shutdown()


if __name__ == '__main__':
    app.run_forever(after_start=main())
