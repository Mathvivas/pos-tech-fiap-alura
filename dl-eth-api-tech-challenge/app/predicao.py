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
    model,
    ticker='ETH-USD'
):
    """
    Preve o preco futuro com base em dados historicos fornecidos pelo usuario.
    """

    data_referencia = pd.to_datetime(data_referencia).normalize()
    dias_previsao = int(dias_previsao)
    dias_anteriores = int(dias_anteriores)

    if dias_previsao <= 0:
        raise ValueError("dias_previsao deve ser maior que zero.")

    if dias_anteriores <= 0:
        raise ValueError("dias_anteriores deve ser maior que zero.")

    # INTERVALO DE DADOS HISTÓRICOS
    data_inicial = data_referencia - pd.Timedelta(days=dias_anteriores - 1)

    # =========================
    # BAIXAR DADOS HISTÓRICOS
    # =========================
    historical_df = yf.download(
        ticker,
        start=data_inicial.strftime('%Y-%m-%d'),
        end=(data_referencia + timedelta(days=1)).strftime('%Y-%m-%d'),
        progress=False
    )

    if historical_df.empty:
        raise ValueError("Nenhum dado histórico encontrado.")

    # Keep only Close price
    historical_prices = historical_df[['Close']].copy()
    historical_prices.rename(columns={'Close': 'Historical_Close'}, inplace=True)
    historical_prices.index = historical_prices.index.tz_localize(None)

    # =====================================
    # PREPARAR ENTRADA PARA LSTM
    # =====================================
    historical_values = historical_prices['Historical_Close'].values.reshape(-1, 1)
    scaled_historical_input = scaler.transform(historical_values)

    sequence_length = dias_anteriores

    if len(scaled_historical_input) < sequence_length:
        pad_size = sequence_length - len(scaled_historical_input)

        padded_input = np.repeat(
            scaled_historical_input[-1],
            pad_size
        ).reshape(-1, 1)

        current_sequence = np.concatenate(
            (scaled_historical_input, padded_input),
            axis=0
        )[-sequence_length:]

    else:
        current_sequence = scaled_historical_input[-sequence_length:]

    # =========================
    # PREDIÇÕES
    # =========================
    forecasted_values_scaled = []

    model.eval()

    with torch.no_grad():

        for _ in range(dias_previsao):

            input_tensor = torch.tensor(
                current_sequence,
                dtype=torch.float32
            ).view(1, sequence_length, 1)

            predicted_value_scaled = model(input_tensor).numpy()[0, 0]

            forecasted_values_scaled.append(predicted_value_scaled)

            current_sequence = np.roll(
                current_sequence,
                shift=-1
            )

            current_sequence[-1] = predicted_value_scaled

    predicted_prices = scaler.inverse_transform(
        np.array(forecasted_values_scaled).reshape(-1, 1)
    ).flatten()

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
    result_df['Predicted_Close'] = prediction_df['Predicted_Close']

    return result_df