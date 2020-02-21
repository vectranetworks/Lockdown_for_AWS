import json


def main(event, context):
    body = {
        "message": "This is queueWriter speaking! - Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }

    response = {"body": json.dumps(body)}

    return response

