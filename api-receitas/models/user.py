from . import db

class User(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    birthdate = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f'<Usuario {self.username}>'