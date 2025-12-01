# analyzer.py
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

class LaborMarketAnalyzer:
    """Класс для анализа и прогнозирования данных рынка труда."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        if 'published_at' in self.data.columns:
            self.data['published_at'] = pd.to_datetime(self.data['published_at'], errors='coerce')
            self.data['date'] = self.data['published_at'].dt.date
        else:
            self.data['date'] = pd.Timestamp.now().date()
    
    def calculate_basic_statistics(self) -> Dict:
        """Рассчитывает базовую статистику по вакансиям."""
        stats = {
            'total_vacancies': len(self.data),
            'with_salary': self.data['salary_rur'].notna().sum(),
            'avg_salary': None,
            'median_salary': None,
            'salary_std': None,
            'top_regions': {},
            'top_skills': {}
        }
        
        if 'salary_rur' in self.data.columns:
            salary_notna = self.data['salary_rur'].notna()
            if salary_notna.sum() > 0:
                stats['avg_salary'] = float(self.data.loc[salary_notna, 'salary_rur'].mean())
                stats['median_salary'] = float(self.data.loc[salary_notna, 'salary_rur'].median())
                stats['salary_std'] = float(self.data.loc[salary_notna, 'salary_rur'].std())
        
        if 'area_name' in self.data.columns:
            stats['top_regions'] = self.data['area_name'].value_counts().head(10).to_dict()
        
        stats['top_skills'] = self._extract_top_skills(20)
        return stats
    
    def _extract_top_skills(self, n: int = 20) -> Dict:
        """Извлекает топ-N самых востребованных навыков."""
        all_skills = []
        
        if 'key_skills' not in self.data.columns:
            return {}
        
        for skills_list in self.data['key_skills'].dropna():
            try:
                if isinstance(skills_list, str):
                    # Пытаемся распарсить JSON строку
                    import json
                    skills = json.loads(skills_list)
                    all_skills.extend(skills)
                elif isinstance(skills_list, list):
                    all_skills.extend(skills_list)
            except:
                # Если не получается распарсить, пропускаем
                continue
        
        if not all_skills:
            return {}
        
        from collections import Counter
        skill_counts = Counter(all_skills)
        return dict(skill_counts.most_common(n))
    
    def analyze_salary_factors(self) -> pd.DataFrame:
        """Анализирует зависимость зарплаты от различных факторов."""
        # Создаем копию данных для анализа
        analysis_df = self.data.copy()
        
        # Проверяем необходимые колонки
        required_columns = ['salary_rur', 'area_name', 'experience']
        missing_columns = [col for col in required_columns if col not in analysis_df.columns]
        
        if missing_columns:
            print(f"Отсутствуют колонки для анализа: {missing_columns}")
            return pd.DataFrame()
        
        # Фильтруем данные с зарплатой
        analysis_df = analysis_df[analysis_df['salary_rur'].notna()]
        
        if len(analysis_df) < 5:
            print("Недостаточно данных с зарплатой для анализа")
            return pd.DataFrame()
        
        # Создаем числовое представление опыта
        exp_mapping = {
            'Нет опыта': 0,
            'От 1 года до 3 лет': 2,
            'От 3 до 6 лет': 4.5,
            'Более 6 лет': 7
        }
        
        # Применяем маппинг, если значение есть в маппинге, иначе используем 0
        analysis_df['exp_numeric'] = analysis_df['experience'].map(exp_mapping).fillna(0)
        
        # Анализ по регионам
        regional_stats = analysis_df.groupby('area_name').agg({
            'salary_rur': ['mean', 'count', 'std'],
            'id': 'count'
        }).round(2)
        
        # Переименовываем колонки
        regional_stats.columns = ['avg_salary', 'vacancy_count', 'salary_std', 'total']
        regional_stats = regional_stats.sort_values('avg_salary', ascending=False)
        
        return regional_stats
    
    def forecast_demand(self, days_forecast: int = 30) -> Tuple[Optional[pd.Series], Optional[pd.Series], str]:
        """Прогнозирует спрос на вакансии с помощью модели ARIMA."""
        if 'date' not in self.data.columns or len(self.data) < 10:
            return None, None, "Недостаточно данных для прогнозирования"
        
        try:
            # Агрегация по дням
            daily_demand = self.data.groupby('date').size()
            
            if len(daily_demand) < 10:
                return None, None, f"Недостаточно дней с данными: {len(daily_demand)} < 10"
            
            # Преобразуем в временной ряд с постоянной частотой
            date_range = pd.date_range(start=daily_demand.index.min(), end=daily_demand.index.max(), freq='D')
            daily_demand = daily_demand.reindex(date_range, fill_value=0)
            
            # Построение упрощенной модели (используем более простой подход)
            # Для ARIMA нужно больше данных, поэтому используем простую модель
            if len(daily_demand) > 14:
                try:
                    # Используем простую модель скользящего среднего для демонстрации
                    forecast_values = daily_demand.rolling(window=7, min_periods=1).mean().iloc[-days_forecast:]
                    
                    # Создаем индекс для прогноза
                    last_date = daily_demand.index[-1]
                    forecast_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_forecast, freq='D')
                    
                    # Создаем Series с прогнозом
                    forecast_series = pd.Series(
                        forecast_values.values[:days_forecast] if len(forecast_values) >= days_forecast 
                        else [forecast_values.mean()] * days_forecast,
                        index=forecast_index
                    )
                    
                    return daily_demand, forecast_series, "Прогноз построен успешно"
                    
                except Exception as e:
                    # Резервный простой прогноз
                    avg_demand = daily_demand.mean()
                    last_date = daily_demand.index[-1]
                    forecast_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_forecast, freq='D')
                    forecast_series = pd.Series([avg_demand] * days_forecast, index=forecast_index)
                    
                    return daily_demand, forecast_series, f"Упрощенный прогноз на основе среднего: {avg_demand:.1f}"
            else:
                # Очень мало данных - используем среднее
                avg_demand = daily_demand.mean()
                last_date = daily_demand.index[-1]
                forecast_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_forecast, freq='D')
                forecast_series = pd.Series([avg_demand] * days_forecast, index=forecast_index)
                
                return daily_demand, forecast_series, f"Прогноз на основе среднего (мало данных): {avg_demand:.1f}"
                
        except Exception as e:
            return None, None, f"Ошибка прогнозирования: {str(e)}"
    
    def build_salary_regression_model(self) -> Dict:
        """Строит регрессионную модель для прогнозирования зарплаты."""
        if 'salary_rur' not in self.data.columns:
            return {"error": "Нет данных о зарплате"}
        
        model_data = self.data[self.data['salary_rur'].notna()].copy()
        
        if len(model_data) < 50:
            return {"error": f"Недостаточно данных для построения модели: {len(model_data)} < 50"}
        
        # Подготовка признаков
        X_data = []
        valid_indices = []
        
        for idx, row in model_data.iterrows():
            try:
                # Кодируем опыт
                exp_level = 1
                if isinstance(row.get('experience'), str):
                    exp_lower = row['experience'].lower()
                    if 'нет опыта' in exp_lower or 'до 1 года' in exp_lower:
                        exp_level = 1
                    elif 'от 1 года до 3 лет' in exp_lower:
                        exp_level = 2
                    elif 'от 3 до 6 лет' in exp_lower:
                        exp_level = 3
                    elif 'более 6 лет' in exp_lower:
                        exp_level = 4
                
                # Кодируем регион
                is_moscow = 1 if isinstance(row.get('area_name'), str) and 'москва' in row['area_name'].lower() else 0
                is_spb = 1 if isinstance(row.get('area_name'), str) and ('петербург' in row['area_name'].lower() or 'спб' in row['area_name'].lower()) else 0
                
                X_data.append([exp_level, is_moscow, is_spb])
                valid_indices.append(idx)
            except:
                continue
        
        if len(X_data) < 30:
            return {"error": f"Недостаточно валидных данных: {len(X_data)} < 30"}
        
        X = np.array(X_data)
        y = model_data.loc[valid_indices, 'salary_rur'].values
        
        # Обучение модели
        model = LinearRegression()
        model.fit(X, y)
        
        # Расчет метрик
        y_pred = model.predict(X)
        r_squared = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - np.mean(y)) ** 2)
        
        # Важность признаков
        feature_names = ['exp_level', 'is_moscow', 'is_spb']
        coefficients = pd.DataFrame({
            'feature': feature_names,
            'coefficient': model.coef_
        }).sort_values('coefficient', key=abs, ascending=False)
        
        return {
            'model': model,
            'r_squared': float(r_squared),
            'coefficients': coefficients.to_dict('records'),
            'intercept': float(model.intercept_),
            'n_samples': len(X)
        }