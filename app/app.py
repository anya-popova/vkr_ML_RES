# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np

@st.cache_data
def load_data():
    df_predictions = pd.read_csv('predictions.csv', parse_dates=['forecast_date', 'target_time'])
    df_weather_price = pd.read_csv('weather_and_price.csv', parse_dates=['time'])
    return df_predictions, df_weather_price
# production_info: forecast_date, target_time, hour, true_solar, pred_solar, true_wind, pred_wind
# weather_price: массив с time, generation solar, generation wind onshore, price day ahead, temp,
    # clouds_all_*, humidity_*, pressure_*, rain_1h_*, wind_deg_*, wind_speed_*, hour, month

production_info, weather_price = load_data()
naive_df = pd.read_csv('naive_forecast.csv')

def check_weather_warnings(forecast_time, weather_price):
    """
    Проверка погодных условий и формирование предупреждений.
    Вызывается при смене даты.
    """
    weather_future_end = forecast_time + timedelta(hours=48)
    weather_120h = weather_price[
        (weather_price['time'] >= forecast_time - timedelta(hours=72)) & 
        (weather_price['time'] <= weather_future_end)
    ]
    
    warnings = []
    cities = ['Valencia', 'Madrid', 'Bilbao']
    temp_tomorrow = weather_120h[weather_120h['time'] > forecast_time]['temp'].values[:24]
    
    for city in cities:
        wind_tomorrow = weather_120h[weather_120h['time'] > forecast_time][f'wind_speed_{city}'].values[:24]
        humidity_tomorrow = weather_120h[weather_120h['time'] > forecast_time][f'humidity_{city}'].values[:24]
        rain_tomorrow = weather_120h[weather_120h['time'] > forecast_time][f'rain_1h_{city}'].values[:24]
        
        if wind_tomorrow.max() > 12:
            warnings.append(f"Сильный ветер {wind_tomorrow.max():.0f} м/с в {city}; рекомендуется внеплановый осмотр после снижения скорости ветра")
        
        if temp_tomorrow.min() < 273 and (humidity_tomorrow.max() > 70 or rain_tomorrow.sum() > 0):
            min_temp_c = temp_tomorrow.min() - 273.15
            warnings.append(f"Риск обледенения в {city} (t мин = {min_temp_c:.0f}°C); рекомендуется проверка энергоустановок")
        
        if rain_tomorrow.sum() > 2:
            warnings.append(f"Сильные осадки в {city}; рекомендуется очистка панелей")
        
        if wind_tomorrow.max() > 10 and humidity_tomorrow.min() < 40:
            warnings.append(f"Сильный ветер при низкой влажности в {city}; риск пылевых отложений на панелях")
    
    if temp_tomorrow.max() > 305:
        max_temp_c = temp_tomorrow.max() - 273.15
        warnings.append(f"Температура {max_temp_c:.0f}°C; снижение эффективности СЭС")
    
    return warnings


def optimize_application(future_24h, past_72h, acc_charge_current, acc_capacity=60000):
    """
    Оптимизация заявки на рынок на сутки вперёд
    
    Вход:
        future_24h: DataFrame (24 строки): прогноз на 24 часа вперёд
            столбцы: target_time, hour, pred_solar, pred_wind, true_solar, true_wind
        past_72h: DataFrame (72 строки): данные за прошлые 72 часа
            столбцы: target_time, hour, true_solar, pred_solar, true_wind, pred_wind

        acc_capacity: float ёмкость аккумулятора (по умолчанию 60000 МВт·ч)
        
    Выход:
        application_24h: массив (24, 2) оптимизированная заявка [solar, wind]
    """
    
    pred_solar = future_24h['pred_solar'].values.copy()
    pred_wind = future_24h['pred_wind'].values.copy()

    # сглаживание выработки СЭС
    solar_original = pred_solar.copy()
    

    for i in range(1, 23):
        if solar_original[i] < solar_original[i-1] and solar_original[i] < solar_original[i+1]:
            pred_solar[i] = (solar_original[i-1] + solar_original[i+1]) / 2

    for i in range(2, 22):
        left = solar_original[i-2:i]
        right = solar_original[i+1:i+3]
        neighbors = np.concatenate([left, right])
        neighbor_mean = np.mean(neighbors)
        
        # текущее значение  отличается от соседних
        if neighbor_mean > 0 and abs(solar_original[i] - neighbor_mean) / neighbor_mean > 0.8:
            pred_solar[i] = neighbor_mean
            
    # Завышение ветра
    for i in range(24):
        h = i + 1
        if h <= 4:
            pred_wind[i] *= 1.10
        elif h <= 8:
            pred_wind[i] *= 1.20
        else:
            pred_wind[i] *= 1.30
    
    # Сглаживание
    for i in range(1, 23):
        if max(pred_wind[i-1], 1) > 0 and abs(pred_wind[i] - pred_wind[i-1]) / max(pred_wind[i-1], 1) > 0.05:
            pred_wind[i] = (pred_wind[i-1] + pred_wind[i+1]) / 2


    application_24h = np.column_stack([pred_solar, pred_wind])
    return application_24h


