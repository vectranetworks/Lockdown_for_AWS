# <center /> Lockdown for AWS



## <center /> Installation and usage instructions

<center /> Written by
<center /> Vectra.AI

<br /><br />
Version 1.0


-------
<div style="text-align: center">

## Installation steps.

<div style="text-align: left">

Lockdown for AWS is written in Python using the Serverless Framework.   It does require some prerequisites be installed, however I will walk you though the installation of the required prerequisites, setup and configuration of Lockdown for AWS, and deployment into your amazon AWS account.  These instructions will be based on the Mac OS X platform, however this will run under both Windows and Linux with some modifications of the instructions below.

### Requirements:

- Python 3.8.
- A new virtual environment - With some python modules.
- A recent version of Node.JS.
- Serverless Framework installed globally.
- The AWSCLI installed and configured.
- Proper rights within the AWS account to deploy / run.

### A note regarding rights in AWS

There are two "sets" of rights that are required to deploy Lockdown for AWS.  Once is the set of rights that are required to deploy, the second are the rights made available to a specific Lambda function.

Deployment Rights - Generally it's easiest to use an admin account to deploy lockdown for aws.  There is a GitHub issue where a reduced set of rights can be used for deploy that is documented in this issue. https://github.com/serverless/serverless/issues/1439

Lambda Rights - The rights that are available to each Lambda have been reduced to what is necessary for the Lambda to operate.  Each Lambda has a IAM role that is created at deployment time, that contains the policy that the Lambda will use at execution time.



### Step by Step Instructions.

1. We will be using a package manager to install all the requirements.  On the Mac we are using HomeBrew.  On Linux, use the default package manager for your distribution, and on Windows, you can install Chocolaty.

2. Install HomeBrew as per the instructions located at [HomeBrew](https://brew.sh/)

3. Once homebrew is installed perform a 
`brew doctor` and a
`brew update`

4. Once complete, let's install some software we need.

   `brew install nodejs`
   `brew install pyenv`
   `brew install pipenv`
   `brew install git`

   You can use any other methods that you are familiar with to build a python environment including virtualenv, poetry and others.  However in this guide we will be using pyenv and pipenv.

   You also need the docker desktop installed for your client OS.  It is available from here [Docker Desktop](https://www.docker.com/products/docker-desktop)

5. Clone the Lockdown for AWS code to a directory on your local computer.

   `git clone https://github.com/vectranetworks/Lockdown_for_AWS`

6. Cd twice into the code for Lockdown for AWS.  You are looking for the file `serverless.yml`  This is the system configuration file we will be editing soon.

CHECKPOINT #1
At this point let's confirm that our prerequisites have installed properly.  First nodejs

![checking Node and NPM versions](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+14.11.20.png)

Now check pyenv and pipenv
![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+14.13.51.png)

This checkpoint allows me to confirm that my prerequisites are installed and function properly.  If you are not seeing similar output, you will not be able to continue.

7. Now let's install serverless framework into this location.  Issue a
`npm install -g serverless`

8. Now install some needed plugins.
`sls plugin install --name serverless-python-requirements`
`sls plugin install --name serverless-iam-roles-per-function`
`sls plugin install --name serverless-cloudformation-parameters`
`sls plugin install --name serverless-pseudo-parameters`
![Serverless plugin installation](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+14.20.58.png)

CHECKPOINT #2
Let's make sure that the serverless framework is installed and functioning properly.

`sls info`

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+14.29.23.png)
We would expect an error that says that lockdown does not exist, but this confirms that Serverless can communicate with AWS and our AWSCLI is configured properly.

9. Now let's install the needed python version and set up a virtualenv.  To use pyenv and pipenv
`pyenv install 3.8.0`
This will install python 3.8.0.  Now create a new virtualenv with
`pipenv --python 3.8.0`
then enter the new virtualenv with an
`pipenv shell` and a
`pipenv install`

CHECKPOINT #3

10. You will know that all the above steps have worked if you see that your python is running within a virtualenv.
![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+14.03.41.png)

Assuming that all checkpoints 1-3 have passed properly, you are ready to configure and deploy Lockdown for AWS.  If not please reach out for support.

Let's configure how Lockdown for AWS will run.  Open a code editor and edit the `serverless.yml` file.  At the bottom of the file is a set of variables we will edit.

These variables are between the 
\#Start customization here
and
\#End customization here
markers
Locate this at the end of the file and then set the values as needed.  The details on the settings are below:

baseName - Whatever value you select for the basename will be prefaced in front of all objects that Lockdown for AWS creates.  Any value can be used here, but this would be of particular importance if you want to deploy Lockdown for AWS multiple times in one AWS account.

stage - This can be left as is or you can provide a string value.  If you leave the provided value it will default to dev if no stage is provided on the command line.  You can provide a --stage to set it at install time.

minimum_threat_score_for_remediation - is the required threat score that a host will need to hit before it is eligible for remediation.  The next score check must also pass.

minimum_certainty_score_for_remediation - is the required certainty score a host must score before it is eligible for remediation.  Assuming that both score checks pass, we consult the next setting.

remediation_type - How would you like Lockdown for AWS to remediate this host.  Either 'stop' or 'terminate' can be set.

securityHubCustomActionARN - This will be configured in a later step.

snsRemediationNotificationARN - A SNS ARN that you would like to have notifications of actions that Lockdown for AWS takes.  Not required.

11. Once this file is configured, you can deploy Lockdown for AWS.  To deploy it simply run

`sls deploy -v`

NOTE - I recommend that you export the profile you are using for deployment into your shell.  If you do this then Serverless Framework will deploy without specifying a profile on the command line.  You can do something like:
`export AWS_PROFILE=<profile_name>`

![deployment](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+14.56.26.png)

12. You will know that your deploy is complete when you see something like.

![finished deployment](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.01.05.png)

Lockdown for AWS is now deployed.  The last step we need to perform is to configure it inside the AWS console. 

Login to the AWS console using the same account that you deployed into in the previous steps.  Then go to Security Hub.

13. Once in Security Hub select Settings and then Custom Actions.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.10.57.png)

