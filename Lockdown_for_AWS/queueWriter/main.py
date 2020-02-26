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


lambda_client = boto3.client("lambda")  # client object to access lambda APIs
sns_client = boto3.client("sns")  # client object to access sns topics
sqs_client = boto3.client("sqs")

xray_recorder.begin_subsegment("read_and_verify_envrionment_variables")

minimum_threat_score_for_remediation = int(
    os.environ.get("MINIMUM_THREAT_SCORE_FOR_REMEDIATION")
)
minimum_certainty_score_for_remediation = int(
    os.environ.get("MINIMUM_CERTAINTY_SCORE_FOR_REMEDIATION")
)

remediation_type = os.environ.get("REMEDIATION_TYPE")

# Reading my necessary variables from the envrionment and making sure that they are valid.  First is threat.
if minimum_threat_score_for_remediation is None:
    print(
        "CRITICAL ERROR! unable to obtain minumim_threat_score_for_remediation from the execution envrionment. Returned value is None."
    )
    sys.exit(100)

if minimum_threat_score_for_remediation < 0:
    print("minimum_threat_score_for_remediation is too low value < 0. setting to 0")
    minimum_threat_score_for_remediation = 0

elif minimum_threat_score_for_remediation > 99:
    print("minimum_threat_score_for_remediation is too high value > 99. setting to 99")
    minimum_threat_score_for_remediation = 99

# Now checking for the certainty values.

if minimum_certainty_score_for_remediation is None:
    print(
        "CRITICAL ERROR! unable to obtain minumim_certainty_score_for_remediation from the execution envrionment. Returned value is None."
    )
    sys.exit(101)

if minimum_certainty_score_for_remediation < 0:
    print("minimum_certainty_score_for_remediation is too low value < 0. setting to 0")
    minimum_certainty_score_for_remediation = 0

elif minimum_certainty_score_for_remediation > 99:
    print(
        "minimum_certainty_score_for_remediation is too high value > 99. setting to 99"
    )
    minimum_certainty_score_for_remediation = 99

# Next is the remediation type.

if remediation_type is None:
    print(
        "CRITICAL ERROR! unable to obtain remediation_type from the execution envrionment. Returned value is None."
    )
    sys.exit(101)

# Now let's add some annotations to the xray trace for this subsesgment.
xray_recorder.put_annotation(
    "minimum_threat_score_for_remediation", minimum_threat_score_for_remediation
)
xray_recorder.put_annotation(
    "minimum_certainty_score_for_remediation", minimum_certainty_score_for_remediation
)
xray_recorder.put_annotation("remediation_type", remediation_type)
xray_recorder.end_subsegment()

# Looking good, lets get some information from the event and context objects


def main(event, context):

    """
    This is the callable that lambda will execute.
    
    
    """
    xray_recorder.begin_subsegment("main")
    print(
        f"minimum_threat_score_for_remediation value received from the execution envrionment -> {minimum_threat_score_for_remediation}. Value appears valid"
    )
    print(
        f"minimum_certainty_score_for_remediation value received from the execution envrionment -> {minimum_certainty_score_for_remediation}. Value appears valid"
    )
    print(f"queueWriter received an event object -> {event}")
    print(f"queueWriter received context object vars(context) -> {vars(context)}")
    print(f"queueWriter received context object dir(context) -> {dir(context)}")
    print(f"start operating on aws_request_id {context.aws_request_id}")
    print(f"runtime of function remaining -> {context.get_remaining_time_in_millis()}")

    aws_request_id = context.aws_request_id
    invoked_function_arn = context.invoked_function_arn
    event_confidence = event["Confidence"]
    event_criticality = event["Criticality"]
    event_title = event["Title"]

    print(
        f"Received event id={aws_request_id} event_confidence={event_confidence} event_criticality={event_criticality} event_title={event_title}"
    )
    xray_recorder.put_annotation("event_confidence", event_confidence)
    xray_recorder.put_annotation("event_criticality", event_criticality)
    xray_recorder.put_annotation(
        "minimum_threat_score_for_remediation", minimum_threat_score_for_remediation
    )
    xray_recorder.put_annotation(
        "minimum_certainty_score_for_remediation",
        minimum_certainty_score_for_remediation,
    )

    # Do we need to perform a remediation based on this event?

    if (
        event_criticality < minimum_threat_score_for_remediation
    ):  # NO REMEDIATION - threat score too low
        print(
            "event_criticality < minimum_threat_score_for_remediation - event_criticality too low! NO REMEDIATION will be performed on this event!"
        )
        return "event_criticality < minimum_threat_score_for_remediation"

    if (
        event_confidence < minimum_certainty_score_for_remediation
    ):  # NO REMEDIATION - certainty score too low
        print(
            "event_confidence < minimum_certainty_score_for_remediation - event_confidence too low! NO REMEDIATION will be performed on this event!"
        )
        return "event_confidence < minimum_certainty_score_for_remediation"

    if (
        event_criticality >= minimum_threat_score_for_remediation
    ):  # REMEDIATION IS POSSIBLE
        print(
            "event_criticality >= minimum_threat_score_for_remediation - event_criticality will allow remediation"
        )

        if (
            event_confidence >= minimum_certainty_score_for_remediation
        ):  # REMEDIATION IS REQUIRED!
            print(
                "event_confidence >= minimum_certainty_score_for_remediation - event_confidence will allow remediation"
            )
            print("host remediation is required for this event!!")

            # Start of all remediation logic here

            print(
                "Start building the message for the SQS queue.  Getting the queue URL"
            )
            queue_url = sqs_client.get_queue_url(QueueName="Lockdown_eventSQSQueue")
            print(f"queue_url is {queue_url['QueueUrl']}")
            print(f"type of queue_url is {type(queue_url)}")

            sqs_send_response = sqs_client.send_message(
                QueueUrl=queue_url["QueueUrl"],
                MessageBody=json.dumps(event),
                DelaySeconds=0,
            )

            print(sqs_send_response)

        # End of all remediation logic here
        elif (
            event_confidence < minimum_certainty_score_for_remediation
        ):  # REMEDIATION WAS CLOSE BUT NOT REQUIRED.
            print(
                "event_confidence >= minimum_certainty_score_for_remediation - event_confidence too low! NO REMEDIATION will be performed on this event!"
            )
            print(
                "event_confidence too low! NO REMEDIATION will be performed on this event!"
            )

    body = {
        "message": "This is queueWriter speaking! - Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }

    response = {"body": json.dumps(body)}

    return response

