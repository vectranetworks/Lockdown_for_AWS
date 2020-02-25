import json
import logging
import os
import sys

import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()  # This will patch boto3 and any other supported client library to emit xray data.

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sh.setFormatter(formatter)
logger.addHandler(sh)

lambda_client = boto3.client("lambda")  # client object to access lambda APIs
sns_client = boto3.client("sns")  # client object to access sns topics

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
    logger.critical(
        "CRITICAL ERROR! unable to obtain minumim_threat_score_for_remediation from the execution envrionment. Returned value is None."
    )
    sys.exit(100)

if minimum_threat_score_for_remediation < 0:
    logger.error(
        "minimum_threat_score_for_remediation is too low value < 0. setting to 0"
    )
    minimum_threat_score_for_remediation = 0

elif minimum_threat_score_for_remediation > 99:
    logger.error(
        "minimum_threat_score_for_remediation is too high value > 99. setting to 99"
    )
    minimum_threat_score_for_remediation = 99

# Now checking for the certainty values.

if minimum_certainty_score_for_remediation is None:
    logger.critical(
        "CRITICAL ERROR! unable to obtain minumim_certainty_score_for_remediation from the execution envrionment. Returned value is None."
    )
    sys.exit(101)

if minimum_certainty_score_for_remediation < 0:
    logger.error(
        "minimum_certainty_score_for_remediation is too low value < 0. setting to 0"
    )
    minimum_certainty_score_for_remediation = 0

elif minimum_certainty_score_for_remediation > 99:
    logger.error(
        "minimum_certainty_score_for_remediation is too high value > 99. setting to 99"
    )
    minimum_certainty_score_for_remediation = 99

# Next is the remediation type.

if remediation_type is None:
    logger.critical(
        "CRITICAL ERROR! unable to obtain remediation_type from the execution envrionment. Returned value is None."
    )
    sys.exit(101)


logger.debug(
    "minimum_threat_score_for_remediation value received from the execution envrionment -> %s. Value appears valid",
    minimum_threat_score_for_remediation,
)
logger.debug(
    "minimum_certainty_score_for_remediation value received from the execution envrionment -> %s. Value appears valid",
    minimum_certainty_score_for_remediation,
)

xray_recorder.end_subsegment()


def main(event, context):
    logger.debug("queueWriter received an event object -> %s", event)
    logger.debug(
        "queueWriter received context object vars(context) -> %s", vars(context)
    )
    logger.debug("queueWriter received context object dir(context) -> %s", dir(context))
    logger.debug("start operating on aws_request_id %s", context.aws_request_id)
    logger.debug(
        "runtime of function remaining -> %s", context.get_remaining_time_in_millis()
    )

    body = {
        "message": "This is queueWriter speaking! - Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }

    response = {"body": json.dumps(body)}

    return response

