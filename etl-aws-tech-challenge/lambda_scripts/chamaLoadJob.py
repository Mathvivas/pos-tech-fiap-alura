import json
import boto3

glue = boto3.client('glue')
load_job = 'load'

def lambda_handler(event, context):
    record = event['Records'][0]
    key = record['s3']['object']['key']

    if key != 'interim/_EXTRACT_COMPLETE':
        return {"status": "ignored"}

    response = glue.start_job_run(JobName=load_job)
    status = glue.get_job_run(JobName=load_job, RunId=response['JobRunId'])

    status = status['JobRun']

    print(f"Job Run ID: {status['Id']}")
    print(f"Job Status: {status['JobRunState']}")

    return {
            'statusCode': 200,
            'body': json.dumps(status['JobRunState'])
        }