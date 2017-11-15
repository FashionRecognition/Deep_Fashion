from PIL import Image
import shutil
import re
import os
import zipfile

# Run once before training the network to prepare the dataset

df_womens = {
    'source': r'.\sources\img.zip',
    'data': r'.\data\deep_fashion_womens\\',
    'processed': r'.\processed\deep_fashion_womens\\'
}


# Useful for unzipping large files with limited memory
def unzip(inpath, outpath):
    archive = zipfile.ZipFile(inpath)

    for file in archive.namelist():
        try:
            archive.extract(file, outpath)
            print(file)
        except:
            print("Failed extracting " + file)


# A training image should have standard 224x224 dimensions, and be corrected for mean and variance
def preprocess(im):
    # Change filetype

    dimensions = min(im.size)

    # Width is smaller dimension
    if im.size[0] == dimensions:
        xoff = 0
        yoff = (im.size[0] - dimensions) / 2
    else:
        xoff = (im.size[1])
        yoff = 0

    # Reduce size
    im = im.crop((xoff, yoff, dimensions, dimensions))
    im = im.resize((200, 200), Image.NEAREST)

    # Normalize the image
    # colors = np.array(im).astype(float)
    # colors -= 128
    # colors /= 256
    # print(colors)
    # colors = (colors - np.mean(colors, axis=2)[..., None]) / np.std(colors, axis=2)[..., None]
    # colors *= 256
    # colors += 128
    # colors = np.clip(colors, 0, 255)

    # Image.fromarray(colors, 'RGB').save(fullname_png)
    return im


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Extract if not extracted, and .zip exists
if not os.path.exists(df_womens['data']):
    if os.path.exists(df_womens['source']):
        unzip(**df_womens)

# Only enable for debugging
# if os.path.exists(df_womens['procpath']):
#     shutil.rmtree(df_womens['procpath'])

# Preprocess if necessary
if not os.path.exists(df_womens['processed']):
    for root, dirs, filenames in os.walk(df_womens['data']):
        for f in filenames:
            fullname_in = root + '\\' + f
            fullname_out = root.replace(os.path.abspath(df_womens['data']), os.path.abspath(df_womens['processed'])) + \
                           '\\' + re.sub('[jpg]{3}$', 'png', f)

            processed_im = preprocess(Image.open(fullname_in))

            if not os.path.exists(os.path.dirname(fullname_out)):
                os.mkdir(os.path.dirname(fullname_out))
            processed_im.save(fullname_out)