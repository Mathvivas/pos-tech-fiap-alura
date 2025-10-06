import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split

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

def data_cleaning(data):
    data['Rating'] = data['Rating'].apply(nota)
    
    data['Availability_ok'] = data['Availability'].apply(disponibilidade)
    data.drop(columns=['Availability'], inplace=True)

    data['Price'] = data['Price'].astype(float)

    data = one_hot_category(data)

    data_ml = data.drop(columns=['Title', 'Image', 'Description'])

    return data_ml


def split_data(data):
    y = data['Price']
    X = data.drop(columns=['Price'])
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )
    return X_train, X_test, y_train, y_test