def calculate_profit(real_24h, application_24h, prices_24h, 
                     acc_current, acc_capacity):
    """
    Расчёт прибыли за 24 часа с учётом аккумулятора.
    
    Вход:
        real_24h: массив (24, 2) реальная выработка [solar, wind]
        application_24h: массив (24, 2) заявка [solar, wind]
        prices_24h: list[24] цена на каждый час
        acc_current: float текущий заряд аккумулятора, МВт·ч
        acc_capacity: float ёмкость аккумулятора, МВт·ч
        
    Выход:
        profit: float прибыль за сутки
        acc_remaining: float остаток заряда аккумулятора
    """
    
    total_profit_day = 0
    charge_loss = 0.2
    
    for t in range(24):
        fact = real_24h[t, 0] + real_24h[t, 1]
        application = application_24h[t, 0] + application_24h[t, 1]
        price = prices_24h[t]
        
        income = price * min(fact, application)
        
        shortage = max(0, application - fact)
        covered = min(acc_current, shortage)
        acc_current -= covered
        penalty = 0.3 * price * (shortage - covered)
        
        surplus = max(0, fact - application)
        charge = surplus * (1 - charge_loss)
        acc_current = min(acc_capacity, acc_current + charge)
        
        profit = income - penalty
        total_profit_day += profit
    
    return total_profit_day, acc_current


st.set_page_config(page_title="Прогноз генерации ВИЭ", layout="wide")
st.title("Прогноз выработки СЭС и ВЭС на сутки вперёд")

# Календарь
dates = sorted(production_info['forecast_date'].dt.date.unique())
selected_date = st.sidebar.date_input("Выберите дату прогноза", 
                                       st.session_state.get('selected_date', dates[0]), 
                                       min_value=dates[0], max_value=dates[-1])
st.session_state.selected_date = selected_date

forecast_time = pd.Timestamp(selected_date).replace(hour=12)
forecast_data = production_info[production_info['forecast_date'] == forecast_time].sort_values('target_time')

# Погодные предупреждения при смене даты
st.session_state.weather_warnings = check_weather_warnings(forecast_time, weather_price)

# Сброс флага расчёта при смене даты
if 'last_selected_date' not in st.session_state:
    st.session_state.last_selected_date = selected_date
if st.session_state.last_selected_date != selected_date:
    st.session_state.application_calculated = False
    st.session_state.last_selected_date = selected_date
    st.session_state.use_recommended = False

# Инициализация общей прибыли
if 'total_profit' not in st.session_state:
    st.session_state.total_profit = 0
    st.session_state.days_passed = 0

# Сбор данных для графика
if len(forecast_data) == 0:
    st.warning(f"Нет данных на {selected_date}")
