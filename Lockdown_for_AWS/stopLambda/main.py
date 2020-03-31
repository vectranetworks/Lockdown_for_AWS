# noqa
try:
    import unzip_requirements
except ImportError:
    pass
# required for serverless framework to un-compress binaries

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
logger.debug("stopLambda DEPLOYMENT_STAGE is {}".format(DEPLOYMENT_STAGE))


def main(event, context):

    logger.debug("stopLambda received an event object -> {}".format(event))
    logger.debug(
        "stopLambda received context object vars(context) -> {}".format(vars(context))
    )
    logger.debug(
        "stopLambda received context object dir(context) -> {}".format(dir(context))
    )

    remediation_type = event["remediation_type"]
    instance_id = event["instance_id"]
    instance_region = event["instance_region"]

    if event["remediation_type"] == "stop":
        logger.debug(
            "stopLambda received a stop request stopping resource {}".format(
                event["instance_id"]
            )
        )

        ec2_client = boto3.client("ec2")
        try:
            ec2_client.stop_instances(InstanceIds=[instance_id], DryRun=True)

        except ClientError as err:
            if "DryRunOperation" not in str(err):
                raise
            logger.debug("instance stop test was successful. now stopping instance.")

        try:
            response = ec2_client.stop_instances(
                InstanceIds=[instance_id], DryRun=False
            )
            logger.debug(response)
        except ClientError as err:
            logger.debug(err)

    return {
        "body": json.dumps(response),
        "statusCode": 200,
    }
