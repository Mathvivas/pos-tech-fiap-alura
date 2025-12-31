# Tech Challenge 2 - ETL AWS

## Procedimento

- EventBridge/Scheduler chama a Lambda do Extract.
- A Lambda do Extraction chama o Job do Extract.
- O Job do Extract executa o script e insere os dados na pasta raw/.
- Após todos os dados serem inseridos, é criado um arquivo "_EXTRACT_COMPLETE". Seu papel é mostrar que a execução foi concluída.
- O Job do Transform está com uma trigger no raw/_EXTRACT_COMPLETE, ou seja, após sua criação, o Job executa e também cria esse arquivo na pasta interim/ quando for concluído.
- O Job do Load está com uma trigger no interim/_EXTRACT_COMPLETE.

## S3

![Pastas criadas no S3 da AWS](/images/s3-folders.png "Pastas criadas no S3 da AWS")

![Dados inseridos na pasta](/images/dadosInseridos.png "Dados inseridos na pasta")

## Glue

![Jobs do Glue](/images/glue-jobs.png "Jobs do Glue")

## Lambda

**NÃO ESQUECER DE FAZER O DEPLOY DO CÓDIGO**

![Lambda Extraction Job](images/lambdaExtractJob.png "Lambda Extraction Job")

![Lambda Transform Job](images/lambdaTransformJob.png "Lambda Transform Job")

![Lambda Load Job](images/lambdaLoadJob.png "Lambda Load Job")

## Athena

![Athena Query](images/athena-query.png "Athena Query")

## Vídeo de demonstração da aplicação

[![https://www.youtube.com/watch?v=dgmtKAeq_-Y](https://img.youtube.com/vi/dgmtKAeq_-Y/0.jpg)](https://www.youtube.com/watch?v=dgmtKAeq_-Y)
