- Rodando pelo terminal
```docker
docker network create books-net

docker run --name flask-api --network books-net -p 5000:5000 mathvivas/tech-challenge-books-flask-api:latest

docker run --name streamlit-ui --network books-net \
  -e API_URL=http://flask-api:5000 \
  -p 8000:8000 mathvivas/tech-challenge-books-streamlit-api:latest
```