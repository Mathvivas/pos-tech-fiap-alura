import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from nltk.corpus import stopwords
import re
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
import streamlit as st
import numpy as np

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

def clean_text(text):
    stop_words = set(stopwords.words('english'))
    t = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    return " ".join([w for w in t.split() if w not in stop_words])

def split_data(data):
    y = data['Price']
    X = np.array(data['Embeddings'].tolist())
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return X_train, X_test, y_train, y_test

def data_cleaning(data):
    data['Rating'] = data['Rating'].apply(nota)
    
    data['Availability_ok'] = data['Availability'].apply(disponibilidade)
    data.drop(columns=['Availability'], inplace=True)

    data['Price'] = data['Price'].astype(float)

    data = one_hot_category(data)

    data['Text'] = data['Title'] + ' ' + data['Description']
    data['Clean_Text'] = data['Text'].apply(clean_text)

    data_ml = data.drop(columns=['Title', 'Image', 'Description', 'Text', 'Id', 'Clean_Text'])

    return data_ml
