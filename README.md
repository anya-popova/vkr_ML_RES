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

1. Скачайте проект
2. Распакуйте архив
3. Откройте папку `app/`
4. Установите Python-библиотеки:
   - В терминале необходимо выполнить `pip install -r requirements.txt`
5. Запуск интерфейса с помощью команды в терминале `streamlit run app.py`
6. Интерфейс доступен по адресу: `http://localhost:8501`
