import sys
import logging
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import (
    avg, 
    col, 
    concat,
    current_date,
    date_format,
    round,
    lag,
    lpad,
    max,
    min,
    quarter,
    stddev,
    to_date,
    when
)
from pyspark.sql.window import Window

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

database_name = 'tech_challenge_2_db'
table_name = 'b3_raw'

dyf = glueContext.create_dynamic_frame.from_catalog(database=database_name, table_name=table_name)
df = dyf.toDF()

logger.info('Schema do DataFrame após leitura da tabela:')
df.printSchema()

df = df.withColumnRenamed('Close', 'Fechamento') \
        .withColumnRenamed('High', 'Máximo') \
        .withColumnRenamed('Low', 'Mínimo') \
        .withColumnRenamed('Open', 'Abertura') \
        .withColumnRenamed('Volume', 'Volume de Transação') \
        .withColumnRenamed('Date', 'Data')

df = df.withColumn('dataproc', date_format('Data', 'yyyyMMdd').cast('int'))

transformed_data_path = 's3://etl-pos-tech-challenge-2-mathvivas/interim/'

df.write.mode('overwrite').partitionBy('dataproc').parquet(transformed_data_path)

glue_client = boto3.client('glue')

transformed_table_name = 'b3_interim'
transformed_table_location = transformed_data_path

try:
    glue_client.get_database(Name=database_name)
except glue_client.exceptions.EntityNotFoundException:
    glue_client.create_database(
        DatabaseInput={'Name': database_name}
    )
    logger.info(f'Banco de dados {database_name} criado no Glue Catalog.')
    
table_input = {
    'Name': transformed_table_name,
    'StorageDescriptor': {
        'Columns': [
            {'Name': "Fechamento", 'Type': 'double'},
            {'Name': "Máximo", 'Type': 'double'},
            {'Name': "Mínimo", 'Type': 'double'},
            {'Name': "Abertura", 'Type': 'double'},
            {'Name': "Volume de Transação", 'Type': 'bigint'}
        ],
        'Location': transformed_table_location,
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

try:
    glue_client.get_table(DatabaseName=database_name, Name=transformed_table_name)
    logger.info(f'Tabela {transformed_table_name} já existe no Glue Catalog. Atualizando a tabela...')
    glue_client.update_table(DatabaseName=database_name, TableInput=table_input)
    logger.info(f'Tabela {transformed_table_name} atualizada no Glue Catalog.')
except glue_client.exceptions.EntityNotFoundException:
    glue_client.create_table(DatabaseName=database_name, TableInput=table_input)
    logger.info(f'Tabela {transformed_table_name} criada no Glue Catalog.')
    
logger.info(f'Tabela {transformed_table_name} disponível no Athena.')

repair_table_query = f'MSCK REPAIR TABLE {database_name}.{transformed_table_name}'
logger.info(f'Executando comando: {repair_table_query}')
spark.sql(repair_table_query)
logger.info(f'Comando MSCK REPAIR TABLE executando com sucesso para a tabela {transformed_table_name}')

job.commit()