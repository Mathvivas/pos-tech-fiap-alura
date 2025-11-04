# Projeto Tech Challenge Flask-Streamlit App de Livros

- API Rest em utilizando Web Scraping, Flask, Streamlit e Docker.
- Dados raspados de [Books to Scrape](https://books.toscrape.com/index.html)

## Estrutura do Projeto
```
books-api-tech-challenge/
├── app/
│   ├── __init__.py
|   ├── airflow/
│   ├── routes/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── models/
│   │   ├── __init__.py
|   |   ├── book.py
│   │   └── user.py
│   ├── pages/
│   │   ├── __init__.py
|   |   ├── estatisticas.py
|   |   ├── listar_categorias.py
|   |   ├── listar_livros.py
|   |   ├── machine_learning.py
|   |   ├── metrics.py
|   |   ├── status.py
│   │   └── web_scraping.py
|   ├── app.py
|   ├── books.db
|   ├── data_cleaning.py
|   ├── pagination.py
|   ├── streamlit_app.py
|   ├── utils.py
│   └── config.py
├── data/
|   └── books.csv
├── images/
|   ├── book-logo-nbg.png
|   └── scrap_to_ml-graph.png
|
├── nltk_data/
|   ├── corpora/
|   |   ├── stopwords.zip
|   |   └── wordnet.zip
|   ├── taggers/
|   |   └── averaged_perceptron_tagger_eng.zip
|   └── tokenizers/
|       ├── punkt.zip
|       └── punkt_tab.zip
├── .dockerignore
├── .gitignore
├── Dockerfile_flask
├── Dockerfile_streamlit
├── README.md
├── requirements.txt
├── supervisord_flask.conf
└── supervisord_streamlit.conf
```

- ```app/```: Diretório principal.
  - ```routes/```: Contém todas as rotas em um único arquivo.
  - ```models/```: Contém as classes das tabelas do banco de dados.
  - ```pages/```: Contém as páginas da aplicação.
  - ```app.py```: Arquivo principal do back-end Flask.
  - ```data_cleaning.py```: Principais funções para uso no Machine Learning.
  - ```pagination.py```: Principais funções para a funcionalidade da paginação.
  - ```streamlit_app.py```: Arquivo principal do front-end Streamlit.
  - ```utils.py```: Funções e variáveis.
  - ```config.py```: Configurações da aplicação Flask.
- ```nltk_data/```: Contém os arquivos zip necessários para o funcionamento do modelo de Machine Learning, extraídos pelo Dockerfile.
- ```Dockerfile_flask```: Configurações para o Docker do Flask.
- ```Dockerfile_streamlit```: Configurações para o Docker do Streamlit.
- ```README.md```: Documentação do projeto.
- ```requirements.txt```: Lista de dependências do projeto.
- ```supervisord_flask.conf```: Arquivo de configuração e inicialização do Flask.
- ```supervisord_streamlit.conf```: Arquivo de configuração e inicialização do Streamlit.

## Como a aplicação funciona?

- Existem dois serviços:
  - Back-end de Flask: [tech-challenge-books-flask-api.onrender.com](https://tech-challenge-books-flask-api.onrender.com)
  - Front-end de Streamlit: [tech-challenge-books-streamlit-api.onrender.com](https://tech-challenge-books-streamlit-api.onrender.com)

- <span style="color:red">**IMPORTANTE**</span>: Os serviços ficam em modo repouso após um tempo sem utilização, ou seja, ao abrir o front-end e mandar uma requisição, a aplicação pode falhar. <span style="color:red">**É necessário garantir que os dois serviços estejam funcionando.**</span>
- Ao seguir o link do back-end, o serviço deve apresentar uma tela com o código 404, já estará funcionando.

- <span style="color:green">**POSSÍVEL BUG**</span>: É possível que após digitar algo em um campo de texto, a página recarregue e o valor desapareça. Acredito que seja um bug do Streamlit que acontece somente na primeira inicialização. Após esse acontecimento, os campos são preenchidos normalmente.

### Arquitetura do Serviço

![Arquitetura do Projeto](images/scrap_to_ml-graph.png)

### Realização do Login

- Ao inserir os dados necessários de usuário e senha, um token será gerado ao clicar no botão de Login.
- Esse token deve ser copiado e colado na aba ```Token``` logo abaixo. **Apenas cole e ele já estará funcionando**, o botão desta aba é somente para gerar outro caso sinta necessidade.


## Como rodar a aplicação pelo Docker?

- **[Imagens Docker](https://hub.docker.com/repositories/mathvivas)**

- Rodando as imagens pelo terminal
```docker
docker network create books-net

docker run --name flask-api --network books-net -p 5000:5000 mathvivas/tech-challenge-books-flask-api:latest

docker run --name streamlit-ui --network books-net \
  -e API_URL=http://flask-api:5000 \
  -p 8000:8000 mathvivas/tech-challenge-books-streamlit-api:latest
```

##  Como rodar a aplicação localmente com o projeto do Github?

### Clonar o repositório
```shell
git clone https://github.com/Mathvivas/pos-tech-fiap-alura.git
cd books-api-tech-challenge
```
### Criar um ambiente virtual
```shell
python -m venv .venv
source .venv/bin/activate ou .venv\Scripts\activate
```
### Instalar as dependências
```shell
pip install -r requirements.txt
```
### Executar o back-end dentro da pasta app:
```
gunicorn --bind 0.0.0.0:5000 app:app
```
### Executar o front-end dentro da pasta app:
```
streamlit run streamlit_app.py
```

## Documentação da API

- **[https://tech-challenge-books-flask-api.onrender.com/apidocs/](https://tech-challenge-books-flask-api.onrender.com/apidocs/)**


## Vídeo de demonstração da aplicação

[![https://www.youtube.com/watch?v=PD2pTJ3ie5I](https://img.youtube.com/vi/PD2pTJ3ie5I/0.jpg)](https://www.youtube.com/watch?v=PD2pTJ3ie5I)