from models import db
import re
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f'<Usuario {self.username}>'
    
    def set_password(password):
        return generate_password_hash(password)
        

    def check_password(username, password):
        user = User.query.filter_by(username=username).first()
        return check_password_hash(user.password, password)
    
    def check_password_strength(password):
        errors = []
        if len(password) < 8:
            errors.append('Senha deve ter pelo menos 8 caracteres.')
        if not re.search(r'[A-Z]', password):
            errors.append('Senha deve conter pelo menos uma letra maiúscula.')
        if not re.search(r'[a-z]', password):
            errors.append('Senha deve conter pelo menos uma letra minúscula.')
        if not re.search(r'\d', password):
            errors.append('Senha deve conter pelo menos um número.')
        if not re.search(r"[!@#$%^&*()_+={}\[\]:;<>,.?~\\-]", password):
            errors.append('Senha deve conter pelo menos um caracter especial.')
        
        if errors:
            return False, errors
        return True, ['Senha é forte.']