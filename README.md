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
[Просмотр в Google Colab](https://colab.research.google.com/drive/1QX0kvqHC4C7CPu3zhO9tqtmTHVJo28BN?hl=ru#scrollTo=NVB5oW05q-76)


## Установка и запуск интерфейса
### Вариант 1: Клонирование репозитория (Git)
```bash
git clone https://github.com/ваш-логин/vkr-energy-forecast.git
cd vkr-energy-forecast
pip install -r requirements.txt
cd app
streamlit run app.py
```

Вариант 2: С помощью ZIP-архива
1. Скачайте проект
2. Распакуйте архив
3. Откройте корневую папку в терминале
4. Установите Python-библиотеки в терминале необходимо командой `pip install -r requirements.txt`
5. Перейдите в папку `app/`: `cd app`
6. Запуск интерфейса с помощью команды `streamlit run app.py`
7. Интерфейс доступен по адресу: `http://localhost:8501`