14.Then click on Create custom action.  Then fill out the form that appears.  For example:

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.14.17.png)

15. After you click Create custom action you will now see that acton added to the list of custom actions.  Make sure that you copy the ARN of your new action to the clipboard.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.18.15.png)

Now go to CloudWatch Events.  Once in CloudWatch Events we are going to create a new rule.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.22.10.png)

16. Select Create Rule.

On the left next to Event Pattern Preview select edit.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.25.59.png)

Paste in this


{
  "source": [
    "aws.securityhub"
  ],
  "detail-type": [
    "Security Hub Findings - Custom Action"
  ],
  "resources": [
    "arn:aws:securityhub:us-west-2:123456789012:action/custom/test-action1"
  ]
}

under the resources section above, replace this with the ARN that you copied in step #15 above.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.31.45.png)
Then click Save.

1.  Then on the same screen under Targets click Add target*

2.  Make sure that you have selected Lambda Function on the dropdown select the function that contains queueWriter in the name.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.36.06.png) Then click on Configure details.

19. On the next screen enter values for Name and Description.  Make sure that enabled is selected. 
![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.38.57.png)

Then click on Create rule.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-21+15.40.35.png)

### Setup and Configuration is complete.

### Testing
**NOTE Vectra recommends that you only test Lockdown for AWS when you have the remediation_type set to stop.  DO NOT test Lockdown for AWS when you are using the remediation_type of terminate unless you understand EXACTLY what resource(s) will be terminated.**

20. To test Lockdown for AWS, you can simply go to Security Hub in the Amazon AWS console and locate a host that has a Cognito Detect finding associated with it.  To test the shutdown of that host, click the checkbox next to the finding and then select the Actions button.  Select Lockdown for AWS.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-22+11.47.22.png)



21.  You can now go back to the EC2 console and see that the host related to the finding is shutting down.

![](https://vectra-public-files.s3-us-west-2.amazonaws.com/images/Screenshot+2020-03-22+11.54.12.png)

### Troubleshooting

