from ndn.app import NDNApp
from ndn.encoding import Name, Component

import time
import queue
import csv
import os
import logging


SEGMENT_SIZE = 4000


name = 'img2.png'
# name = 'img1_org.jpg'
with open(name, 'rb') as f:
    data = f.read()
name = Name.normalize(name)

logging.basicConfig(
    filename='/src/producer1.log',
    level=logging.INFO,
    format='%(asctime)s\t%(message)s'
)


def main():
    app = NDNApp()

    seg_cnt = (len(data) + SEGMENT_SIZE - 1) // SEGMENT_SIZE
    packets = [app.prepare_data(name + [Component.from_segment(i)],
                                data[i*SEGMENT_SIZE:(i+1)*SEGMENT_SIZE],
                                freshness_period=1000,
                                final_block_id=Component.from_segment(seg_cnt - 1))
               for i in range(seg_cnt)]
    print(f'Created {seg_cnt} chunks under name {Name.to_str(name)}')

    @app.route(name)
    def on_interest(int_name, _int_param, _app_param):
        logging.info('Interest\t'+Name.to_str(int_name)+'\tIN')
        if Component.get_type(int_name[-1]) == Component.TYPE_SEGMENT:
            seg_no = Component.to_number(int_name[-1])
        else:
            seg_no = 0
        if seg_no < seg_cnt:
            # print(f'Putting a packet:\t{seg_no}')
            logging.info('Data\t'+Name.to_str(int_name)+'\tOUT')
            app.put_raw_packet(packets[seg_no])

    app.run_forever()


if __name__ == '__main__':
    main()
