import os

from PIL import Image


def function(data_list):
    # return relay(data_list)
    # return pick_one(data_list)
    return concatimg(data_list)


def relay(data_list):
    # just relay function
    return data_list

def pick_one(data_list):
    return data_list[0]


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
    # baseimg.save('putdata.png')
    baseimg.save('putdata.jpg')
    with open('putdata.jpg', 'rb') as f:
        put_data = f.read()
    # os.remove('putdata.png')
    os.remove('putdata.jpg')
    return put_data


def get_concat_h(im1, im2):
    dst = Image.new('RGB', (im1.width + im2.width, im1.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    return dst
