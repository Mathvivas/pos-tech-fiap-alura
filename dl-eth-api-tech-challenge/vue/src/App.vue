<script setup>
import { computed, reactive, ref } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ethereum-predictor-latest.onrender.com'
// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const form = reactive({
  data_referencia: '',
  dias_previsao: 10,
  dias_anteriores: 30,
})

const isLoading = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const predictionResults = ref(null)

const isFormValid = computed(() => {
  const diasPrevisao = Number(form.dias_previsao)
  const diasAnteriores = Number(form.dias_anteriores)

  return Boolean(form.data_referencia) && diasPrevisao > 0 && diasAnteriores > 0
})

const chartData = computed(() => {
  if (!predictionResults.value?.length) return null

  const allData = predictionResults.value
    .map(item => ({
      date: item.date,
      historical:
        item.historical_close != null
          ? Number(item.historical_close)
          : null,
      predicted:
        item.predicted_close != null
          ? Number(item.predicted_close)
          : null
    }))
    .sort((a, b) => new Date(a.date) - new Date(b.date))

    console.log('predictionResults', predictionResults.value)
    console.log('allData', allData)
    console.log(JSON.stringify(allData, null, 2))

  const lastHistoricalItem = allData
    .filter(item => item.historical != null)
    .slice(-1)[0]

  const predictedData = allData.map(item => {
    if (item.date === lastHistoricalItem?.date) {
      return lastHistoricalItem.historical
    }
    return item.predicted
  })

  return {
    labels: allData.map(item => item.date),
    datasets: [
      {
        label: 'Preços Históricos',
        data: allData.map(item => item.historical),
        borderColor: '#3b82f6',
        backgroundColor: '#3b82f6',
        tension: 0.1,
        pointRadius: 3,
        pointHoverRadius: 5,
        spanGaps: true
      },
      {
        label: 'Previsões',
        data: predictedData,
        borderColor: '#ef4444',
        backgroundColor: '#ef4444',
        borderDash: [5, 5],
        tension: 0.1,
        pointRadius: 3,
        pointHoverRadius: 5,
        spanGaps: true
      }
    ]
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
    },
    title: {
      display: true,
      text: 'Previsão de Preços do Ethereum'
    }
  },
  scales: {
    x: {
      title: {
        display: true,
        text: 'Data'
      }
    },
    y: {
      title: {
        display: true,
        text: 'Preço (USD)'
      }
    }
  }
}))

async function enviarPredicao() {
  successMessage.value = ''
  errorMessage.value = ''

  if (!isFormValid.value) {
    errorMessage.value = 'Preencha todos os campos com valores válidos.'
    return
  }

  isLoading.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        data_referencia: form.data_referencia,
        dias_previsao: Number(form.dias_previsao),
        dias_anteriores: Number(form.dias_anteriores),
      }),
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      const backendMessage =
        data?.message ||
        data?.error ||
        data?.detail ||
        `Erro ${response.status} ao processar a solicitacao.`
      throw new Error(backendMessage)
    }

    successMessage.value = data.message || 'Predição enviada com sucesso.'
    predictionResults.value = data.data || []
  } catch (error) {
    errorMessage.value = error.message || 'Erro inesperado ao enviar predição.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="container">
    <section class="card">
      <h1>Previsão de Ethereum</h1>
      <p>Informe os parâmetros para enviar a solicitação ao backend.</p>

      <form class="form" @submit.prevent="enviarPredicao">
        <label for="data_referencia">Data de referência</label>
        <input
          id="data_referencia"
          v-model="form.data_referencia"
          type="date"
          required
        />

        <label for="dias_previsao">Dias de previsão</label>
        <input
          id="dias_previsao"
          v-model.number="form.dias_previsao"
          type="number"
          min="1"
          required
        />

        <label for="dias_anteriores">Dias anteriores</label>
        <input
          id="dias_anteriores"
          v-model.number="form.dias_anteriores"
          type="number"
          min="1"
          required
        />

        <button type="submit" :disabled="isLoading">
          {{ isLoading ? 'Enviando...' : 'Enviar para previsao' }}
        </button>
      </form>

      <p v-if="successMessage" class="message success">{{ successMessage }}</p>
      <p v-if="errorMessage" class="message error">{{ errorMessage }}</p>

      <!-- Prediction Results -->
      <div v-if="predictionResults" class="results">
        <h2>Resultados da Previsao</h2>
        
        <div class="chart-container">
          <Line v-if="chartData" :data="chartData" :options="chartOptions"/>
        </div>

        <div class="tables">
          <div class="table-section">
            <h3>Dados Historicos</h3>
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Preço (USD)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in predictionResults.filter(item => item.historical_close !== null)" :key="item.date">
                  <td>{{ item.date }}</td>
                  <td>${{ item.historical_close.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="table-section">
            <h3>Previsoes</h3>
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Preço Previsto (USD)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in predictionResults.filter(item => item.predicted_close !== null)" :key="item.date">
                  <td>{{ item.date }}</td>
                  <td>${{ item.predicted_close.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <small class="api-info">API: {{ API_BASE_URL }}/predict</small>
    </section>
  </main>
</template>

<style scoped>
.container {
  min-height: 100vh;
  display: grid;
  place-items: center;
}

.card {
  width: min(100%, 640px);
  background-color: #1f2937;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

h1 {
  margin: 0;
  font-size: 1.6rem;
}

p {
  margin-top: 0.6rem;
  color: #d1d5db;
}

.form {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

label {
  font-weight: 600;
}

input {
  width: 100%;
  border: 1px solid #4b5563;
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
  background-color: #2c3b5a;
  color: #f9fafb;
}

button {
  margin-top: 0.8rem;
  border: 0;
  border-radius: 8px;
  padding: 0.7rem 1rem;
  background-color: #2563eb;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.message {
  margin-top: 1rem;
  font-weight: 600;
}

.success {
  color: #86efac;
}

.error {
  color: #fca5a5;
}

.api-info {
  display: block;
  margin-top: 0.8rem;
  color: #9ca3af;
}

.results {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #374151;
}

.results h2 {
  margin: 0 0 1rem 0;
  font-size: 1.4rem;
  color: #f9fafb;
}

.chart-container {
  height: 400px;
  margin-bottom: 2rem;
  background-color: #111827;
  border-radius: 8px;
  padding: 1rem;
}

.tables {
  display: grid;
  gap: 2rem;
  grid-template-columns: 1fr 1fr;
}

.table-section h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  color: #f9fafb;
}

table {
  width: 100%;
  border-collapse: collapse;
  background-color: #111827;
  border-radius: 8px;
  overflow: hidden;
}

th, td {
  padding: 0.5rem 0.8rem;
  text-align: left;
  border-bottom: 1px solid #374151;
}

th {
  background-color: #374151;
  font-weight: 600;
  color: #f9fafb;
}

td {
  color: #d1d5db;
}

tr:last-child td {
  border-bottom: none;
}

@media (max-width: 768px) {
  .tables {
    grid-template-columns: 1fr;
  }
  
  .card {
    width: min(100%, 480px);
  }
}
</style>
