try:
    import unzip_requirements
except ImportError:
    pass

import json
import os
import sys
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()  # This will patch boto3 and any other supported client library to emit xray data.

lambda_client = boto3.client("lambda")
# Let's figure out what stage we are running and set the logging and xray configuration based on it.
DEPLOYMENT_STAGE = os.environ.get("DEPLOYMENT_STAGE")
if DEPLOYMENT_STAGE is None:
    logging.debug("No DEPLOYMENT_STAGE environment variable set. Assuming dev.")
    DEPLOYMENT_STAGE = (
        "dev"  # The default stage will be dev even if nothing is specified.
    )


# Next I want to set a specific xray sampling configurarion.

if DEPLOYMENT_STAGE in ["dev", "test"]:
    xray_recorder.configure(sampling=False)
# No need to set the prod configuration as sampling is normally True.
logger.debug("routerLambda DEPLOYMENT_STAGE is {}".format(DEPLOYMENT_STAGE))


def main(event, context):

    remediation_type = os.environ.get("REMEDIATION_TYPE")
    stop_lambda_name = os.environ.get("STOP_LAMBDA_NAME")
    terminate_lambda_name = os.environ.get("TERMINATE_LAMBDA_NAME")

    logger.debug("routerLambda received an event object -> {}".format(event))
    logger.debug(
        "routerLambda received context object vars(context) -> {}".format(vars(context))
    )
    logger.debug(
        "routerLambda received context object dir(context) -> {}".format(dir(context))
    )
    # We have received an event from the queue, let's validate the event itself.

    remediation_type = event["Records"][0]["messageAttributes"]["remediation_type"][
        "stringValue"
    ]
    instance_id = event["Records"][0]["messageAttributes"]["instance_id"]["stringValue"]
    instance_region = event["Records"][0]["messageAttributes"]["instance_region"][
        "stringValue"
    ]
    certainty = event["Records"][0]["messageAttributes"]["certainty"]["stringValue"]
    event_source = event["Records"][0]["messageAttributes"]["event_source"][
        "stringValue"
    ]
    notification_arn = event["Records"][0]["messageAttributes"]["notification_arn"][
        "stringValue"
    ]
    threat = event["Records"][0]["messageAttributes"]["threat"]["stringValue"]

    logger.debug(
        "Received an event of type {}. the remediation type is {} against the instance {} in region {}".format(
            event_source, remediation_type, instance_id, instance_region
        )
    )

    event_payload = {}
    event_payload["remediation_type"] = remediation_type
    event_payload["instance_id"] = instance_id
    event_payload["instance_region"] = instance_region
    payload_to_send = json.dumps(event_payload)
    logger.debug("payload_to_send {}".format(payload_to_send))

    if remediation_type == "stop":  # stop, terminate, isolate
        logger.debug("calling stopLambda to stop instance {resource_id}")
        lambda_response = lambda_client.invoke(
            FunctionName=stop_lambda_name,
            InvocationType="RequestResponse",
            Payload=payload_to_send,
        )
        logger.debug("lambda_response {}".format(lambda_response))

    if remediation_type == "terminate":
        logger.debug("calling terminateLambda to terminate instance {resource_id}")
        lambda_response = lambda_client.invoke(
            FunctionName=terminate_lambda_name,
            InvocationType="RequestResponse",
            Payload=payload_to_send,
        )
        logger.debug("lambda_response {}".format(lambda_response))

    string_response = lambda_response["Payload"].read().decode("utf-8")
    parsed_response = json.loads(string_response)
    logger.debug("Lambda invocation message {}".format(parsed_response))

    return parsed_response
