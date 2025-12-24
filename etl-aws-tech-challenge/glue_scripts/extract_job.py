import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

import subprocess
import sys

packages_to_install = ["pandas_datareader", "yfinance"]
for package in packages_to_install:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])

import yfinance as yf
import pandas_datareader as pdr
import pandas as pd
import boto3
import logging
from pyspark.sql.functions import current_date, date_format
from pyspark.sql.functions import day

logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)


ativo = '^BVSP'

# data_inicial = '2025-11-01'
# data_final = '2025-11-30'

# cotacoes = yf.download(ativo, data_inicial, data_final)
cotacoes = yf.download(ativo, period="1mo")
cotacoes.reset_index(inplace=True)

# Converte de pandas DataFrame para PySpark DataFrame
cotacoes = spark.createDataFrame(cotacoes)

# Renomeando as colunas
cotacoes = cotacoes.withColumnRenamed("('Date', '')", "Date") \
       .withColumnRenamed("('Close', '^BVSP')", "Close") \
       .withColumnRenamed("('High', '^BVSP')", "High") \
       .withColumnRenamed("('Low', '^BVSP')", "Low") \
       .withColumnRenamed("('Open', '^BVSP')", "Open") \
       .withColumnRenamed("('Volume', '^BVSP')", "Volume")
       
# Modificando a data
cotacoes = cotacoes.withColumn('Date', date_format('Date', 'yyyy-MM-dd').cast('date'))
cotacoes = cotacoes.withColumn('dataproc', date_format('Date', 'yyyyMMdd').cast('int'))

# log do schema do DataFrame
logger.info("======= Schema do DataFrame: =======\n")
cotacoes.printSchema()

raw_data_path = 's3://etl-pos-tech-challenge-2-mathvivas/raw/'

cotacoes.write.mode('overwrite').partitionBy('dataproc').parquet(raw_data_path)

glue_client = boto3.client('glue')

database_name = 'tech_challenge_2_db'
table_name = 'b3_raw'
table_location = raw_data_path


try:
    glue_client.get_database(Name=database_name)
except glue_client.exceptions.EntityNotFoundException:
    glue_client.create_database(
        DatabaseInput={'Name': database_name}
    )
    logger.info(f'Banco de dados {database_name} criado no Glue Catalog.')
    
# Definição da tabela
table_input = {
    'Name': table_name,
    'StorageDescriptor': {
        'Columns': [
            {'Name': "Close", 'Type': 'double'},
            {'Name': "High", 'Type': 'double'},
            {'Name': "Low", 'Type': 'double'},
            {'Name': "Open", 'Type': 'double'},
            {'Name': "Volume", 'Type': 'bigint'},
            {'Name': "Date", 'Type': 'date'}
        ],
        'Location': table_location,
        'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
        'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
        'Compressed': False,
        'SerdeInfo': {
            'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
            'Parameters': {'serialization.format': '1'}
        }
    },
    'PartitionKeys': [{'Name': 'dataproc', 'Type': 'int'}],
    'TableType': 'EXTERNAL_TABLE'
}

# Cria ou atualiza a tabela no Glue Catalog
try:
    glue_client.get_table(DatabaseName=database_name, Name=table_name)
    logger.info(f'Tabela {table_name} já existe no Glue Catalog. Atualizando a tabela...')
    glue_client.update_table(DatabaseName=database_name, TableInput=table_input)
    logger.info(f'Tabela {table_name} atualizada no Glue Catalog.')
except glue_client.exceptions.EntityNotFoundException:
    glue_client.create_table(DatabaseName=database_name, TableInput=table_input)
    logger.info(f'Tabela {table_name} criada no Glue Catalog.')

logger.info(f'Tabela {table_name} disponível no Athena.')

# Executa MSCK REPAIR TABLE para descobrir partições
repair_table_query = f'MSCK REPAIR TABLE {database_name}.{table_name}'
logger.info(f'Executando comando: {repair_table_query}')
spark.sql(repair_table_query)
logger.info(f'Comando MSCK REPAIR TABLE executando com sucesso para a tabela {table_name}.')


job.commit()