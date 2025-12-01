# data_processor.py
import pandas as pd
import numpy as np
import json
from typing import List, Dict, Any
import re

class DataProcessor:
    """Класс для обработки и очистки данных о вакансиях."""
    
    def __init__(self):
        pass
    
    def process_vacancies(self, vacancies_data: List[Dict]) -> List[Dict]:
        """
        Обрабатывает сырые данные вакансий.
        Включает очистку, нормализацию и извлечение дополнительных признаков.
        """
        processed = []
        
        for vacancy in vacancies_data:
            processed_vacancy = self._process_single_vacancy(vacancy)
            if processed_vacancy:
                processed.append(processed_vacancy)
        
        return processed
    
    def _process_single_vacancy(self, vacancy: Dict) -> Dict:
        """Обрабатывает одну вакансию."""
        try:
            # Базовые поля
            result = {
                'id': vacancy.get('id', ''),
                'name': vacancy.get('name', ''),
                'area_id': vacancy.get('area_id', ''),
                'area_name': vacancy.get('area_name', ''),
                'published_at': vacancy.get('published_at', ''),
                'employer_name': vacancy.get('employer_name', ''),
                'salary_rur': vacancy.get('salary_rur'),
                'experience': vacancy.get('experience', ''),
                'employment': vacancy.get('employment', ''),
                'schedule': vacancy.get('schedule', ''),
                'description': vacancy.get('description', ''),
                'alternate_url': vacancy.get('alternate_url', '')
            }
            
            # Обработка ключевых навыков
            key_skills = vacancy.get('key_skills', [])
            if isinstance(key_skills, str):
                try:
                    key_skills = json.loads(key_skills.replace("'", '"'))
                except:
                    key_skills = []
            result['key_skills'] = json.dumps(key_skills, ensure_ascii=False) if key_skills else '[]'
            
            # Обработка профессиональных ролей
            prof_roles = vacancy.get('professional_roles', [])
            result['professional_roles'] = json.dumps(prof_roles, ensure_ascii=False) if prof_roles else '[]'
            
            # Извлечение дополнительных признаков из описания
            description = vacancy.get('description', '')
            result['description_length'] = len(description) if description else 0
            
            # Извлечение требований к образованию
            result['requires_higher_education'] = self._check_education_requirement(description)
            
            # Определение уровня позиции по названию
            result['position_level'] = self._determine_position_level(
                vacancy.get('name', ''), 
                vacancy.get('experience', '')
            )
            
            return result
            
        except Exception as e:
            print(f"Ошибка обработки вакансии {vacancy.get('id')}: {e}")
            return None
    
    def _check_education_requirement(self, description: str) -> int:
        """Проверяет требование высшего образования в описании."""
        if not description:
            return 0
        
        description_lower = description.lower()
        education_keywords = [
            'высшее образование', 'вуз', 'диплом', 'вышка',
            'higher education', 'university degree'
        ]
        
        for keyword in education_keywords:
            if keyword in description_lower:
                return 1
        
        return 0
    
    def _determine_position_level(self, position_name: str, experience: str) -> str:
        """Определяет уровень позиции (junior, middle, senior)."""
        position_lower = position_name.lower()
        
        # Определение по названию
        if any(word in position_lower for word in ['junior', 'младш', 'начинающ', 'стажер']):
            return 'junior'
        elif any(word in position_lower for word in ['senior', 'ведущ', 'старш', 'руковод']):
            return 'senior'
        elif any(word in position_lower for word in ['middle', 'средн']):
            return 'middle'
        
        # Определение по опыту
        if experience:
            if 'нет опыта' in experience.lower() or 'до 1 года' in experience.lower():
                return 'junior'
            elif 'более 6 лет' in experience.lower() or 'от 3 до 6 лет' in experience.lower():
                return 'senior'
            elif 'от 1 года до 3 лет' in experience.lower():
                return 'middle'
        
        return 'unknown'
    
    def create_summary_statistics(self, processed_data: List[Dict]) -> Dict:
        """Создает сводную статистику по обработанным данным."""
        df = pd.DataFrame(processed_data)
        
        stats = {
            'total_processed': len(df),
            'with_salary': df['salary_rur'].notna().sum(),
            'unique_regions': df['area_name'].nunique(),
            'unique_employers': df['employer_name'].nunique(),
            'avg_description_length': df['description_length'].mean() if 'description_length' in df.columns else 0
        }
        
        # Статистика по уровням позиций
        if 'position_level' in df.columns:
            level_stats = df['position_level'].value_counts().to_dict()
            stats['position_levels'] = level_stats
        
        # Статистика по типам занятости
        if 'employment' in df.columns:
            employment_stats = df['employment'].value_counts().to_dict()
            stats['employment_types'] = employment_stats
        
        return stats
    
    def save_to_csv(self, processed_data: List[Dict], filename: str = 'processed_vacancies.csv'):
        """Сохраняет обработанные данные в CSV файл."""
        df = pd.DataFrame(processed_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Данные сохранены в {filename}")
    
    def load_from_csv(self, filename: str = 'processed_vacancies.csv') -> pd.DataFrame:
        """Загружает обработанные данные из CSV файла."""
        try:
            df = pd.read_csv(filename, encoding='utf-8-sig')
            
            # Восстанавливаем JSON поля
            for column in ['key_skills', 'professional_roles']:
                if column in df.columns:
                    df[column] = df[column].apply(
                        lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else []
                    )
            
            return df
        except FileNotFoundError:
            print(f"Файл {filename} не найден")
            return pd.DataFrame()
        
def process_vacancies_improved(self, vacancies_data: List[Dict]) -> List[Dict]:
    """
    Улучшенная обработка данных с учетом новой структуры HH API.
    """
    processed = []
    
    for vacancy in vacancies_data:
        processed_vacancy = self._process_hh_vacancy(vacancy)
        if processed_vacancy:
            processed.append(processed_vacancy)
    
    return processed

def _process_hh_vacancy(self, vacancy: Dict) -> Dict:
    """Обрабатывает вакансию в формате HH API."""
    try:
        # Извлечение основных полей
        result = {
            'id': vacancy.get('id', ''),
            'name': vacancy.get('name', '').strip(),
            'area_id': vacancy.get('area_id'),
            'area_name': vacancy.get('area_name', 'Не указан'),
            'published_at': vacancy.get('published_at', ''),
            'employer_name': vacancy.get('employer_name', ''),
            'description': vacancy.get('description', ''),
            'alternate_url': vacancy.get('alternate_url', '')
        }
        
        # Обработка зарплаты
        salary_info = vacancy.get('salary', {})
        if salary_info:
            result['salary_from'] = salary_info.get('from')
            result['salary_to'] = salary_info.get('to')
            result['salary_currency'] = salary_info.get('currency')
            result['salary_gross'] = salary_info.get('gross')
            result['salary_rur'] = salary_info.get('rur')
        else:
            result['salary_rur'] = None
        
        # Опыт работы
        result['experience'] = vacancy.get('experience', 'Не указан')
        
        # Тип занятости
        result['employment'] = vacancy.get('employment', 'Не указан')
        
        # График работы
        result['schedule'] = vacancy.get('schedule', 'Не указан')
        
        # Ключевые навыки
        key_skills = vacancy.get('key_skills', [])
        if isinstance(key_skills, list):
            result['key_skills'] = json.dumps(key_skills, ensure_ascii=False)
        else:
            result['key_skills'] = '[]'
        
        # Профессиональные роли
        prof_roles = vacancy.get('professional_roles', [])
        if isinstance(prof_roles, list):
            result['professional_roles'] = json.dumps(prof_roles, ensure_ascii=False)
        else:
            result['professional_roles'] = '[]'
        
        # Дополнительные поля
        result['has_test'] = vacancy.get('has_test', False)
        result['response_letter_required'] = vacancy.get('response_letter_required', False)
        result['archived'] = vacancy.get('archived', False)
        
        # Извлечение даты для анализа
        if 'published_at' in result and result['published_at']:
            try:
                published_date = pd.to_datetime(result['published_at'])
                result['date'] = published_date.date()
                result['year'] = published_date.year
                result['month'] = published_date.month
                result['weekday'] = published_date.strftime('%A')
            except:
                result['date'] = pd.Timestamp.now().date()
        
        return result
        
    except Exception as e:
        print(f"Ошибка обработки вакансии {vacancy.get('id')}: {e}")
        import traceback
        traceback.print_exc()
        return None