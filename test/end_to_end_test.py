from glob import glob
from os.path import isfile
from time import sleep
import json
import pytest
import requests

# This should be replaced with the correct url for each service
ENDPOINT_URL = "https://trknmunrdl.execute-api.us-east-1.amazonaws.com/dev"

files = [f for f in glob('./data/TestCases/*') if isfile(f)]
pytestmark = pytest.mark.parametrize("file", files)

class TestClass:
    def test_upload_file_and_get(self, file):
        print('Starting test with file {}'.format(file))
        content = open(file, 'rb').read()
        r = requests.post(_generate_post_create_url())
        body = json.loads(r.text)['body']
        upload_url = body['upload_url']
        blob_id = body['id']
        print('The blob id we got back was {}'.format(blob_id))

        p = requests.put(url=upload_url, data=content)
        # https://stackoverflow.com/questions/15258728/requests-how-to-tell-if-youre-getting-a-404
        assert p, 'Our put request failed with status code {}'.format(str(p.status_code))

        # Sleep to let our async lambda invoke
        sleep(5)
        response = requests.get(_generate_get_blob_url(blob_id))
        output = json.loads(response.text)
        print('We got response {}'.format(response.text))

        assert output['statusCode'] == 200, 'Our get request failed with status code {}'.format(output['statusCode'])
        assert len(output['body']['labels']) > 0, 'We did not get any labels back'

def _generate_post_create_url():
    return "{}/blobs".format(ENDPOINT_URL)

def _generate_get_blob_url(blob_id):
    return "{}/blobs/{}".format(ENDPOINT_URL, blob_id)
