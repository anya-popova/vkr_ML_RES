# Выпускная квалификационная работа бакалавра
## Прогнозирование выработки СЭС и ВЭС с оптимизацией заявки на рынок на сутки вперёд

## Структура репозитория

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
## Данные

Использован открытый набор данных с Kaggle: [Hourly energy demand generation and weather](https://www.kaggle.com/datasets/nicholasjhana/energy-consumption-generation-prices-and-weather/data) (2015–2019, Испания).

## Jupyter-ноутбук

Полный код обработки данных и обучения моделей находится в `notebooks/vkr_actual_24mod.ipynb`. 
[Просмотр в Google Colab]([https://colab.research.google.com/](https://colab.research.google.com/drive/1QX0kvqHC4C7CPu3zhO9tqtmTHVJo28BN?hl=ru#scrollTo=NVB5oW05q-76)])

## Запуск интерфейса

1. Скачайте проект
2. Распакуйте архив
3. Откройте папку `app/`
4. Установите Python-библиотеки:
   - В терминале необходимо выполнить `pip install -r requirements.txt`
5. Запуск интерфейса с помощью команды в терминале `streamlit run app.py`
6. Интерфейс доступен по адресу: `http://localhost:8501`
