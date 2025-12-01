# run_diploma_full.py
import sys
import os
import yaml

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("АНАЛИЗ")
    print("=" * 60)
    
    # 1. Создаем полный конфиг
    full_config = {
        'project_name': 'Дипломный проект: Анализ кадрового потенциала РФ',
        'author': 'Юлия Иллюк',
        'email': 'julsillyuk@gmail.com',
        
        'search_queries': [
            {
                'name': 'IT-специалисты',
                'keywords': [
                    'разработчик', 'программист', 'аналитик', 
                    'Data Scientist', 'ML engineer', 'Python',
                    'Java', 'JavaScript', 'C++', 'DevOps',
                    'системный администратор', 'тестировщик'
                ]
            },
            {
                'name': 'Аналитики',
                'keywords': [
                    'аналитик данных', 'бизнес-аналитик',
                    'системный аналитик', 'financial analyst'
                ]
            }
        ],
        
        'regions': [
            {'id': 1, 'name': 'Москва'},
            {'id': 2, 'name': 'Санкт-Петербург'},
            {'id': 76, 'name': 'Новосибирск'},
            {'id': 66, 'name': 'Екатеринбург'},
            {'id': 88, 'name': 'Краснодар'},
            {'id': 54, 'name': 'Казань'},
            {'id': 104, 'name': 'Нижний Новгород'},
            {'id': 99, 'name': 'Воронеж'}
        ],
        
        'period': {
            'days_to_collect': 30,
            'max_vacancies_per_query': 500
        },
        
        'api': {
            'base_url': 'https://api.hh.ru/',
            'user_agent': 'DiplomaResearch/1.0 (julsillyuk@gmail.com)',
            'timeout': 30,
            'delays': {
                'between_requests': 0.5,
                'after_403': 2.0
            },
            'only_with_salary': True
        },
        
        'oauth': {
            'client_id': 'QD4OKONPO2O76BGA9PDU2L88T4L7QPVJN8KS97P7E76HO9D4D0LDPLJO8KUOHM3G',
            'client_secret': 'QVN13AEOPACUJCP1GM4CO9S0DTK352NAVT0G7DEPANPBN947JEKC8AUPIDNFR073',
            'redirect_uri': 'https://diplom/',
            'token_url': 'https://hh.ru/oauth/token'
        },
        
        'analysis': {
            'min_vacancies_for_analysis': 100,
            'forecast_days': 30,
            'salary_outlier_threshold': 3.0
        }
    }
    
    # Сохраняем конфиг
    with open('config_full.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(full_config, f, default_flow_style=False, allow_unicode=True)
    
    print("✅ Создан полный конфиг: config_full.yaml")
    
    # 2. Запускаем систему
    print("\n🚀 Запуск системы сбора и анализа данных...")
    
    try:
        from hh_api_client import HHAPIClient
        from data_processor import DataProcessor
        from analyzer import LaborMarketAnalyzer
        import pandas as pd
        import json
        import numpy as np
        
        # Инициализация
        client = HHAPIClient(config_path='config_full.yaml')
        
        print(f"\n📊 Сбор данных за последние {client.config['period']['days_to_collect']} дней...")
        print("Это может занять несколько минут...")
        
        # Сбор данных
        raw_vacancies = []
        
        # Собираем по регионам и запросам
        for region in client.config['regions'][:3]:  # Ограничим 3 региона для скорости
            for query_group in client.config['search_queries']:
                for keyword in query_group['keywords'][:2]:  # Ограничим 2 ключевых слова
                    print(f"🔍 Поиск: '{keyword}' в регионе {region['name']}")
                    
                    vacancies, count = client.search_vacancies(
                        text=keyword,
                        area=region['id'],
                        per_page=50
                    )
                    
                    print(f"   Найдено: {count} вакансий")
                    
                    # Получаем детали для первых 10 вакансий
                    for i, vac in enumerate(vacancies[:10]):
                        details = client.get_vacancy_details(vac.get('id'))
                        if details:
                            raw_vacancies.append(details)
                        
                        if (i + 1) % 5 == 0:
                            print(f"   Обработано {i+1} вакансий")
        
        print(f"\n✅ Собрано {len(raw_vacancies)} вакансий с деталями")
        
        if len(raw_vacancies) < 50:
            print("⚠ Внимание: собрано мало данных. Рекомендуется увеличить период сбора.")
        
        # Обработка данных
        processor = DataProcessor()
        processed_data = processor.process_vacancies(raw_vacancies)
        
        df = pd.DataFrame(processed_data)
        df.to_csv('diploma_vacancies.csv', index=False, encoding='utf-8-sig')
        print("✅ Данные сохранены в diploma_vacancies.csv")
        
        # Анализ
        analyzer = LaborMarketAnalyzer(df)
        stats = analyzer.calculate_basic_statistics()
        
        print("\n" + "=" * 60)
        print("📈 РЕЗУЛЬТАТЫ АНАЛИЗА")
        print("=" * 60)
        
        print(f"\n📊 Общая статистика:")
        print(f"   Всего вакансий: {stats['total_vacancies']}")
        print(f"   С указанной зарплатой: {stats['with_salary']} ({stats['with_salary']/stats['total_vacancies']*100:.1f}%)")
        
        if stats['avg_salary']:
            print(f"   Средняя зарплата: {stats['avg_salary']:,.0f} ₽")
            print(f"   Медианная зарплата: {stats['median_salary']:,.0f} ₽")
        
        print(f"\n📍 Распределение по регионам:")
        for region, count in list(stats['top_regions'].items())[:5]:
            print(f"   {region}: {count} вакансий")
        
        print(f"\n💡 Топ-10 востребованных навыков:")
        for skill, count in list(stats['top_skills'].items())[:10]:
            print(f"   {skill}: {count}")
        
        # Дополнительный анализ
        print(f"\n📊 ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ:")
        
        # Анализ зарплат по регионам
        salary_stats = analyzer.analyze_salary_factors()
        if not salary_stats.empty:
            print(f"\n💰 Средние зарплаты по регионам:")
            for idx, row in salary_stats.head(5).iterrows():
                print(f"   {idx}: {row['avg_salary']:,.0f} ₽ (вакансий: {row['vacancy_count']})")
        
        # Прогнозирование
        print(f"\n🔮 ПРОГНОЗИРОВАНИЕ СПРОСА:")
        historical, forecast, message = analyzer.forecast_demand(days_forecast=7)
        print(f"   {message}")
        if forecast is not None:
            print(f"   Средний прогноз на 7 дней: {forecast.mean():.1f} вакансий в день")
        
        # Регрессионный анализ
        print(f"\n🧮 РЕГРЕССИОННЫЙ АНАЛИЗ:")
        regression_results = analyzer.build_salary_regression_model()
        
        if 'error' not in regression_results:
            print(f"   Коэффициент детерминации R²: {regression_results['r_squared']:.3f}")
            if 'n_samples' in regression_results:
                print(f"   Образцов для обучения: {regression_results['n_samples']}")
        else:
            print(f"   {regression_results['error']}")
        
        # Сохранение отчета
        print(f"\n💾 СОХРАНЕНИЕ ОТЧЕТА...")
        
        # Подготовка данных для JSON
        report_data = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'project': client.config.get('project_name', 'Дипломный проект'),
            'period_days': client.config['period']['days_to_collect'],
            'vacancies_total': int(stats['total_vacancies']),
            'vacancies_with_salary': int(stats['with_salary']),
            'salary_statistics': {
                'average': float(stats['avg_salary']) if stats['avg_salary'] else None,
                'median': float(stats['median_salary']) if stats['median_salary'] else None,
                'std': float(stats['salary_std']) if stats['salary_std'] else None
            },
            'top_regions': {str(k): int(v) for k, v in stats['top_regions'].items()},
            'top_skills': {str(k): int(v) for k, v in stats['top_skills'].items()},
            'forecast_info': {
                'message': message,
                'avg_forecast': float(forecast.mean()) if forecast is not None else None
            }
        }
        
        if 'error' not in regression_results and 'r_squared' in regression_results:
            report_data['regression_model'] = {
                'r_squared': float(regression_results['r_squared']),
            }
            
            if 'coefficients' in regression_results and isinstance(regression_results['coefficients'], list):
                report_data['regression_model']['coefficients'] = [
                    {'feature': str(coef.get('feature', '')), 'value': float(coef.get('coefficient', 0))}
                    for coef in regression_results['coefficients']
                    if isinstance(coef, dict)
                ]
        
        # Сохранение с кастомным энкодером
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, 
                                   np.int32, np.int64, np.uint8, np.uint16, 
                                   np.uint32, np.uint64)):
                    return int(obj)
                elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return json.JSONEncoder.default(self, obj)
        
        with open('diploma_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
        
        print("✅ Отчет сохранен в diploma_report.json")
        
        try:
            import plotly.graph_objects as go
            print(f"\n🎨 ГЕНЕРАЦИЯ ПРОСТЫХ ГРАФИКОВ...")
            
            # Простая визуализация зарплат
            if 'salary_rur' in df.columns and df['salary_rur'].notna().sum() > 0:
                fig = go.Figure(data=[go.Histogram(x=df['salary_rur'].dropna(), nbinsx=30)])
                fig.update_layout(
                    title='Распределение зарплат',
                    xaxis_title='Зарплата, ₽',
                    yaxis_title='Количество вакансий'
                )
                fig.write_html("salary_distribution.html")
                print("✅ График распределения зарплат: salary_distribution.html")
            
            # Визуализация топ регионов
            if 'area_name' in df.columns:
                region_counts = df['area_name'].value_counts().head(10)
                fig = go.Figure(data=[go.Bar(
                    x=region_counts.index,
                    y=region_counts.values,
                    text=region_counts.values,
                    textposition='auto',
                )])
                fig.update_layout(
                    title='Топ-10 регионов по количеству вакансий',
                    xaxis_title='Регион',
                    yaxis_title='Количество вакансий'
                )
                fig.write_html("top_regions.html")
                print("✅ График топ регионов: top_regions.html")
            
        except ImportError:
            print("⚠ Plotly не установлен. Для графиков установите: pip install plotly")
        
        print("\n📁 Результаты сохранены в файлах:")
        print("   • diploma_vacancies.csv - исходные данные")
        print("   • diploma_report.json - полный отчет")
        print("   • salary_distribution.html - распределение зарплат")
        print("   • top_regions.html - топ регионов")
        
    except ImportError as e:
        print(f"\n❌ Ошибка импорта: {e}")
        print("Установите недостающие зависимости:")
        print("pip install pandas numpy requests pyyaml")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()