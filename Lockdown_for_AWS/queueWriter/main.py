try:
    import unzip_requirements
except ImportError:
    pass

import json
import os
import sys
import logging
import re


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()  # This will patch boto3 and any other supported client library to emit xray data.

# Credentails for the lambdas are set via IAM roles in the serverless.yml file.

lambda_client = boto3.client("lambda")  # client object to access lambda APIs
sqs_client = boto3.client("sqs")

# Let's figure out what stage we are running and set the logging and xray configuration based on it.
DEPLOYMENT_STAGE = os.environ.get("DEPLOYMENT_STAGE")
if DEPLOYMENT_STAGE is None:
    logger.debug("No DEPLOYMENT_STAGE environment variable set. Assuming dev.")
    DEPLOYMENT_STAGE = (
        "dev"  # The default stage will be dev even if nothing is specified.
    )


# Next I want to set a specific xray sampling configurarion.
# if we are running in dev or test then all events will be traced with xray
if DEPLOYMENT_STAGE in ["dev", "test"]:
    xray_recorder.configure(sampling=False)
# No need to set the prod configuration as sampling is normally True.
logger.debug("queueWriter DEPLOYMENT_STAGE is {}".format(DEPLOYMENT_STAGE))
xray_recorder.begin_subsegment("read_and_verify_envrionment_variables")
# Reading my necessary variables from the envrionment and making sure that they are valid.  First is threat.
minimum_threat_score_for_remediation = int(
    os.environ.get("MINIMUM_THREAT_SCORE_FOR_REMEDIATION")
)
minimum_certainty_score_for_remediation = int(
    os.environ.get("MINIMUM_CERTAINTY_SCORE_FOR_REMEDIATION")
)

remediation_type = os.environ.get("REMEDIATION_TYPE")

notification_arn = os.environ.get("NOTIFICATION_ARN")

if minimum_threat_score_for_remediation is None:
    logger.critical(
        "CRITICAL ERROR! unable to obtain minumim_threat_score_for_remediation from the execution envrionment. Returned value is None."
    )
    raise RuntimeError(
        "Unable to obtain minimum_threat_score_for_remediation from the execution envrionment."
    )

if minimum_threat_score_for_remediation < 0:
    logger.warning(
        "minimum_threat_score_for_remediation is too low value < 0. setting to 0"
    )
    minimum_threat_score_for_remediation = 0

elif minimum_threat_score_for_remediation > 99:
    logger.warning(
        "minimum_threat_score_for_remediation is too high value > 99. setting to 99"
    )
    minimum_threat_score_for_remediation = 99

# Now checking for the certainty values.

if minimum_certainty_score_for_remediation is None:
    logger.critical(
        "CRITICAL ERROR! unable to obtain minumim_certainty_score_for_remediation from the execution envrionment. Returned value is None."
    )
    raise.RuntimeError("unable to obtain minumim_certainty_score_for_remediation from the execution envrionment.")

if minimum_certainty_score_for_remediation < 0:
    logger.warning(
        "minimum_certainty_score_for_remediation is too low value < 0. setting to 0"
    )
    minimum_certainty_score_for_remediation = 0

elif minimum_certainty_score_for_remediation > 99:
    logger.warning(
        "minimum_certainty_score_for_remediation is too high value > 99. setting to 99"
    )
    minimum_certainty_score_for_remediation = 99

# Next is the remediation type.

if remediation_type is None:
    logger.critical(
        "CRITICAL ERROR! unable to obtain remediation_type from the execution envrionment. Returned value is None."
    )
    raise.RuntimeError("unable to obtain remediation_type from the execution envrionment.")
# I do not want to set a default, although a default of stop might make sense.

# Now let's add some annotations to the xray trace for this subsesgment.

if DEPLOYMENT_STAGE in ["dev", "test"]:
    xray_recorder.put_annotation(
        "minimum_threat_score_for_remediation", minimum_threat_score_for_remediation
    )
    xray_recorder.put_annotation(
        "minimum_certainty_score_for_remediation", minimum_certainty_score_for_remediation
    )
    xray_recorder.put_annotation("remediation_type", remediation_type)
    xray_recorder.end_subsegment()

# Looking good, lets get some information from the event and context objects


def update_xray_annotations(
    event_confidence,
    event_criticality,
    event_title,
    remediation_type,
    minimum_threat_score_for_remediation,
    minimum_certainty_score_for_remediation,
    event_source,
):

    xray_recorder.put_annotation("event_confidence", event_confidence)
    xray_recorder.put_annotation("event_criticality", event_criticality)
    xray_recorder.put_annotation("event_title", event_title)
    xray_recorder.put_annotation("remediation_type", remediation_type)
    xray_recorder.put_annotation(
        "minimum_threat_score_for_remediation", minimum_threat_score_for_remediation
    )
    xray_recorder.put_annotation(
        "minimum_certainty_score_for_remediation",
        minimum_certainty_score_for_remediation,
    )
    xray_recorder.put_annotation("event_source", event_source)


def is_key_present(event, key):
    try:
        buffer = event[key]
    except KeyError:
        return False
    return True


def send_sqs_message(
    queue_url,
    message_body,
    remediation_type,
    threat,
    certainty,
    instance_id,
    instance_region,
    notification_arn,
    event_source,
):

    """
    send_sqs_messages will create the actual message that will be sent to the SQS Queue if remediation is required.
    
    """
    threat_string = str(threat)
    certainty_string = str(certainty)

    response = sqs_client.send_message(
        QueueUrl=queue_url,
        DelaySeconds=0,
        MessageAttributes={
            "remediation_type": {"DataType": "String", "StringValue": remediation_type},
            "threat": {"DataType": "Number", "StringValue": threat_string},
            "certainty": {"DataType": "Number", "StringValue": certainty_string},
            "instance_id": {"DataType": "String", "StringValue": instance_id},
            "instance_region": {"DataType": "String", "StringValue": instance_region},
            "notification_arn": {"DataType": "String", "StringValue": notification_arn},
            "event_source": {"DataType": "String", "StringValue": event_source},
        },
        MessageBody=(json.dumps(message_body)),
    )

    return response


