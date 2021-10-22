import os
import http.client as httplib
from pynamodb.exceptions import DoesNotExist
from blob.blob_model import BlobModel, State
from log_cfg import logger


def get(event, context):
    """
    Get the labels if any for <blob-id>
    """
    # Sample events using different lambda integrations:
    #
    # _lambda_event = {
    #     'body': {}, 'method': 'GET', 'principalId': '', 'stage': 'dev', 'cognitoPoolClaims': {'sub': ''},
    #     'headers': {'Accept': '*/*', 'CloudFront-Forwarded-Proto': 'https', 'CloudFront-Is-Desktop-Viewer': 'true',
    #                 'CloudFront-Is-Mobile-Viewer': 'false', 'CloudFront-Is-SmartTV-Viewer': 'false',
    #                 'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-Country': 'US',
    #                 'Host': 'c1xblyjsid.execute-api.us-east-1.amazonaws.com', 'User-Agent': 'curl/7.56.1',
    #                 'Via': '1.1 57933097ddb189ecc8b3745fb94cfa94.cloudfront.net (CloudFront)',
    #                 'X-Amz-Cf-Id': 'W95mJn3pc3G8T85Abt2Dj_wLPE_Ar_q0k56uF5yreiaNOMn6P2Nltw==',
    #                 'X-Amzn-Trace-Id': 'Root=1-5a1b453d-1e857d3548e38a1c2827969e',
    #                 'X-Forwarded-For': '75.82.111.45, 216.137.44.17', 'X-Forwarded-Port': '443',
    #                 'X-Forwarded-Proto': 'https'}, 'query': {},
    #     'path': {'asset_id': '0e4e06c6-d2fc-11e7-86c6-6672893a702e'},
    #     'identity': {'cognitoIdentityPoolId': '', 'accountId': '', 'cognitoIdentityId': '', 'caller': '',
    #                  'apiKey': '', 'sourceIp': '75.82.111.45', 'accessKey': '', 'cognitoAuthenticationType': '',
    #                  'cognitoAuthenticationProvider': '', 'userArn': '', 'userAgent': 'curl/7.56.1', 'user': ''},
    #     'stageVariables': {}}
    #
    # _lambda_event_with_timeout = {
    #     'body': {}, 'method': 'GET', 'principalId': '', 'stage': 'dev',
    #     'cognitoPoolClaims': {'sub': ''},
    #     'headers': {'Accept': '*/*', 'CloudFront-Forwarded-Proto': 'https',
    #                 'CloudFront-Is-Desktop-Viewer': 'true',
    #                 'CloudFront-Is-Mobile-Viewer': 'false',
    #                 'CloudFront-Is-SmartTV-Viewer': 'false',
    #                 'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-Country': 'US',
    #                 'Host': 'c1xblyjsid.execute-api.us-east-1.amazonaws.com',
    #                 'User-Agent': 'curl/7.56.1',
    #                 'Via': '1.1 7acf1813f9ec06038d676de15fcfc28f.cloudfront.net (CloudFront)',
    #                 'X-Amz-Cf-Id': 'RBFBVYMys7aDqQ8u2Ktqvd-ZNwy-Kg7LPZ9LBTe-42nnx1wh0b5bGg==',
    #                 'X-Amzn-Trace-Id': 'Root=1-5a1b4655-785e402d33e13e9d533281ef',
    #                 'X-Forwarded-For': '75.82.111.45, 216.137.44.103',
    #                 'X-Forwarded-Port': '443', 'X-Forwarded-Proto': 'https'},
    #     'query': {'timeout': '1000000'},
    #     'path': {'asset_id': '0e4e06c6-d2fc-11e7-86c6-6672893a702e'},
    #     'identity': {'cognitoIdentityPoolId': '', 'accountId': '', 'cognitoIdentityId': '',
    #                  'caller': '', 'apiKey': '', 'sourceIp': '75.82.111.45', 'accessKey': '',
    #                  'cognitoAuthenticationType': '', 'cognitoAuthenticationProvider': '',
    #                  'userArn': '', 'userAgent': 'curl/7.56.1', 'user': ''},
    #     'stageVariables': {}}

    logger.debug('event: {}'.format(event))
    try:
        ttl = os.environ['URL_DEFAULT_TTL']
        try:
            ttl = int(event['query']['timeout'])
        except KeyError or ValueError:
            pass
        blob_id = event['path']['blob_id']
        blob = BlobModel.get(hash_key=blob_id)

        if blob.state == State.CREATED.name:
            return {
                'statusCode': httplib.PRECONDITION_REQUIRED,
                'body': {
                    'errorMessage': 'Image has not been uploaded to be processed. Please upload BLOB {} to s3'.format(blob_id)
                }
            }
        if blob.state == State.UPLOADED.name:
            return {
                'statusCode': httplib.PRECONDITION_REQUIRED,
                'body': {
                    'errorMessage': 'Image has not finished processing. Please retry your request again shortly'
                }
            }
        if blob.rekognition_error:
            return {
                'statusCode': httplib.PRECONDITION_FAILED,
                'body': {
                    'errorMessage': 'Image processing failed due to client error: {}'.format(blob.rekognition_error)
                }
            } 
        labels = []
        if blob.state == State.PROCESSED.name or blob.state == State.PROCESSED_WITH_CALLBACK.name:
            labels = blob.labels

    except DoesNotExist:
        return {
            'statusCode': httplib.NOT_FOUND,
            'body': {
                'errorMessage': 'BLOB {} not found'.format(blob_id)
            }
        }

    return {
        "statusCode": httplib.OK,
        "body": {
            'labels': labels
        }
    }
