import boto3
from blob.blob_model import BlobModel, State
import http.client as httplib
from log_cfg import logger
import requests

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
    event_name = event['Records'][0]['eventName']
    state = event['Records'][0]['dynamodb']['NewImage']['state']
    if 'MODIFY' == event_name and State.PROCESSED.name == state:
        try:
            blob = BlobModel.get(hash_key=blob_id)
            if blob.callback_url:
                r = requests.post(blob.callback_url, data={'blobId': blob_id, 'labels': labels})
                blob.mark_processed_with_callback()
        except UpdateError:
            return {
                'statusCode': httplib.BAD_REQUEST,
                'body': {
                    'error_message': 'Unable to update ASSET'}
            }
        except DoesNotExist:
            return {
                'statusCode': httplib.NOT_FOUND,
                'body': {
                    'error_message': 'BLOB {} not found'.format(blob_id)
                }
            }

    return {'statusCode': httplib.ACCEPTED}
