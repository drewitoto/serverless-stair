import boto3
from blob.blob_model import BlobModel, State
from pynamodb.exceptions import DoesNotExist
import http.client as httplib
from log_cfg import logger
import requests
import json

def event(event, context):
    """
    Triggered by s3 events, object create and remove

    """
    # Sample event:
    #
    # _event = { "Records":[
    #       {
    #          "eventID":"09e0813523b2eb0c3500362656be1e2b",
    #          "eventName":"MODIFY",
    #          "eventVersion":"1.1",
    #          "eventSource":"aws:dynamodb",
    #          "awsRegion":"us-east-1",
    #          "dynamodb":{
    #             "ApproximateCreationDateTime":1634201419.0,
    #             "Keys":{
    #                "blob_id":{
    #                   "S":"9421d7a7-9db6-4848-8761-89d3c5a1b97e"
    #                }
    #             },
    #             "NewImage":{
    #                "created_time":{
    #                   "S":"2021-10-14T08:49:59.006870+0000"
    #                },
    #                "updated_time":{
    #                   "S":"2021-10-14T08:50:19.091491+0000"
    #                },
    #                "blob_id":{
    #                   "S":"9421d7a7-9db6-4848-8761-89d3c5a1b97e"
    #                },
    #                "state":{
    #                   "S":"UPLOADED"
    #                },
    #                "labels":{
    #                   "L":[
                        
    #                   ]
    #                }
    #             },
    #             "SequenceNumber":"1600000000078016319551",
    #             "SizeBytes":194,
    #             "StreamViewType":"NEW_IMAGE"
    #          },
    #          "eventSourceARN":"arn:aws:dynamodb:us-east-1:987490795154:table/serverless-image-processing-test/stream/2021-10-14T06:39:10.093"
    #       },
    #       {
    #          "eventID":"fd72cf84cee3eb888416b6faa70af2de",
    #          "eventName":"MODIFY",
    #          "eventVersion":"1.1",
    #          "eventSource":"aws:dynamodb",
    #          "awsRegion":"us-east-1",
    #          "dynamodb":{
    #             "ApproximateCreationDateTime":1634201419.0,
    #             "Keys":{
    #                "blob_id":{
    #                   "S":"9421d7a7-9db6-4848-8761-89d3c5a1b97e"
    #                }
    #             },
    #             "NewImage":{
    #                "created_time":{
    #                   "S":"2021-10-14T08:49:59.006870+0000"
    #                },
    #                "updated_time":{
    #                   "S":"2021-10-14T08:50:19.216716+0000"
    #                },
    #                "blob_id":{
    #                   "S":"9421d7a7-9db6-4848-8761-89d3c5a1b97e"
    #                },
    #                "state":{
    #                   "S":"UPLOADED"
    #                },
    #                "rekognition_error":{
    #                   "S":"An error occurred (AccessDeniedException) when calling the DetectLabels operation: User: arn:aws:sts::987490795154:assumed-role/serverless-image-processing-dev-us-east-1-lambdaRole/serverless-image-processing-test-bucket is not authorized to perform: rekognition:DetectLabels"
    #                },
    #                "labels":{
    #                   "L":[
    #                   ]
    #                }
    #             },
    #             "SequenceNumber":"1700000000078016319640",
    #             "SizeBytes":486,
    #             "StreamViewType":"NEW_IMAGE"
    #          },
    #          "eventSourceARN":"arn:aws:dynamodb:us-east-1:987490795154:table/serverless-image-processing-test/stream/2021-10-14T06:39:10.093"
    #       }
    #    ]
    # }

    logger.debug('event: {}'.format(event))
    for record in event['Records']:
        processRecord(record)
    
    return {'statusCode': httplib.NO_CONTENT}

def processRecord(record):
    """
    Processes a single record in a batch of records. This has the business logic of checking
    if the event is what we expect and then performing a post request for callback.
    """
    event_name = record['eventName']
    state = record['dynamodb']['NewImage']['state']['S']
    callback_url = record['dynamodb']['NewImage'].get('callback_url', None)
    logger.info('Callback url is: {}'.format(callback_url))
    if 'MODIFY' == event_name and State.PROCESSED.name == state and callback_url is not None:
        try:
            callback_url = callback_url['S']
            logger.info('Trying to send label results to provided callback url')
            blob_id = record['dynamodb']['NewImage']['blob_id']['S']
            logger.info(blob_id)
            blob = BlobModel.get(hash_key=blob_id)
            data = None
            if blob.rekognition_error:
                data = json.dumps({'blobId': blob_id, 'rekognition_error': blob.rekognition_error})
            else:
                data = json.dumps({'blobId': blob_id, 'labels': blob.labels})
            r = requests.post(callback_url, data=data)
            blob.mark_processed_with_callback()
        except DoesNotExist:
            logger.exception('Trying to send callback for a blob that does not exist')
        except AssertionError:
            logger.exception('State of item must be PROCESSED to set the state to PROCESSED_WITH_CALLBACK.' + 
            'Callback may have been erroneously sent twice. ')
        except Exception:
            logger.exception('Sending callback to callback url failed')
