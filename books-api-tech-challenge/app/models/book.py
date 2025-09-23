from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(600), nullable=False)
    availability = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    image = db.Column(db.String(90), nullable=False)

    def __repr__(self):
        return f'<Book {self.title}>'