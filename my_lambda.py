import json
import logging
import os
import random
import re
import sys

sys.path.append("lib")
import requests
from requests_oauthlib import OAuth1

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ENDPOINT = "https://api.twitter.com/1.1/statuses/update.json"
SIGNS_URL = os.getenv('SIGNS_URL',
                     "https://cdn.rawgit.com/jikuja/leaflet-liikennemerkit/master/liikennemerkit.geojson")
MAPPING_URL = os.getenv('MAPPING_URL',
                      "https://cdn.rawgit.com/jikuja/liikennemerkkinumerot/master/merkit_map.json")
logging.debug("starting")


def send_tweet(auth, data):
    response = requests.post(ENDPOINT, data=data, auth=auth)
    logger.info(response)
    logger.info(response.request.body)
    logger.info(response.content.decode('utf-8'))


def get_data(url, boto):
    if boto:
        import boto3
        splitted = url.split(":")
        s3 = boto3.resource("s3")
        obj = s3.Object(splitted[0], splitted[1])
        s = obj.get()['Body'].read().decode("utf-8")
        return json.loads(s)
    else:
        resp =requests.get(url)
        # TODO: errors handling
        return resp.json()
        # TODO: error handling


def get_random_sign(signs):
    random.seed()
    point = random.randint(0, len(signs) - 1)
    random_sign = signs[point]
    return random_sign['properties']


def get_sign_description(txt, mapping):
    # first handle speed limits
    m = re.match("(361|362|363|364)_(\d+)", txt)
    if m:
        return mapping.get(m.group(1)) + "arvolla" + m.group(2)
    if txt == "Unclassified":   # sign not automatically identified by cyclorama
        return "tunnistamaton"
    return mapping.get(txt, "bork!")


def create_tweet_data(sign, mapping):
    sign_type = get_sign_description(sign['signtype'], mapping)
    tweet_text = "Päivän liikennemerkki on '{}'".format(sign_type)

    text = sign['signtext']
    if text:
        if text == "unreadable" or text == "unredable": # SIC!
            tweet_text = "{} Merkin tekstiä ei ole pystytty tulkitsemaan koneellisesti.".format(tweet_text)
        else:
            tweet_text = "{} Merkistä on luettu teksti '{}'.".format(tweet_text, text)

    tweet_text = "{} Katso lisää: https://jikuja.kapsi.fi/leaflet-liikennemerkit/?fid={}".format(tweet_text, sign['fid_'])
    logger.debug(tweet_text)
    data = {"status": tweet_text}
    return data


def my_handler(event, context):
    my_function(False, True)


def my_function(dry_run, boto):
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_key = os.getenv('ACCESS_KEY')
    access_secret = os.getenv('ACCESS_SECRET')
    keys_found = consumer_key and consumer_secret and access_key and access_secret

    if dry_run or keys_found:
        # load datas
        signs = get_data(SIGNS_URL, boto)['features']
        mapping = get_data(MAPPING_URL, boto)
        sign = get_random_sign(signs)

        # create tweet
        data = create_tweet_data(sign, mapping)

        logger.debug(json.dumps(data))
        if not dry_run and keys_found:
            auth = OAuth1(consumer_key, consumer_secret, access_key, access_secret)
            send_tweet(auth, data)
    else:
        logger.error("fsck!")


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.debug("Starting....")
    # TODO: test locally with boto
    my_function(False, False)
