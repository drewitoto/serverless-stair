# Serverless REST API
This example demonstrates how to setup a [RESTful Web Service](https://en.wikipedia.org/wiki/Representational_state_transfer#Applied_to_web_services) 
using [Presigned URLs](http://boto3.readthedocs.io/en/latest/guide/s3.html?highlight=presigned#generating-presigned-urls) 
to manage image uploads and then processing them by labelling. This uses the serverless example project [aws-python-pynamodb-s3-sigurl](https://github.com/serverless/examples/tree/master/aws-python-pynamodb-s3-sigurl) as a start point.

The initial POST creates an asset entry in dynamo and returns a presigned upload URL. 
This is used to upload the asset without needing any credentials. 
An s3 event triggers another lambda method to process the upload image using rekognition.
One can then initiate a get to see what labels were found in the image. If there was a callback url provided, that url will be called with the image label results. 

DynamoDB is used to store the index and tracking data referring to the assets on s3.

## Structure
This service has a separate directory for all the assets operations. 
For each operation exactly one file exists e.g. `blobs/create.py`. In each of these files there is exactly one function defined.
### Model
The idea behind the `blob` directory is that in case you want to create a service containing multiple resources e.g. users, notes, 
comments you could do so in the same service. 
While this is certainly possible you might consider creating a separate service for each resource. 
It depends on the use-case and your preference.
### API GW Integration model
All methods use `lambda` integration as that reduces the API GW interference in the payload.
### Logging
The log_cfg.py is an alternate way to setup the python logging to be more friendly wth AWS lambda.
The lambda default logging config is to not print any source file or line number which makes it harder to correleate with the source.

Adding the import:
```python
    from log_cfg import logger
```
at the start of every event handler ensures that the format of the log messages are consistent, customizable and all in one place. 

Default format uses:
```python
'%(asctime)-15s %(process)d-%(thread)d %(name)s [%(filename)s:%(lineno)d] :%(levelname)8s: %(message)s'
```

### Notes
Initial scaffold copied from the aws-python-pynamodb-s3-sigurl example.
Right now there's no good way to return rekognition client exceptions back to the original uploader since the processing is done asynchronously. We just store the error and return it through the callback url or on the next get. Currently the user has no way to update or delete their images.

## Setup

```bash
npm install
```

## Deploy

In order to deploy the endpoint simply run

```bash
serverless deploy
```

The expected result should be similar to:

```bash
%> sls deploy                                                                               
Serverless: Parsing Python requirements.txt
Serverless: Installing required Python packages for runtime python3.6...
Serverless: Linking required Python packages...
Serverless: Packaging service...
Serverless: Excluding development dependencies...
Serverless: Unlinking required Python packages...
Serverless: Uploading CloudFormation file to S3...
Serverless: Uploading artifacts...
Serverless: Uploading service .zip file to S3 (7.14 MB)...
Serverless: Validating template...
Serverless: Updating Stack...
Serverless: Checking Stack update progress...
............................................
Serverless: Stack update finished...
Service Information
service: serverless-image-processing
stage: dev
region: us-east-1
stack: serverless-image-processing-dev
resources: 39
api keys:
  None
endpoints:
  POST - https://trknmunrdl.execute-api.us-east-1.amazonaws.com/dev/blobs
  GET - https://trknmunrdl.execute-api.us-east-1.amazonaws.com/dev/blobs/{blob_id}
functions:
  create: serverless-image-processing-test-create
  bucket: serverless-image-processing-test-bucket
  stream: serverless-image-processing-test-stream
  get: serverless-image-processing-test-get
```
## Running Tests
In order to run the tests, first install requirements from the base directory 
```
pip install -r requirements.txt
```
To run the tests you must be within the /test directory. The command is
```
pytest 
```
or on windows
```
python -m pytest
```
Currently there's no test support for callbacks

## Usage

You can create, or get, the blob with the following commands:
The $URL is the base URL specified in the POST endpoint above.

`jsonpp` used to format the output for visibility but is not required for use.

### Get an asset pre-signed upload URL

```bash
%> curl -sX POST $URL | jsonpp
{
  "statusCode": 201,
  "body": {
    "upload_url": "<SIGNED-URL>",
    "id": "1a5ea69a-d30c-11e7-90d0-129b5a655d2d"
  }
}
```

### Upload a file to the URL
```bash
%> curl -sX PUT --upload-file file.txt "<SIGNED_URL>"
```

### Upload a file after pre-signed URL has expired
```bash
%> curl -sX PUT --upload-file file.txt "<SIGNED-URL>"
<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>AccessDenied</Code>
    <Message>Request has expired</Message>
    <Expires>2027T01:03:04Z</Expires>
    <ServerTime>2027T01:05:41Z</ServerTime>
    <RequestId>D4EFA3C1A8DDD525</RequestId>
    <HostId>vS12oM24ZidzjG0JZon/y/8XD8whCKD/0JZappUNOekOJ3Eqp10Q5ne0emPVM/Mx6K1lYr0bi6c=</HostId>
</Error>
```

### Get image labels:
```bash
%> curl -sX GET "$URL/1a5ea69a-d30c-11e7-90d0-129b5a655d2d" | jsonpp
{
  "statusCode": 200,
  "body": {
    "labels": "[IMAGE_LABELS]"
  }
}
```

### Callback Response:
```
{
  "blobId": "<BLOB_ID>"
  "labels": "[LABELS]"
}
```

## Scaling

### AWS Lambda

By default, AWS Lambda limits the total concurrent executions across all functions within a given region to 100. 
The default limit is a safety limit that protects you from costs due to potential runaway or recursive functions during initial development and testing. 
To increase this limit above the default, 
follow the steps in [To request a limit increase for concurrent executions](http://docs.aws.amazon.com/lambda/latest/dg/concurrent-executions.html#increase-concurrent-executions-limit).


### DynamoDB

The table is set to on-demand since that scales better.
I f you want to change the provisioning, this is can be done via settings in the `serverless.yml`.

```yaml
  ProvisionedThroughput:
    ReadCapacityUnits: 1
    WriteCapacityUnits: 1
```
