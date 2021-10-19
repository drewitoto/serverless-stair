from datetime import datetime
import uuid
from enum import Enum
import boto3
import os
from pynamodb.attributes import ListAttribute, UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.models import Model
from log_cfg import logger

BUCKET = os.environ['S3_BUCKET']
KEY_BASE = os.environ['S3_KEY_BASE']

class State(Enum):
    """
    Manage asset states in dynamo with a string field
    Could have used an int as well, or used a custom serializer which is a bit cleaner.
    """
    CREATED = 1
    UPLOADED = 2
    PROCESSED = 3
    PROCESSED_WITH_CALLBACK = 4

class BlobModel(Model):
    class Meta:
        table_name = os.environ['DYNAMODB_TABLE']
        if 'ENV' in os.environ:
            host = 'http://localhost:8000'
        else:
            region = os.environ['REGION']
            host = os.environ['DYNAMODB_HOST']
            # 'https://dynamodb.us-east-1.amazonaws.com'

    blob_id = UnicodeAttribute(hash_key=True)
    callback_url = UnicodeAttribute(null=True)
    labels = ListAttribute(null=False, default=[])
    state = UnicodeAttribute(null=False, default=State.CREATED.name)
    created_time = UTCDateTimeAttribute(null=False, default=datetime.now().astimezone())
    updated_time = UTCDateTimeAttribute(null=False, default=datetime.now().astimezone())
    rekognition_error = UnicodeAttribute(null=True)

    def __str__(self):
        return 'blob_id:{}, callback_url:{}, labels'.format(self.blob_id, self.callback_url, self.labels)

    def get_key(self):
        return u'{}/{}'.format(KEY_BASE, self.blob_id)

    def save(self, conditional_operator=None, **expected_values):
        try:
            self.updated_time = datetime.now().astimezone()
            logger.debug('saving: {}'.format(self))
            super(BlobModel, self).save()
        except Exception as e:
            logger.error('save {} failed: {}'.format(self.blob_id, e), exc_info=True)
            raise e

    def __iter__(self):
        for name, attr in self._get_attributes().items():
            yield name, attr.serialize(getattr(self, name))

    def get_upload_url(self, ttl=60):
        """
        :param ttl: url duration in seconds
        :return: a temporary presigned PUT url
        """
        s3 = boto3.client('s3')
        put_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET,
                'Key': self.get_key()
            },
            ExpiresIn=ttl,
            HttpMethod='PUT'
        )
        logger.debug('upload URL: {}'.format(put_url))
        return put_url

    def generate_new_item(self, callback_url=None):
        self.blob_id = uuid.uuid4().__str__()
        if callback_url:
            self.callback_url = callback_url
        self.save()

    def update_state_to_processed_and_add_labels(self, labels):
        """
        Mark asset as having been processed after rekognition has run and change labels
        """
        if self.state is not State.UPLOADED.name:
            raise AssertionError('State: \"{}\" must be {}'.format(self.state, State.UPLOADED.name))
        self.state = State.PROCESSED.name
        logger.debug('mark asset processed: {}'.format(self.blob_id))
        self.labels = labels
        self.save()
    
    def mark_uploaded(self):
        """
        Mark assest as been having uploaded by client
        """
        self.state = State.UPLOADED.name 
        logger.debug('mark asset uploaded: {}'.format(self.blob_id))
        self.save()

    def mark_processed_with_callback(self):
        """
        Mark asset as having been received via the s3 objectCreated:Put event
        """
        if self.state is not State.PROCESSED.name:
            raise AssertionError('State: \"{}\" must be one of {}'.format(self.state, State.PROCESSED.name))
        self.state = State.PROCESSED_WITH_CALLBACK.name
        logger.debug('mark asset processed and callback complete: {}'.format(self.blob_id))
        self.save()

    def set_rekognition_error(self, error):
        self.rekognition_error = error
        logger.debug('rekognition returned with errors: {}'.format(self.rekognition_error))
        self.save()

    def set_labels(self, labels):
        self.labels = labels
        logger.debug('saved {} labels'.format(len(self.labels)))
        self.save()
