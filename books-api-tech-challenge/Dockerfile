FROM python:3.11.13
WORKDIR /books
COPY . /books
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "./app/app.py"]