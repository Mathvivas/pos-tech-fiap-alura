import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
import nltk
nltk.data.path.append("/usr/local/share/nltk_data")
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from nltk.corpus import wordnet
import re
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def nota(coluna):
    if 'One' in coluna:
        return 1
    elif 'Two' in coluna:
        return 2
    elif 'Three' in coluna:
        return 3
    elif 'Four' in coluna:
        return 4
    elif 'Five' in coluna:
        return 5
    
def disponibilidade(coluna):
    if 'ok' in coluna:
        return 1
    else:
        return 0
    
def one_hot_category(data):
    ohe = OneHotEncoder()
    one_hot_encoded = ohe.fit_transform(data[['Category']])
    encoded_df = pd.DataFrame(one_hot_encoded.toarray(),
                        columns=ohe.get_feature_names_out())
    dfe = pd.concat([data, encoded_df], axis=1)
    dfe.drop(columns=['Category'], inplace=True)
    return dfe

def get_wordnet_tag(tag):
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

def clean_text(text):
    # Lowercasing
    text = text.lower()

    # Remove punctuation and special characters
    text = re.sub(r'[^a-z\s]', '', text)

    # Tokenization
    tokens = word_tokenize(text)

    # Removing Stop Words
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [token for token in tokens if token not in stop_words]

    # Lemmatization
    lemmatizer = WordNetLemmatizer()
    lemmatized_tokens = [lemmatizer.lemmatize(token, get_wordnet_tag(tag))
                         for token, tag in pos_tag(filtered_tokens)]

    return " ".join(lemmatized_tokens)

def split_data(data):
    y = data['Price']
    X = data.drop(columns=['Price'])
    X_train, _, _, _ = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return X_train

def data_cleaning(data):
    data['Rating'] = data['Rating'].apply(nota)
    
    data['Availability_ok'] = data['Availability'].apply(disponibilidade)
    data.drop(columns=['Availability'], inplace=True)

    data['Price'] = data['Price'].astype(float)

    data = one_hot_category(data)

    data['Text'] = data['Title'] + ' ' + data['Description']
    data['Clean_Text'] = data['Text'].apply(clean_text)

    data_ml = data.drop(columns=['Image', 'Description', 'Text', 'Id'])

    return data_ml

def vectorize(data):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(data['Clean_Text'])
    tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), columns=vectorizer.get_feature_names_out())
    df = pd.concat([data, tfidf_df], axis=1)
    return df, tfidf_matrix, vectorizer

def find_similar(df, text, vectorizer, tfidf_matrix):
    vec = vectorizer.transform([text])
    similarities = cosine_similarity(vec, tfidf_matrix).flatten()

    top3_indices = similarities.argsort()[-3:][::-1]

    return df.iloc[top3_indices][['Title']]