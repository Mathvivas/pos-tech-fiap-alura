import pandas as pd
import numpy
from sklearn.preprocessing import OneHotEncoder

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
    one_hot_encoded = ohe.fit_transform(data[['category']])
    encoded_df = pd.DataFrame(one_hot_encoded.toarray(),
                        columns=ohe.get_feature_names_out())
    dfe = pd.concat([data, encoded_df], axis=1)
    dfe.drop(columns=['category'], inplace=True)
    return dfe

def data_cleaning(csv_path):
    data = pd.read_csv(csv_path)

    data['rating'] = data['rating'].apply(nota)
    
    data['availability_ok'] = data['availability'].apply(disponibilidade)
    data.drop(columns=['availability'], inplace=True)

    data['price'] = data['price'].astype(float)

    data = one_hot_category(data)

    data_ml = data.drop(columns=['title', 'image', 'description'])

    return data_ml


