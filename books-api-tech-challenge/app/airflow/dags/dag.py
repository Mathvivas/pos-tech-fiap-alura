from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator
from pages.web_scraping import import_df_to_db
from data_cleaning import data_cleaning, vectorize, split_data, find_similar
import pendulum

with DAG(
    dag_id='scrap_to_ml',
    start_date=pendulum.today('UTC').add(days=-1),
    schedule=None
) as dag:
    
    scrap = PythonOperator(
        task_id='web_scraping',
        python_callable=import_df_to_db
    )

    clean = PythonOperator(
        task_id='data_cleaning',
        python_callable=data_cleaning,
        op_kwargs={'data_url': "{{ ti.xcom_pull(task_ids='web_scraping') }}"}
    )

    vector = PythonOperator(
        task_id='vectorize',
        python_callable=vectorize,
        op_kwargs={'data_url': "{{ ti.xcom_pull(task_ids='data_cleaning') }}"}
    )

    split = PythonOperator(
        task_id='split_data',
        python_callable=split_data,
        op_kwargs={'data_url': "{{ ti.xcom_pull(task_ids='data_cleaning') }}"}
    )

    similar = PythonOperator(
        task_id='find_similar',
        python_callable=find_similar,
        op_kwargs={
            'text': "adventure", 
            'vectorizer': "{{ ti.xcom_pull(task_ids='vectorize', key='vectorizer') }}", 
            'tfidf_matrix': "{{ ti.xcom_pull(task_ids='vectorize', key='tfidf_matrix') }}",
            'data_url': "{{ ti.xcom_pull(task_ids='vectorize', key='data_url') }}",
            }
    )

    scrap >> clean >> [vector, split]
    vector >> similar