def main(event, context):

    """
    This is the callable that lambda will execute.
    
    
    """
    # Start logging some stats of the event.
    if DEPLOYMENT_STAGE in ["dev", "test"]:
        xray_recorder.begin_subsegment("main")

    logger.debug("queueWriter received an event object -> {}".format(event))
    logger.debug("start operating on aws_request_id {}".format(context.aws_request_id))
    # End logging

    # first let's determine the source of the event.  Either it's from SecHub or it's a test event.

    result = is_key_present(event, "version")
    if result:
        logger.debug("Event was from AWS SECURITYHUB!")
        event_source = "sechub"
        aws_request_id = context.aws_request_id
        invoked_function_arn = context.invoked_function_arn
        event_confidence = event["detail"]["findings"][0]["Confidence"]
        event_criticality = event["detail"]["findings"][0]["Criticality"]
        event_title = event["detail"]["findings"][0]["Title"]
        instance_id = re.search(
            r"arn:aws:ec2:[a-z1-9-]+:\d+:instance\/(i-\w+)",
            event["detail"]["findings"][0]["Resources"][0]["Id"],
        ).group(1)
        instance_region = event["detail"]["findings"][0]["Resources"][0]["Region"]
        message_body = event["detail"]
        logger.debug("instance_id is {}".format(instance_id))
        logger.debug(
            "Received an event directly from Securiy Hub event id={} event_confidence={} event_criticality={} event_title={}".format(
                aws_request_id, event_confidence, event_criticality, event_title
            )
        )
    if not result:
        logger.debug("Event was an injected test event!")
        event_source = "injected"
        logger.debug("Received a test event injected directly into queueWriter.")
        aws_request_id = context.aws_request_id
        invoked_function_arn = context.invoked_function_arn
        event_confidence = event["Confidence"]
        event_criticality = event["Criticality"]
        event_title = event["Title"]
        instance_id = re.search(
            r"arn:aws:ec2:[a-z1-9-]+:\d+:instance\/(i-\w+)", event["Resources"][0]["Id"]
        ).group(1)
        instance_region = event["Resources"][0]["Region"]
        message_body = event
        logger.debug("instance_id is {}".format(instance_id))

        logger.debug(
            "Received an injected test event id={} event_confidence={} event_criticality={} event_title={}".format(
                aws_request_id, event_confidence, event_criticality, event_title
            )
        )

    if DEPLOYMENT_STAGE in ["dev", "test"]:
        update_xray_annotations(
            event_confidence,
            event_criticality,
            event_title,
            remediation_type,
            minimum_threat_score_for_remediation,
            minimum_certainty_score_for_remediation,
            event_source,
        )

    # Do we need to perform a remediation based on this event?

    if not (
        event_criticality >= minimum_threat_score_for_remediation
    ):  # NO REMEDIATION - threat score too low
        logger.info(
            "event_criticality is not >= minimum_threat_score_for_remediation - event_criticality too low! NO REMEDIATION will be performed on this event!"
        )
        body = "event_criticality is not >= minimum_threat_score_for_remediation"  # if the threat score is too low we are done here.

    if not (
        event_confidence >= minimum_certainty_score_for_remediation
    ):  # NO REMEDIATION - certainty score too low
        logger.info(
            "event_confidence is not >= minimum_certainty_score_for_remediation - event_confidence too low! NO REMEDIATION will be performed on this event!"
        )
        body = "event_confidence is not >= minimum_certainty_score_for_remediation"  # if the certainty score is too low we are done here.

    if not (
        event_criticality <= minimum_threat_score_for_remediation
    ):  # REMEDIATION IS POSSIBLE
        logger.info(
            "event_criticality is not <= minimum_threat_score_for_remediation - event_criticality will allow remediation"
        )

        if not (
            event_confidence <= minimum_certainty_score_for_remediation
        ):  # REMEDIATION IS REQUIRED!
            logger.info(
                "event_confidence is not <= minimum_certainty_score_for_remediation - event_confidence will allow remediation"
            )
            logger.info("host remediation is required for this event!!")

            # Start of all remediation logic here

            logger.debug(
                "Start building the message for the SQS queue.  Getting the queue URL"
            )
            queue_url_dict = sqs_client.get_queue_url(
                QueueName="Lockdown_eventSQSQueue"
            )
            queue_url = queue_url_dict["QueueUrl"]
            logger.debug("queue_url is {}".format(queue_url[1]))
            logger.debug("type of queue_url is {}".format(type(queue_url)))

            message_response = send_sqs_message(
                queue_url,
                message_body,
                remediation_type,
                event_criticality,
                event_confidence,
                instance_id,
                instance_region,
                notification_arn,
                event_source,
            )

        # End of all remediation logic here
        elif (
            event_confidence < minimum_certainty_score_for_remediation
        ):  # REMEDIATION WAS CLOSE BUT NOT REQUIRED.
            logger.info(
                "event_confidence >= minimum_certainty_score_for_remediation - event_confidence too low! NO REMEDIATION will be performed on this event!"
            )
            logger.info(
                "event_confidence too low! NO REMEDIATION will be performed on this event!"
            )

        if body == None:
            body = {"message": "queueWriter ran successfully"}

    logger.debug(
        "runtime of function remaining -> {}".format(
            context.get_remaining_time_in_millis()
        )
    )

    return {"body": json.dumps(body)}

