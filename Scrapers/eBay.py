import requests
import sys
import time
import json
from random import random

from multiprocessing import Queue, Process, cpu_count

import bs4

from pymongo import MongoClient
import numpy as np

from io import BytesIO
from bson.binary import Binary

from PIL import Image

mongo_client = MongoClient(host='localhost', port=27017)  # Default port
db = mongo_client.deep_fashion


labels = json.load(open('../Tagger/labels.json'))

ignore = ['pant', 'jean', 'shorts', 'skirt', 'trouser', 'glove', 'bikini', 'sock', 'capri', 'underwear', 'skirt',
          'bra ', 'push-up', 'push up', 'swimsuit', 'leggings', 'skort', 'wunder under', 'leg ', 'purse', 'vassarette']


def scrape(label, tag):
    print({label: tag})

    page_queue = Queue()

    page_count = 199  # this many pages have rendered content
    for page in reversed(range(page_count)):
        page_queue.put(page)

    pool = [Process(target=process_wrapper, args=(page_queue, label, tag), name=str(proc))
            for proc in range(cpu_count())]

    for proc in pool:
        proc.start()

    while any([proc.is_alive() for proc in pool]) and page_queue.qsize() != 0:

        # Show status
        sys.stdout.write("\r\x1b[KCollecting: " + str(199 - page_queue.qsize()) + '/' + str(199))
        sys.stdout.flush()
        time.sleep(0.5)

    # Print a newline to stdout
    print()

    # Once the pool of pages to scrape has been exhausted, each thread will die
    # Once the threads are dead, this terminates all threads and the program is complete
    for proc in pool:
        proc.terminate()


def process_wrapper(page_queue, label, tag):
    # Take elements from the queue until the queue is exhausted
    while not page_queue.empty():
        page_id = page_queue.get()

        success = False
        while not success:
            try:
                scrape_page(page_id, label, tag)
                success = True

            except TypeError:
                # Sometimes the div doesn't get loaded properly, just re-attempt quietly
                pass

            except Exception as err:
                print(err)
                print("Re-attempting page " + str(page_id))

            # Be nice to their servers
            time.sleep(1)


def scrape_page(page_number, label, tag):
    listing_url = 'https://www.ebay.com/sch/i.html' + \
                  '?_nkw=used+womens+clothes+' + tag.replace(' ', '+') + \
                  '&_sop=10&_pgn=' + str(page_number)

    # This only downloads the raw html
    soup = bs4.BeautifulSoup(requests.get(listing_url).content, "lxml")

    # Iterate through each product listing
    for listing in soup.find("ul", {"id": "ListViewInner"}):

        # Some elements are not for products. Just ignore the error
        try:
            # Isolate the image div.
            element = bs4.BeautifulSoup(str(listing), "lxml").li.div.div.a.img

            # Don't write elements that match the ignore list
            if any([ignore_tag in element['alt'].lower() for ignore_tag in ignore]):
                continue

            # Ignore invalid image format
            if element['src'].endswith('.gif'):
                continue

            # Check if record is already in database
            if not list(db.ebay.find({'image_url': element['src']})):
                # Example conversion from url > request > bytestream > binary > bytestream > image
                # The binary stage is stored in mongodb
                # Image.open(BytesIO(Binary(BytesIO(requests.get(image_url).content).getvalue()))).show()

                # Decode binary via the following:
                # Image.open(BytesIO(listing['image']))

                # Download image
                content = requests.get(element['src']).content

                try:
                    assert(len(np.array(Image.open(BytesIO(content))).shape) == 3)
                except (IOError, AssertionError):
                    # Ignore greyscale or corrupted images
                    continue

                listing = {'image_url': element['src'],
                           'title': element['alt'],
                           'image': Binary(BytesIO(content).getvalue()),
                           label: tag
                           }

                db.ebay.insert_one(listing)
            else:
                db.ebay.update({'image_url': element['src']}, {"$set": {label: tag}})

        except AttributeError:
            pass


# Only call scrape when invoked from main. This prevents forked processes from calling it
if __name__ == '__main__':

    for label, tags in sorted(labels.items(), key=lambda x: random()):
        for tag in sorted(tags, key=lambda x: random()):
            scrape(label, tag)
