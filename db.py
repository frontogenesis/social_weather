import os
import boto3
from botocore.exceptions import ClientError

class Database:
    
    def __init__(self, table):
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = dynamodb.Table(os.environ[table])

    def put(self, items):
        response = self.table.put_item(Item=items)
        return response

    def get_all(self):
        try:
            response = self.table.scan()
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response['Items']

    def delete(self, id):
        try:
            response = self.table.delete_item(Key={'id': id})
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response