import os

creds = {
        'florida_storms': {
            'db_table_env_var': 'DYNAMODB_TABLE_FLORIDA',
            'hashtag': '#FLwx',
            'api_endpoint': 'area=FL',
            'overlays': True,
            'consumer_key': os.environ['TWITTER_CONSUMER_KEY_FLORIDA'],
            'consumer_secret': os.environ['TWITTER_CONSUMER_SECRET_FLORIDA'],
            'access_token': os.environ['TWITTER_ACCESS_TOKEN_FLORIDA'],
            'access_token_secret': os.environ['TWITTER_ACCESS_TOKEN_SECRET_FLORIDA']
        },
        'palmetto_storms': {
            'db_table_env_var': 'DYNAMODB_TABLE_PALMETTO',
            'hashtag': '#scwx',
            'api_endpoint': 'area=SC',
            'overlays': False,
            'consumer_key': os.environ['TWITTER_CONSUMER_KEY_PALMETTO'],
            'consumer_secret': os.environ['TWITTER_CONSUMER_SECRET_PALMETTO'],
            'access_token': os.environ['TWITTER_ACCESS_TOKEN_PALMETTO'],
            'access_token_secret': os.environ['TWITTER_ACCESS_TOKEN_SECRET_PALMETTO']
        },
        'ray_hawthorne': {
            'db_table_env_var': 'DYNAMODB_TABLE',
            'db_table_env_var_stories': 'DYNAMODB_TABLE_hazard_stories',
            'hashtag': '#FLwx',
            'api_endpoint': 'area=MO',
            'overlays': True,
            'consumer_key': os.environ['TWITTER_CONSUMER_KEY'],
            'consumer_secret': os.environ['TWITTER_CONSUMER_SECRET'],
            'access_token': os.environ['TWITTER_ACCESS_TOKEN'],
            'access_token_secret': os.environ['TWITTER_ACCESS_TOKEN_SECRET']
        },
    }