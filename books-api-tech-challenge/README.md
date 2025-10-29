# Projeto Tech Challenge Flask-Streamlit App de Livros

## Como a aplicação funciona?

- Existem dois serviços:
  - Back-end de Flask: [tech-challenge-books-flask-api.onrender.com](https://tech-challenge-books-flask-api.onrender.com)
  - Front-end de Streamlit: [tech-challenge-books-streamlit-api.onrender.com](https://tech-challenge-books-streamlit-api.onrender.com)

<span style="color:red">IMPORTANTE</span>: O serviços ficam em modo repouso após um tempo sem utilização, ou seja, ao abrir o front-end e mandar uma requisição, a aplicação pode falhar. <span style="color:red">É necessário garantir que os dois serviços estejam funcionando.</span>

## Realização do Login

- Ao inserir os dados necessários de usuário e senha, um token será gerado ao clicar no botão de Login.
- Esse token deve ser copiado e colado na aba ```Token``` logo abaixo. **Apenas cole e ele já estará funcionando**, o botão desta aba é somente para gerar outro caso sinta necessidade.



- Rodando a imagem Docker pelo terminal
```docker
docker network create books-net

docker run --name flask-api --network books-net -p 5000:5000 mathvivas/tech-challenge-books-flask-api:latest

docker run --name streamlit-ui --network books-net \
  -e API_URL=http://flask-api:5000 \
  -p 8000:8000 mathvivas/tech-challenge-books-streamlit-api:latest
```