else:
    morning_start = forecast_time.replace(hour=1)
    morning_mask = (production_info['target_time'] >= morning_start) & (production_info['target_time'] <= forecast_time)
    morning_data = production_info[morning_mask][['target_time', 'true_solar', 'true_wind']].drop_duplicates('target_time')
    
    for _, row in morning_data.iterrows():
        if row['target_time'] not in forecast_data['target_time'].values:
            new_row = pd.DataFrame([{
                'forecast_date': forecast_time,
                'target_time': row['target_time'],
                'hour': row['target_time'].hour,
                'true_solar': row['true_solar'],
                'pred_solar': None,
                'true_wind': row['true_wind'],
                'pred_wind': None
            }])
            forecast_data = pd.concat([forecast_data, new_row], ignore_index=True)
    
    forecast_data = forecast_data.sort_values('target_time').reset_index(drop=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7))
    
    times = [t.strftime('%H:%M') for t in forecast_data['target_time']]
    x = range(len(forecast_data))
    has_fact = forecast_data['target_time'] <= forecast_time
    
    ax1.plot(x, forecast_data['pred_solar'], 'r--o', label='Прогноз', markersize=3)
    if has_fact.any():
        fact_x = [i for i in x if has_fact.iloc[i]]
        fact_y = forecast_data.loc[has_fact, 'true_solar']
        ax1.plot(fact_x, fact_y, 'b-o', label='Факт', markersize=4)
    ax1.set_xticks(range(0, len(x), 3))
    ax1.set_xticklabels([times[i] for i in range(0, len(x), 3)], rotation=45)
    ax1.set_ylabel('МВт')
    ax1.set_title(f'Солнечная генерация {selected_date}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(x, forecast_data['pred_wind'], 'orange', linestyle='--', marker='o', label='Прогноз', markersize=3)
    if has_fact.any():
        fact_y_w = forecast_data.loc[has_fact, 'true_wind']
        ax2.plot(fact_x, fact_y_w, 'g-o', label='Факт', markersize=4)
    ax2.set_xticks(range(0, len(x), 3))
    ax2.set_xticklabels([times[i] for i in range(0, len(x), 3)], rotation=45)
    ax2.set_xlabel('Время')
    ax2.set_ylabel('МВт')
    ax2.set_title(f'Ветровая генерация {selected_date}')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    if st.session_state.get('application_calculated', False):
        rec_x = list(x)[-24:]
        ax1.plot(rec_x, st.session_state.recommended_solar, 'darkgreen', linewidth=2.5, label='Рекомендация')
        ax2.plot(rec_x, st.session_state.recommended_wind, 'darkblue', linewidth=2.5, label='Рекомендация')
    
    plt.tight_layout()

    col1, col2, col3 = st.columns(3)
    col1.metric("Общая прибыль", f"{st.session_state.get('total_profit', 0):,.0f} EUR".replace(',', ' '))
    col2.metric("Прибыль за 24 ч с оптимизацией", f"{st.session_state.get('last_day_profit_rec', 0) or 0:,.0f} EUR".replace(',', ' '))
    col3.metric("Прибыль за 24 ч без оптимизации", f"{st.session_state.get('last_day_profit_model', 0) or 0:,.0f} EUR".replace(',', ' '))
    
    st.pyplot(fig)


# Боковая панель: настройки
acc_capacity = st.sidebar.number_input("Ёмкость аккумулятора, МВт·ч", value=60000)

manual_input = st.sidebar.checkbox(
    "Ввести заряд вручную", 
    value=st.session_state.get('manual_input', False)
)

if manual_input:
    acc_current = st.sidebar.number_input(
        "Текущий заряд аккумулятора, МВт·ч", 
        min_value=0, 
        max_value=acc_capacity,
        value=int(st.session_state.get('acc_current', 20000))
    )
    st.session_state.acc_current = acc_current
else:
    st.sidebar.metric("Заряд аккумулятора", 
                      f"{st.session_state.get('acc_current', 20000):.0f} МВт·ч")
    acc_current = st.session_state.get('acc_current', 20000)

# Кнопка "Рассчитать оптимальную заявку", используем только для графика
if st.sidebar.button("Рассчитать оптимальную заявку"):
    past_start = forecast_time - timedelta(hours=72)
    past_for_optimization = production_info[
        (production_info['target_time'] >= past_start) & 
        (production_info['target_time'] <= forecast_time)
    ]
    
    future_end = forecast_time + timedelta(hours=24)
    future_for_optimization = production_info[
        (production_info['target_time'] > forecast_time) & 
        (production_info['target_time'] <= future_end)
    ]
    
    weather_past_start = forecast_time - timedelta(hours=72)
    weather_future_end = forecast_time + timedelta(hours=48)
    weather_for_optimization = weather_price[
        (weather_price['time'] >= weather_past_start) & 
        (weather_price['time'] <= weather_future_end)
    ]

    recommended_application = optimize_application(
        future_24h=future_for_optimization,
        past_72h=past_for_optimization,
        acc_charge_current=acc_current,
        acc_capacity=acc_capacity
    )
    
    # для графиков
    st.session_state.recommended_application = recommended_application
    st.session_state.recommended_solar = recommended_application[:, 0]
    st.session_state.recommended_wind = recommended_application[:, 1]
    st.session_state.application_calculated = True

    # для проведения дня, чтобы не считать заново
    st.session_state.future_for_optimization = future_for_optimization
    st.session_state.prices_24h = weather_price[
        (weather_price['time'] > forecast_time) & 
        (weather_price['time'] <= forecast_time + timedelta(hours=24))
    ]['price day ahead'].values[:24]
    st.rerun()

# Чекбокс: использовать рекомендуемую заявку
use_recommended = st.sidebar.checkbox(
    "Использовать рекомендуемую заявку",
    value=st.session_state.get('use_recommended', False)
)

# Кнопка "Провести день"
if st.sidebar.button("Провести день"):
    if st.session_state.get('application_calculated', False):
        future_for_optimization = st.session_state.future_for_optimization
        prices_24h = st.session_state.prices_24h
        recommended_application = st.session_state.recommended_application
    else:
        past_start = forecast_time - timedelta(hours=72)
        past_for_optimization = production_info[
            (production_info['target_time'] >= past_start) & 
            (production_info['target_time'] <= forecast_time)
        ]
        
        future_end = forecast_time + timedelta(hours=24)
        future_for_optimization = production_info[
            (production_info['target_time'] > forecast_time) & 
            (production_info['target_time'] <= future_end)
        ]
        
        weather_past_start = forecast_time - timedelta(hours=72)
        weather_future_end = forecast_time + timedelta(hours=48)
        weather_for_optimization = weather_price[
            (weather_price['time'] >= weather_past_start) & 
            (weather_price['time'] <= weather_future_end)
        ]

        recommended_application = optimize_application(
            future_24h=future_for_optimization,
            past_72h=past_for_optimization,
            acc_charge_current=acc_current,
            acc_capacity=acc_capacity
        )
        
        weather_future_end = forecast_time + timedelta(hours=24)
        prices_24h = weather_price[
            (weather_price['time'] > forecast_time) & 
            (weather_price['time'] <= weather_future_end)
        ]['price day ahead'].values[:24]
    
    real_24h = future_for_optimization[['true_solar', 'true_wind']].values
    model_application = future_for_optimization[['pred_solar', 'pred_wind']].values
    
    profit_model, acc_model = calculate_profit(
        real_24h, model_application, prices_24h,
        acc_current, acc_capacity
    )
    
    profit_rec, acc_rec = calculate_profit(
        real_24h, recommended_application, prices_24h,
        acc_current, acc_capacity
    )
    
    if use_recommended:
        st.session_state.total_profit += profit_rec
        st.session_state.acc_current = acc_rec
    else:
        st.session_state.total_profit += profit_model
        st.session_state.acc_current = acc_model
    
    st.session_state.last_day_profit_rec = profit_rec
    st.session_state.last_day_profit_model = profit_model
    st.session_state.days_passed += 1
    st.session_state.manual_input = False
    
    next_date = selected_date + timedelta(days=1)
    if next_date in dates:
        st.session_state.selected_date = next_date
    st.rerun()


# Предупреждения
if st.session_state.get('weather_warnings'):
    st.sidebar.divider()
    st.sidebar.subheader("Погодные предупреждения")
    for w in st.session_state.weather_warnings:
        st.sidebar.warning(w)

# Сравнение результатов на всей тестовой выборке
if st.sidebar.button("Сравнение подходов на всей выборке"):
    total_profit_opt = 0
    total_profit_no_opt = 0
    total_profit_naive = 0

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_dates = sorted(production_info['forecast_date'].dt.date.unique())
    n_dates = len(all_dates)
    
    total_profit_opt = 0
    total_profit_no_opt = 0

    acc_opt = acc_current  # берём текущий заряд из интерфейса
    acc_no_opt = acc_current
    acc_naive = acc_current

    for i, test_date in enumerate(all_dates):
        status_text.text(f"Обработка {test_date}... ({i+1}/{n_dates})")
        progress_bar.progress((i+1) / n_dates)
        
        # Формируем данные как по кнопке "Рассчитать"
        fc_time = pd.Timestamp(test_date).replace(hour=12)
        
        past_start = fc_time - timedelta(hours=72)
        past_for_opt = production_info[
            (production_info['target_time'] >= past_start) & 
            (production_info['target_time'] <= fc_time)
        ]
        
        future_end = fc_time + timedelta(hours=24)
        future_for_opt = production_info[
            (production_info['target_time'] > fc_time) & 
            (production_info['target_time'] <= future_end)
        ]
        
        weather_past_start = fc_time - timedelta(hours=72)
        weather_future_end = fc_time + timedelta(hours=48)
        weather_for_opt = weather_price[
            (weather_price['time'] >= weather_past_start) & 
            (weather_price['time'] <= weather_future_end)
        ]
        
        prices_24h = weather_price[
            (weather_price['time'] > fc_time) & 
            (weather_price['time'] <= fc_time + timedelta(hours=24))
        ]['price day ahead'].values[:24]
        
        if len(prices_24h) < 24:
            continue
        
        real_24h = future_for_opt[['true_solar', 'true_wind']].values
        
        # Без оптимизации
        model_app = future_for_opt[['pred_solar', 'pred_wind']].values
        profit_no_opt, acc_no_opt = calculate_profit(
            real_24h, model_app, prices_24h,
            acc_no_opt, acc_capacity  # передаём текущий, получаем обновлённый
        )
        
        # С оптимизацией
        rec_app = optimize_application(
            future_24h=future_for_opt,
            past_72h=past_for_opt,
            acc_charge_current=acc_opt,  # передаём текущий
            acc_capacity=acc_capacity
        )
        profit_opt, acc_opt = calculate_profit(
            real_24h, rec_app, prices_24h,
            acc_opt, acc_capacity  # передаём текущий, получаем обновлённый
        )

        # Наивный прогноз
        naive_app = np.column_stack([naive_df['avg_solar'].values, naive_df['avg_wind'].values])
        profit_naive, acc_naive = calculate_profit(
            real_24h, naive_app, prices_24h,
            acc_naive, acc_capacity
        )
        total_profit_naive += profit_naive
        total_profit_opt += profit_opt
        total_profit_no_opt += profit_no_opt

    
    st.header("Сравнение методов на тестовой выборке")
    st.caption(f"Период: {all_dates[0].strftime('%d.%m.%Y')} — {all_dates[-1].strftime('%d.%m.%Y')} ({n_dates} дней)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Наивный прогноз", f"{total_profit_naive:,.0f} EUR")
    col2.metric("Прогноз XGBoost", f"{total_profit_no_opt:,.0f} EUR", 
                delta=f"{total_profit_no_opt - total_profit_naive:+,.0f}")
    col3.metric("С оптимизацией", f"{total_profit_opt:,.0f} EUR", 
                delta=f"{total_profit_opt - total_profit_no_opt:+,.0f}")
    
    # Подсчёт срабатывания предупреждений
    warning_counts = {
        "Сильный ветер": 0,
        "Обледенение": 0,
        "Сильные осадки": 0,
        "Жара": 0,
        "Пыльные отложения": 0
    }
    
    for test_date in all_dates:
        fc_time = pd.Timestamp(test_date).replace(hour=12)
        warnings = check_weather_warnings(fc_time, weather_price)
        for w in warnings:
            if "Сильный ветер" in w:
                warning_counts["Сильный ветер"] += 1
            elif "обледенения" in w:
                warning_counts["Обледенение"] += 1
            elif "осадки" in w:
                warning_counts["Сильные осадки"] += 1
            elif "Температура" in w:
                warning_counts["Жара"] += 1
            elif "пылевых" in w:
                warning_counts["Пыльные отложения"] += 1
    
    st.subheader("Статистика предупреждений")
    for key, value in warning_counts.items():
        st.caption(f"{key}: {value}")

st.divider()
st.caption(f"Проведено дней: {st.session_state.days_passed}")
st.caption(f"Заряд аккумулятора: {acc_current:.0f} МВт·ч")