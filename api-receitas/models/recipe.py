from . import db

class Recipe(db.Model):
    __tablename__ = 'receitas'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    time_minutes = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('receitas', lazy=True))

    def __repr__(self):
        return f'<Receita {self.title}>'