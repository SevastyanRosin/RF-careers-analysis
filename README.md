# Ситуационное моделирование развития кадрового потенциала в Российской Федерации

## Установка
### 1. Клонируй/скачай репозиторий 
git clone

### 2. Установи зависимости
pip install -r requirements/requirements.txt

### 3. Запусти систему
python run.py

## Основные команды
### Полный анализ (30 дней, все регионы)
python src/run_analysis.py --full

### Быстрый тест (7 дней, 2 региона)
python src/run_analysis.py --fast

### Анализ конкретной профессии
python src/run_analysis.py --query "Python разработчик"

### Только сбор данных
python -c "from src.hh_api_client import HHAPIClient; client = HHAPIClient(); data = client.collect_vacancies()"

### Экспорт в Excel
python src/run_analysis.py --export excel

## Файлы результатов
После запуска в папке results/ создаются:

### vacancies_дата.csv - сырые данные

### analysis_report.json - статистика в JSON

### salary_analysis.html - интерактивные графики

### market_dashboard.html - полный дашборд
