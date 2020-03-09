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

    logger.debug("routerLambda received an event object -> {}".format(event))
    logger.debug(
        "routerLambda received context object vars(context) -> {}".format(vars(context))
    )
    logger.debug(
        "routerLambda received context object dir(context) -> {}".format(dir(context))
    )
    # We have received an event from the queue, let's validate the event itself.

    try:
        remediation_type = os.environ.get("REMEDIATION_TYPE")
        stop_lambda_name = os.environ.get("STOP_LAMBDA_NAME")
        terminate_lambda_name = os.environ.get("TERMINATE_LAMBDA_NAME")
        isolate_lambda_name = os.environ.get("ISOLATE_LAMBDA_NAME")
        logger.debug("stop lambda name is {}".format(stop_lambda_name))
        logger.debug("terminate lambda name is {}".format(terminate_lambda_name))
        logger.debug("isolate lambda name is {}".format(isolate_lambda_name))
        logger.debug(
            "remediation_type for this event is {}".format(
                remediation_type.capitalize()
            )
        )
        message_body = event["Records"][0]["body"]  # Keying into the event object here.

        logger.debug("message body type is {}".format(type(message_body)))
        message_json = json.loads(message_body)
        logger.debug(type(message_json))
        logger.debug("message_json is {}".format(message_json))
        aws_account_id = message_json["AwsAccountId"]
        event_type = message_json["Types"]
        event_created_at = message_json["CreatedAt"]
        event_updated_at = message_json["UpdatedAt"]
        security_hub_confidence = message_json["Confidence"]
        security_hub_criticality = message_json["Criticality"]
        event_title = message_json["Title"]
        event_source_url = message_json["SourceUrl"]
        resource_type = message_json["Resources"][0]["Type"]
        resource_id = message_json["Resources"][0]["Id"]
        resource_partition = message_json["Resources"][0]["Partition"]
        resource_region = message_json["Resources"][0]["Region"]
        workflow_state = message_json["WorkflowState"]
        record_state = message_json["RecordState"]

    except (ValueError):
        logger.debug("JSON extraction from the event FAILED!")

    logger.debug(
        "routerLambda received an event for account id {} of type {}.".format(
            aws_account_id, event_type
        )
    )
    logger.debug(
        "The event was created at {}, and last updated at {}".format(
            event_created_at, event_updated_at
        )
    )
    logger.debug("Here are some more details")
    logger.debug("Event Title is {}".format(event_title))
    logger.debug("Security Hub Confidence is {}".format(security_hub_confidence))
    logger.debug("Security Hub Criticality is {}".format(security_hub_criticality))
    logger.debug("Event Source URL {}".format(event_source_url))
    logger.debug("Resource type for the event {}".format(resource_type))
    logger.debug("Resource id for the event {}".format(resource_id))
    logger.debug("Resource partition for the event {}".format(resource_partition))
    logger.debug("Resource region for the event {}".format(resource_region))

    logger.debug(
        "Calling for a {} remediation on instance {}".format(
            remediation_type, resource_id
        )
    )

    event_payload = {}
    event_payload["remediation_type"] = remediation_type
    event_payload["resource_type"] = resource_type
    event_payload["resource_id"] = resource_id
    event_payload["resource_region"] = resource_region
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

    body = {
        "message": "This is routerLambda speaking! - Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }

    string_response = lambda_response["Payload"].read().decode("utf-8")
    parsed_response = json.loads(string_response)
    logger.debug("Lambda invocation message {}".format(parsed_response))
    # logger.debug(
    #     "keyed into body / stoppinginstances [0] {}".format(
    #         parsed_response["body"][0]["StoppingInstances"]
    #     )
    # )
    # Let's figure out what the state transition is.

    return parsed_response

