# visualizer.py
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

class LaborMarketVisualizer:
    """Класс для визуализации данных рынка труда."""
    
    @staticmethod
    def create_interactive_dashboard(analyzer, stats):
        """Создает интерактивную дашборд-визуализацию."""
        data = analyzer.data
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Динамика публикации вакансий', 'Распределение зарплат',
                          'Топ-10 регионов', 'Топ-15 навыков'),
            specs=[[{'type': 'scatter'}, {'type': 'histogram'}],
                   [{'type': 'bar'}, {'type': 'bar'}]]
        )
        
        # 1. Динамика вакансий (если есть даты)
        if 'date' in data.columns and len(data['date'].unique()) > 1:
            try:
                daily_trend = data.groupby('date').size().reset_index(name='count')
                daily_trend['date'] = pd.to_datetime(daily_trend['date'])
                daily_trend = daily_trend.sort_values('date')
                
                fig.add_trace(
                    go.Scatter(
                        x=daily_trend['date'], 
                        y=daily_trend['count'], 
                        mode='lines+markers', 
                        name='Вакансий в день',
                        line=dict(color='blue', width=2)
                    ),
                    row=1, col=1
                )
            except Exception as e:
                print(f"Ошибка построения графика динамики: {e}")
        
        # 2. Распределение зарплат
        if 'salary_rur' in data.columns:
            salary_data = data['salary_rur'].dropna()
            if len(salary_data) > 0:
                fig.add_trace(
                    go.Histogram(
                        x=salary_data, 
                        nbinsx=30, 
                        name='Распределение зарплат',
                        marker=dict(color='green')
                    ),
                    row=1, col=2
                )
        
        # 3. Топ регионов
        if stats.get('top_regions'):
            top_regions = pd.DataFrame(
                list(stats['top_regions'].items()), 
                columns=['Регион', 'Вакансий']
            )
            fig.add_trace(
                go.Bar(
                    x=top_regions['Регион'], 
                    y=top_regions['Вакансий'], 
                    name='Вакансии по регионам',
                    marker=dict(color='lightblue')
                ),
                row=2, col=1
            )
        
        # 4. Топ навыков
        if stats.get('top_skills'):
            top_skills = pd.DataFrame(
                list(stats['top_skills'].items())[:15], 
                columns=['Навык', 'Упоминаний']
            )
            fig.add_trace(
                go.Bar(
                    x=top_skills['Навык'], 
                    y=top_skills['Упоминаний'], 
                    name='Навыки',
                    marker=dict(color='orange')
                ),
                row=2, col=2
            )
        
        fig.update_layout(
            height=800, 
            title_text="Анализ рынка труда на основе данных HH.ru", 
            showlegend=False,
            template="plotly_white"
        )
        return fig
    
    @staticmethod
    def create_salary_analysis(data):
        """Создает визуализацию анализа зарплат."""
        if 'salary_rur' not in data.columns or 'area_name' not in data.columns:
            return None
        
        data_with_salary = data[data['salary_rur'].notna()].copy()
        
        if len(data_with_salary) == 0:
            return None
        
        # Средние зарплаты по регионам
        salary_by_region = data_with_salary.groupby('area_name')['salary_rur'].agg([
            'mean', 'count', 'std', 'min', 'max'
        ]).round(0).reset_index()
        
        # Сортируем и берем топ-10
        salary_by_region = salary_by_region.sort_values('mean', ascending=False).head(10)
        
        fig = go.Figure(data=[
            go.Bar(
                name='Средняя зарплата',
                x=salary_by_region['area_name'],
                y=salary_by_region['mean'],
                text=salary_by_region['mean'].apply(lambda x: f"{x:,.0f} ₽"),
                textposition='auto',
                marker_color='indianred'
            )
        ])
        
        fig.update_layout(
            title='Топ-10 регионов по средней зарплате',
            xaxis_title="Регион",
            yaxis_title="Средняя зарплата, ₽",
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_skills_cloud(stats):
        """Создает облако навыков (альтернатива bar chart)."""
        if not stats.get('top_skills'):
            return None
        
        skills_df = pd.DataFrame(
            list(stats['top_skills'].items())[:20], 
            columns=['Навык', 'Частота']
        )
        
        # Размер текста пропорционален частоте
        max_freq = skills_df['Частота'].max()
        skills_df['Размер'] = 10 + (skills_df['Частота'] / max_freq * 40)
        
        fig = go.Figure(data=[
            go.Scatter(
                x=np.random.randn(len(skills_df)),  # случайные координаты
                y=np.random.randn(len(skills_df)),
                mode='text',
                text=skills_df['Навык'],
                textfont=dict(
                    size=skills_df['Размер'],
                    color=['blue', 'green', 'red', 'orange', 'purple'] * 4
                )
            )
        ])
        
        fig.update_layout(
            title='Облако навыков (размер = частота упоминания)',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_forecast_plot(historical, forecast, title="Прогноз спроса на вакансии"):
        """Визуализирует прогноз временного ряда."""
        fig = go.Figure()
        
        if historical is not None and len(historical) > 0:
            fig.add_trace(go.Scatter(
                x=historical.index,
                y=historical.values,
                mode='lines+markers',
                name='Исторические данные',
                line=dict(color='blue', width=2)
            ))
        
        if forecast is not None and len(forecast) > 0:
            fig.add_trace(go.Scatter(
                x=forecast.index,
                y=forecast.values,
                mode='lines+markers',
                name='Прогноз',
                line=dict(color='red', width=2, dash='dash')
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Дата",
            yaxis_title="Количество вакансий",
            hovermode='x unified',
            template="plotly_white"
        )
        
        return fig