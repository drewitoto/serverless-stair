import botocore
import boto3
import http.client as httplib
import os
from pynamodb.exceptions import DoesNotExist, UpdateError

from blob.blob_model import BlobModel, State
from log_cfg import logger


def event(event, context):
    """
    Triggered by s3 events, object create and remove

    """
# Sample event:
    #
    # _event = { "Records":[
    #       {
    #          "eventVersion":"2.1",
    #          "eventSource":"aws:s3",
    #          "awsRegion":"us-east-1",
    #          "eventTime":"2021-10-14T07:40:55.113Z",
    #          "eventName":"ObjectCreated:Put",
    #          "userIdentity":{
    #             "principalId":"AWS:AROA6L2YJX2JCJYHEJ4UI:serverless-image-processing-test-create"
    #          },
    #          "requestParameters":{
    #             "sourceIPAddress":"94.140.8.209"
    #          },
    #          "responseElements":{
    #             "x-amz-request-id":"7CJHSGZ9MZF9995F",
    #             "x-amz-id-2":"X5OtpRb+P9CuYKDHvjT8z9prnqqsH1yatZchN2uw8/158mcRUVhQNSW/z5ffXLqkLhu+4Kc163vZiRgVk3XaGd8H1NhZCu8N"
    #          },
    #          "s3":{
    #             "s3SchemaVersion":"1.0",
    #             "configurationId":"9b8f4135-35d4-4e07-b8a5-7d68cc95870b",
    #             "bucket":{
    #                "name":"serverless-image-processing-test-serverless-image-processing",
    #                "ownerIdentity":{
    #                   "principalId":"A5IHQSLNTJKZN"
    #                },
    #                "arn":"arn:aws:s3:::serverless-image-processing-test-serverless-image-processing"
    #             },
    #             "object":{
    #                "key":"test/6e7ef3f0-dcb6-4db6-9518-3bc6ec0ba492",
    #                "size":116716,
    #                "eTag":"f04e70e100f653a0e67f32f6098dea1c",
    #                "sequencer":"006167DF06C888A626"
    #             }
    #          }
    #       }
    #    ]
    # }

    logger.debug('event: {}'.format(event))
    for record in event['Records']:
        processRecord(record)

    return {'statusCode': httplib.ACCEPTED}

def processRecord(record):
    """
    This function processes each record in the event stream and 
    calls rekognition to label the image
    """
    event_name = record['eventName']
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    blob_id = key.replace('{}/'.format(os.environ['S3_KEY_BASE']), '')

    if 'ObjectCreated:Put' == event_name:
        try:
            blob = BlobModel.get(hash_key=blob_id)
            blob.mark_uploaded()
            labels = getImageLabels(bucket, key)
            blob.update_state_to_processed_and_add_labels(labels)
        except UpdateError:
            logger.exception('Unable to update blob')

        except botocore.exceptions.ClientError as e:
            logger.exception('Client provided a bad image')
            blob.set_rekognition_error_and_mark_processed(str(e))

        except DoesNotExist:
            logger.exception('Blob does not exist')

def getImageLabels(bucket, key):
    """
    This is a shim to call aws rekognition and return label results
    """
    client = boto3.client('rekognition')
    resp = client.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        }
    )

    output = []
    # I'm assuming that we only need the name labels to return to the customer. 
    for label in resp['Labels']:
        output.append(label['Name'])
    return output
