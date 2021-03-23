import os
import boto3
from botocore.exceptions import ClientError

class Database:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    @classmethod
    def put_alert(cls, alert):
        response = cls.table.put_item(Item={
            'id': alert['properties']['id'],
            'expires': alert['properties']['expires']
        })
        return response

    @classmethod
    def get_existing_alerts(cls):
        try:
            response = cls.table.scan()
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response['Items']

    @classmethod
    def delete_expired_alert(cls, id):
        try:
            response = cls.table.delete_item(Key={'id': id})
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response
        


# def put_alert(alert):
#     response = table.put_item(Item={
#         'id': alert['properties']['id'],
#         'expires': alert['properties']['expires']
#     })
#     return response

# def get_existing_alerts():
#     try:
#         response = table.scan()
#     except ClientError as e:
#         print(e.response['Error']['Message'])
#     else:
#         return response['Items']

# def delete_expired_alert(id):
#     try:
#         response = table.delete_item(Key={'id': id})
#     except ClientError as e:
#         print(e.response['Error']['Message'])
#     else:
#         return response