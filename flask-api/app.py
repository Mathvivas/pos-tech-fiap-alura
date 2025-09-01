from flask import Flask, jsonify, request
from flask_httpauth import HTTPBasicAuth
from flasgger import Swagger
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

app.config['SWAGGER'] = {
    'title': 'My Flask API',
    'uiversion': 3
}

swagger = Swagger(app)

auth = HTTPBasicAuth()

users = {
    "user1": "password1",
    "user2": "password2"
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

@app.route('/hello', methods=['GET'])
@auth.login_required
def home():
    return 'Hello, Flask!'

items = []

@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(items)

@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()
    items.append(data)
    return jsonify(data), 201

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.get_json()
    if 0 <= item_id < len(items):
        items[item_id].update(data)
        return jsonify(items[item_id])
    return jsonify({'error': 'Item not found'}), 404

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    if 0 <= item_id < len(items):
        removed = items.pop(item_id)
        return jsonify(removed)
    return jsonify({'error': 'Item not found'}), 404

def get_title(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip()
        return jsonify({"title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/scrape/title', methods=['GET'])
@auth.login_required
def scrape_title():
    """
    Extract the title of a web page provided bu the URL.
    ---
    security:
    - BasicAuth: []
    parameters:
      - name: url
        in: query
        type: string
        required: true
        description: URL of the web page
    responses:
        200:
            description: Web page title
    """
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    return get_title(url)


# http://127.0.0.1:5000/scrape/content?url=https://tvnativoos.com.br/wfe/tecnologia-ia-teria-encontrado-forma-de-nao-ser-controlada-por-humanos-entenda/
def get_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        headers = []
        for header_tag in ['h1', 'h2', 'h3']:
            for header in soup.find_all(header_tag):
                headers.append(header.get_text(strip=True))
        
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        return jsonify({'headers': headers, 'paragraphs': paragraphs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/scrape/content', methods=['GET'])
@auth.login_required
def scrape_content():
    """
    Extract headers and paragraphs from a web page provided bu the URL.
    ---
    security:
    - BasicAuth: []
    parameters:
      - name: url
        in: query
        type: string
        required: true
        description: URL of the web page
    responses:
        200:
            description: Web page title
    """
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    return get_content(url)

if __name__ == '__main__':
    app.run(debug=True)