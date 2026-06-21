"""
ETAPA 1 - Base Kaggle e EDA.
Carrega o dataset, remove leakage e salva versão processada.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from src_config import *

np.random.seed(SEED)

def load(path: Path) -> pd.DataFrame:
    """Carrega o dataset do Kaggle."""
    df = pd.read_csv(path, sep=';', index_col=0)
    print(f'Dataset carregado com {df.shape[0]:,} linhas e {df.shape[1]} colunas.')
    return df

def remove_leakage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove colunas com vazamento temporal.
    'duration' só é conhecida APÓS o contato - não pode entrar no modelo.
    """
    cols_to_drop = [c for c in [DURATION_COL] if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        print(f'Colunas removidas por vazamento temporal: {cols_to_drop}')
    return df

def run() -> pd.DataFrame:
    raw_path = DATA_KAGGLE / 'train.csv'

    if not raw_path.exists():
        raise FileNotFoundError(f'Arquivo Kaggle não encontrado: {raw_path}')
    
    df_raw = load(raw_path)
    df = remove_leakage(df_raw)
    processed_path = DATA_PROCESSED / 'kaggle.csv'
    df.to_csv(processed_path, index=False, header=True)
    print(f'Dataset processado salvo em: {processed_path}')

    # Relatório básico de qualidade
    unknown_counts = {
        col: (df[col] == 'unknown').sum()
        for col in df.select_dtypes('object').columns
        if (df[col] == 'unknown').sum() > 0
    }
    print(f"Valores 'unknown': {unknown_counts}")
    print(f"Duplicatas: {df.duplicated().sum()}")
    print(f"Nulos: {df.isnull().sum().sum()}")
    print(f"Taxa de conversão: {(df[TARGET_COL]=='yes').mean():.2%}")
 
    out_path = DATA_PROCESSED / "bank_jyb_processed.csv"
    df.to_csv(out_path, index=False, sep=',')
    print(f"Dataset processado salvo: {out_path}")
    return df
 
 
if __name__ == "__main__":
    run()