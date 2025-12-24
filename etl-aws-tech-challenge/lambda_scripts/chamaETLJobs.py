###################################
####### Extract Job Lambda ######
###################################

import json
import boto3

glue = boto3.client('glue')
extract_job = 'extract'

def lambda_handler(event, context):
    response = glue.start_job_run(JobName=extract_job)
    status = glue.get_job_run(JobName=extract_job, RunId=response['JobRunId'])

    status = status['JobRun']

    print(f'Job Run ID: {status['Id']}')
    print(f'Job Status: {status['JobRunState']}')

    return {
            'statusCode': 200,
            'body': json.dumps(status['JobRunState'])
        }


###################################
####### Transform Job Lambda ######
###################################

import json
import boto3

glue = boto3.client('glue')
transform_job = 'transform'

def lambda_handler(event, context):
    response = glue.start_job_run(JobName=transform_job)
    status = glue.get_job_run(JobName=transform_job, RunId=response['JobRunId'])

    status = status['JobRun']

    print(f'Job Run ID: {status['Id']}')
    print(f'Job Status: {status['JobRunState']}')

    return {
            'statusCode': 200,
            'body': json.dumps(status['JobRunState'])
        }


###################################
######### Load Job Lambda #########
###################################


import json
import boto3

glue = boto3.client('glue')
load_job = 'load'

def lambda_handler(event, context):
    response = glue.start_job_run(JobName=load_job)
    status = glue.get_job_run(JobName=load_job, RunId=response['JobRunId'])

    status = status['JobRun']

    print(f'Job Run ID: {status['Id']}')
    print(f'Job Status: {status['JobRunState']}')

    return {
            'statusCode': 200,
            'body': json.dumps(status['JobRunState'])
        }