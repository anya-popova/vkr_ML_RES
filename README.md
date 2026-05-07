# Выпускная квалификационная работа бакалавра
Прогнозирование выработки СЭС и ВЭС с оптимизацией заявки на рынок на сутки вперёд

```vkr-energy-forecast/
│
├── README.md
├── requirements.txt
│
├── data/                              # Исходные данные с Kaggle
│   ├── energy_dataset.csv
│   └── weather_features.csv
│
├── notebooks/                         # Jupyter
│   └── vkr_actual_24mod.ipynb
│
└── app/                               # Интерфейс и файлы, полученные с vkr_actual_24mod.ipynb
    ├── app.py
    ├── predictions.csv
    ├── weather_and_price.csv
    └── naive_forecast.csv
```

## Запуск интерфейса

### Интерфейс (веб-приложение)

```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```
Открыть в браузере: http://localhost:8501

