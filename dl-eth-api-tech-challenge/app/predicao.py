import torch
import pandas as pd
import numpy as np
import yfinance as yf

from datetime import timedelta

def predict_future_from_history(
    data_referencia,
    dias_previsao,
    dias_anteriores,
    scaler,
    scaler_inverse,
    model,
    ticker='ETH-USD'
):
    """
    Preve o preco futuro com base em dados historicos fornecidos pelo usuario
    usando um modelo LSTM multi-step de forma recursiva.

    Args:
        data_referencia (str ou datetime): Data a partir da qual as previsões começarão.
        dias_previsao (int): Número de dias futuros a serem previstos.
        dias_anteriores (int): Número de dias históricos para usar como input para a previsão (sequence_length).
        scaler (MinMaxScaler): Scaler original usado para normalizar Close e Volume.
        scaler_inverse (MinMaxScaler): Scaler usado especificamente para reverter o preço 'Close'.
        model (nn.Module): O modelo LSTM treinado.
        ticker (str): O ticker do ativo a ser previsto.

    Returns:
        pandas.DataFrame: DataFrame contendo os preços históricos e previstos.
    """

    data_referencia = pd.to_datetime(data_referencia).normalize()
    dias_previsao = int(dias_previsao)
    dias_anteriores = int(dias_anteriores)

    if dias_previsao <= 0:
        raise ValueError("dias_previsao deve ser maior que zero.")

    if dias_anteriores <= 0:
        raise ValueError("dias_anteriores deve ser maior que zero.")

    # INTERVALO DE DADOS HISTÓRICOS
    # Ajustar para garantir que temos dias_anteriores + 1 dia para a referência
    data_inicial = data_referencia - pd.Timedelta(days=dias_anteriores)

    # =========================
    # BAIXAR DADOS HISTÓRICOS
    # =========================
    historical_df = yf.download(
        ticker,
        start=data_inicial.strftime('%Y-%m-%d'),
        end=(data_referencia + timedelta(days=1)).strftime('%Y-%m-%d'), # Inclui o dia da referência
        progress=False
    )

    if historical_df.empty:
        raise ValueError("Nenhum dado histórico encontrado para o período especificado.")

    # Keep only Close price and Volume
    historical_prices = historical_df[['Close', 'Volume']].copy()
    historical_prices.rename(columns={'Close': 'Historical_Close', 'Volume': 'Historical_Volume'}, inplace=True)
    historical_prices.index = historical_prices.index.tz_localize(None)

    # =====================================
    # PREPARAR ENTRADA PARA LSTM
    # =====================================
    historical_values = historical_prices[['Historical_Close', 'Historical_Volume']].values
    scaled_historical_input = scaler.transform(historical_values)

    # Garantir que a sequência de entrada tenha o comprimento correto
    if len(scaled_historical_input) < dias_anteriores:
        pad_size = dias_anteriores - len(scaled_historical_input)
        # Repetir a última linha (Close, Volume) pad_size vezes para preencher
        padded_input = np.tile(scaled_historical_input[-1], (pad_size, 1))
        current_sequence_input = np.concatenate(
            (scaled_historical_input, padded_input),
            axis=0
        )[-dias_anteriores:]
    else:
        current_sequence_input = scaled_historical_input[-dias_anteriores:].copy()

    # =========================
    # PREDIÇÕES (Recursivo Multi-Step)
    # =========================
    forecasted_values_scaled_close = []
    model.eval()

    steps_predicted_so_far = 0
    # Assumir o último volume conhecido para os inputs futuros
    last_known_volume_scaled = current_sequence_input[-1, 1]

    with torch.no_grad():
        while steps_predicted_so_far < dias_previsao:
            # Preparar o tensor de input para o modelo
            input_tensor = torch.tensor(
                current_sequence_input,
                dtype=torch.float32
            ).view(1, dias_anteriores, 2)

            # Obter a previsão multi-step do modelo
            batch_predictions_scaled_close = model(input_tensor).numpy()[0] # shape (dias_previsao,)

            # Determinar quantos passos de previsão pegar deste batch
            take_n = min(dias_previsao, dias_previsao - steps_predicted_so_far)

            # Adicionar as previsões ao resultado
            forecasted_values_scaled_close.extend(batch_predictions_scaled_close[:take_n])

            # Atualizar current_sequence_input para a próxima rodada de previsão (se houver)
            if steps_predicted_so_far + take_n < dias_previsao:
                # Criar o segmento de "Close" e "Volume" a partir das previsões e do volume assumido
                predicted_closes_to_add_to_input = batch_predictions_scaled_close[:take_n].reshape(-1, 1)
                volume_column_for_predicted = np.full((take_n, 1), last_known_volume_scaled)
                predicted_segment_scaled = np.concatenate((predicted_closes_to_add_to_input, volume_column_for_predicted), axis=1)

                # Deslocar a sequência e concatenar as novas previsões
                current_sequence_input = np.concatenate(
                    (current_sequence_input[take_n:], predicted_segment_scaled),
                    axis=0
                )

            steps_predicted_so_far += take_n

    # Reverter as previsões para a escala original usando scaler_inverse
    predicted_prices = scaler_inverse.inverse_transform(
        np.array(forecasted_values_scaled_close).reshape(-1, 1)
    ).flatten()

    # Gerar as datas futuras para as previsões
    future_dates = pd.date_range(
        start=data_referencia + timedelta(days=1),
        periods=dias_previsao,
        freq='D'
    )

    prediction_df = pd.DataFrame(
        {
            'Predicted_Close': predicted_prices
        },
        index=future_dates
    )

    # =========================
    # COMBINAR RESULTADOS
    # =========================
    all_dates = historical_prices.index.union(future_dates).sort_values()
    result_df = pd.DataFrame(index=all_dates, columns=['Historical_Close', 'Predicted_Close'])
    result_df['Historical_Close'] = historical_prices['Historical_Close']
    result_df.loc[prediction_df.index, 'Predicted_Close'] = prediction_df['Predicted_Close']

    return result_df