# hh_api_client.py
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import yaml
import json

class HHAPIClient:
    """Улучшенный клиент для работы с API HeadHunter."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.base_url = self.config['api']['base_url']
        self.headers = {
            'User-Agent': self.config['api']['user_agent'],
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.timeout = self.config['api']['timeout']
        self.delay = self.config['api']['delays']['between_requests']
        self.logger = self._setup_logger()
        self.session = requests.Session()
        
        # Статистика запросов
        self.request_count = 0
        self.error_count = 0
        
        # Получаем OAuth токен
        self.access_token = None
        if 'oauth' in self.config:
            self.access_token = self._get_access_token()
            if self.access_token:
                self.headers['Authorization'] = f'Bearer {self.access_token}'
                self.logger.info("✅ OAuth авторизация успешна")
            else:
                self.logger.warning("⚠ Не удалось получить OAuth токен")
        
        # Загружаем курсы валют
        self.currency_rates = self._load_currency_rates()
        
        # Кэш для временного хранения данных
        self.cache = {}
    
    def _setup_logger(self):
        logger = logging.getLogger('HHAPIClient')
        logger.setLevel(logging.INFO)
        
        # Форматирование
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Файловый вывод
        file_handler = logging.FileHandler('hh_api.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _get_access_token(self) -> Optional[str]:
        """Получает OAuth токен доступа."""
        try:
            oauth_config = self.config['oauth']
            token_url = oauth_config.get('token_url', 'https://hh.ru/oauth/token')
            
            # Используем client credentials flow
            data = {
                'grant_type': 'client_credentials',
                'client_id': oauth_config['client_id'],
                'client_secret': oauth_config['client_secret'],
                'scope': 'read_vacancies'
            }
            
            response = requests.post(
                token_url,
                data=data,
                headers={'User-Agent': self.headers['User-Agent']},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                
                self.logger.info(f"Токен получен, срок действия: {expires_in} сек")
                return access_token
            else:
                self.logger.error(f"Ошибка получения токена: {response.status_code}")
                self.logger.debug(f"Ответ: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка получения OAuth токена: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Выполняет HTTP запрос с обработкой ошибок и повторами."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Добавляем заголовки
        headers = self.headers.copy()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.request_count += 1
                
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Логируем запрос
                self.logger.debug(f"Запрос {method} {url} - статус {response.status_code}")
                
                # Обработка ошибок
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    self.logger.warning(f"Доступ запрещен (403) для {url}")
                    time.sleep(self.config['api']['delays']['after_403'])
                    continue
                elif response.status_code == 404:
                    self.logger.debug(f"Ресурс не найден (404): {url}")
                    return None
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"Превышен лимит запросов. Пауза {retry_after} сек")
                    time.sleep(retry_after)
                    continue
                else:
                    self.logger.error(f"Ошибка {response.status_code} для {url}")
                    self.error_count += 1
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут запроса (попытка {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Ошибка сети: {e}")
                self.error_count += 1
                break
            except json.JSONDecodeError as e:
                self.logger.error(f"Ошибка парсинга JSON: {e}")
                break
        
        return None
    
    def _load_currency_rates(self) -> Dict[str, float]:
        """Загружает справочник курсов валют."""
        try:
            response = self._make_request('GET', 'dictionaries')
            if response and 'currency' in response:
                rates = {curr['code']: curr['rate'] for curr in response['currency']}
                self.logger.info(f"Загружены курсы для {len(rates)} валют")
                return rates
        except Exception as e:
            self.logger.error(f"Ошибка загрузки курсов валют: {e}")
        
        return {'RUR': 1.0}
    
    def _calculate_salary_rur(self, salary_data: Optional[Dict]) -> Optional[float]:
        """Конвертирует зарплату в рубли (на руки)."""
        if not salary_data:
            return None
        
        try:
            # Используем медиану диапазона или одно значение
            salary_from = salary_data.get('from')
            salary_to = salary_data.get('to')
            
            if salary_from is not None and salary_to is not None:
                salary = (salary_from + salary_to) / 2
            elif salary_from is not None:
                salary = salary_from
            elif salary_to is not None:
                salary = salary_to
            else:
                return None
            
            # Конвертация в рубли
            currency = salary_data.get('currency', 'RUR')
            rate = self.currency_rates.get(currency, 1.0)
            salary_rur = salary * rate
            
            # Учет налога (gross = до вычета налога)
            if salary_data.get('gross'):
                salary_rur *= 0.87  # НДФЛ 13%
            
            return round(salary_rur, 2)
            
        except Exception as e:
            self.logger.debug(f"Ошибка расчета зарплаты: {e}")
            return None
    
    def search_vacancies(self, **params) -> Tuple[List[Dict], int]:
        """Поиск вакансий с пагинацией."""
        all_vacancies = []
        page = 0
        
        # Параметры по умолчанию
        default_params = {
            'per_page': 100,
            'page': 0,
            'only_with_salary': self.config.get('api', {}).get('only_with_salary', True)
        }
        default_params.update(params)
        
        while True:
            default_params['page'] = page
            data = self._make_request('GET', 'vacancies', params=default_params)
            
            if not data:
                break
            
            vacancies = data.get('items', [])
            all_vacancies.extend(vacancies)
            
            # Пагинация
            pages = data.get('pages', 0)
            page += 1
            
            self.logger.info(f"Страница {page}/{pages}: {len(vacancies)} вакансий")
            
            # Ограничение по количеству
            max_vacancies = self.config.get('period', {}).get('max_vacancies_per_query', 2000)
            if len(all_vacancies) >= max_vacancies:
                self.logger.info(f"Достигнут лимит в {max_vacancies} вакансий")
                break
            
            if page >= pages:
                break
            
            time.sleep(self.delay)
        
        return all_vacancies, len(all_vacancies)
    
    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict]:
        """Получает детальную информацию о вакансии."""
        try:
            data = self._make_request('GET', f'vacancies/{vacancy_id}')
            if not data:
                return None
            
            # Обработка региона
            area_data = data.get('area', {})
            area_id = None
            area_name = None
            
            if isinstance(area_data, dict):
                area_id = area_data.get('id')
                area_name = area_data.get('name')
            elif isinstance(area_data, str):
                area_name = area_data
            else:
                # Пробуем получить из других полей
                address_data = data.get('address', {})
                if isinstance(address_data, dict):
                    area_name = address_data.get('city', 'Не указан')
                else:
                    area_name = 'Не указан'
            
            # Обработка зарплаты
            salary_data = data.get('salary')
            salary_rur = self._calculate_salary_rur(salary_data)
            
            # Извлечение ключевых навыков
            key_skills = []
            try:
                key_skills_data = data.get('key_skills', [])
                if isinstance(key_skills_data, list):
                    key_skills = [
                        skill.get('name', '') if isinstance(skill, dict) else str(skill)
                        for skill in key_skills_data
                    ]
            except Exception:
                pass
            
            # Формируем структурированные данные
            vacancy = {
                'id': data.get('id'),
                'name': data.get('name', '').strip(),
                'area_id': area_id,
                'area_name': area_name,
                'employer_name': data.get('employer', {}).get('name', ''),
                'salary': {
                    'from': salary_data.get('from') if salary_data else None,
                    'to': salary_data.get('to') if salary_data else None,
                    'currency': salary_data.get('currency') if salary_data else None,
                    'gross': salary_data.get('gross') if salary_data else None,
                    'rur': salary_rur
                },
                'experience': data.get('experience', {}).get('name', 'Не указан'),
                'employment': data.get('employment', {}).get('name', 'Не указан'),
                'schedule': data.get('schedule', {}).get('name', 'Не указан'),
                'key_skills': key_skills,
                'professional_roles': [
                    role.get('name', '') 
                    for role in data.get('professional_roles', []) 
                    if isinstance(role, dict)
                ],
                'published_at': data.get('published_at'),
                'created_at': data.get('created_at'),
                'alternate_url': data.get('alternate_url', ''),
                'description': data.get('description', ''),
                'has_test': data.get('has_test', False),
                'response_letter_required': data.get('response_letter_required', False),
                'archived': data.get('archived', False)
            }
            
            # Для совместимости с data_processor
            vacancy['salary_rur'] = salary_rur
            
            return vacancy
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки вакансии {vacancy_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def collect_vacancies_for_diploma(self) -> List[Dict]:
        """Основной метод сбора данных для дипломного проекта."""
        all_vacancies = []
        start_time = datetime.now() - timedelta(days=self.config['period']['days_to_collect'])
        
        self.logger.info("=" * 60)
        self.logger.info("НАЧАЛО СБОРА ДАННЫХ ДЛЯ ДИПЛОМА")
        self.logger.info(f"Период: последние {self.config['period']['days_to_collect']} дней")
        self.logger.info("=" * 60)
        
        # Собираем данные по всем запросам и регионам
        for region in self.config['regions']:
            for query_group in self.config['search_queries']:
                for keyword in query_group['keywords']:
                    self.logger.info(f"🔍 Поиск: '{keyword}' в регионе {region['name']}")
                    
                    # Поиск вакансий
                    vacancies, count = self.search_vacancies(
                        text=keyword,
                        area=region['id'],
                        date_from=start_time.isoformat(),
                        date_to=datetime.now().isoformat()
                    )
                    
                    self.logger.info(f"   Найдено: {count} вакансий")
                    
                    # Получение деталей
                    detailed_count = 0
                    for vacancy in vacancies[:20]:
                        vacancy_id = vacancy.get('id')
                        if vacancy_id:
                            details = self.get_vacancy_details(vacancy_id)
                            if details:
                                all_vacancies.append(details)
                                detailed_count += 1
                            time.sleep(self.delay * 0.5)
                    
                    self.logger.info(f"   Получено деталей: {detailed_count}")
        
        self.logger.info("=" * 60)
        self.logger.info(f"СБОР ЗАВЕРШЕН. Всего вакансий: {len(all_vacancies)}")
        self.logger.info(f"Статистика: {self.request_count} запросов, {self.error_count} ошибок")
        self.logger.info("=" * 60)
        
        return all_vacancies