try:
    import unzip_requirements
except ImportError:
    pass

import json
import os
import sys

import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()  # This will patch boto3 and any other supported client library to emit xray data.

# Let's figure out what stage we are running and set the logging and xray configuration based on it.
DEPLOYMENT_STAGE = os.environ.get("DEPLOYMENT_STAGE")
if DEPLOYMENT_STAGE is None:
    print("No DEPLOYMENT_STAGE environment variable set. Assuming dev.")
    DEPLOYMENT_STAGE = (
        "dev"  # The default stage will be dev even if nothing is specified.
    )


# Next I want to set a specific xray sampling configurarion.

if DEPLOYMENT_STAGE in ["dev", "test"]:
    xray_recorder.configure(sampling=False)
# No need to set the prod configuration as sampling is normally True.
print(f"queueWriter DEPLOYMENT_STAGE is {DEPLOYMENT_STAGE}")


def main(event, context):

    print(f"queueWriter received an event object -> {event}")
    print(f"queueWriter received context object vars(context) -> {vars(context)}")
    print(f"queueWriter received context object dir(context) -> {dir(context)}")

    body = {
        "message": "This is routerLambda speaking! - Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }

    response = {"body": json.dumps(body)}

    return response
