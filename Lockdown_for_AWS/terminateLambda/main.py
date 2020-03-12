try:
    import unzip_requirements
except ImportError:
    pass

import json
import os
import sys
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

import boto3
from botocore.exceptions import ClientError
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
logger.debug("terminateLambda DEPLOYMENT_STAGE is {}".format(DEPLOYMENT_STAGE))


def main(event, context):

    logger.debug("terminateLambda received an event object -> {}".format(event))
    logger.debug(
        "terminateLambda received context object vars(context) -> {}".format(
            vars(context)
        )
    )
    logger.debug(
        "terminateLambda received context object dir(context) -> {}".format(
            dir(context)
        )
    )

    remediation_type = event["remediation_type"]
    instance_id = event["instance_id"]
    instance_region = event["instance_region"]

    if event["remediation_type"] == "terminate":
        logger.debug(
            "terminateLambda received a terminate request terminateping resource {}".format(
                event["instance_id"]
            )
        )

        ec2_client = boto3.client("ec2")
        try:
            ec2_client.terminate_instances(InstanceIds=[instance_id], DryRun=True)

        except ClientError as err:
            if "DryRunOperation" not in str(err):
                raise
            logger.debug(
                "instance terminate test was successful. now terminateping instance."
            )

        try:
            response = ec2_client.terminate_instances(
                InstanceIds=[instance_id], DryRun=False
            )
            logger.debug(response)
        except ClientError as err:
            logger.debug(err)

    return {
        "body": json.dumps(response),
        "statusCode": 200,
    }

