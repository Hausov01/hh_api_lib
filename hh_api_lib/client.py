import requests
import time
from dataclasses import dataclass
from typing import Any, Dict
import math
import logging
from typing import Optional
from .config import HHConfig, SearchParams
from .exceptions import HHCaptchaRequired


logger = logging.getLogger(__name__)

__all__ = ['external_request']

if __name__ == "__main__":
    logger.info("Прямой запуск не предусмотрен")

@dataclass
class HHConfig:
    per_page: int = 100
    max_vacancies: int = 2000
    timeout: tuple = (3, 10)

@dataclass
class SearchParams:
    area_id: str
    vacancy: str
    base_url: str
    access_token: str | None = None
    email: str | None = None

    period: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class HHCaptchaRequired(Exception):
    def __init__(self, captcha_url: str):
        self.captcha_url = captcha_url
        super().__init__(f"Captcha required. Solve here: {captcha_url}")

def external_request(search_config: SearchParams, show_progress: bool = False, get_total_found: bool = False):
        count = 0
        results = []
        hhconfig = HHConfig()
        with requests.Session() as session:
            headers = {
                'User-Agent': f'HH-API-Client/1.0 ({search_config.email})' if search_config.email else 'HH-API-Client/1.0'
            }
            if search_config.access_token:
                headers['Authorization'] = f'Bearer {search_config.access_token}'
            if not search_config.access_token:
                logger.info("WARNING: No access token provided")
            session.headers.update(headers)

            logger.info("--- Этап 1: Сбор ID вакансий ---")
            logger.info("Поиск по вакансии: %s", search_config.vacancy)
            all_vacancy_ids, total_found = _get_all_vacancy_ids(session, search_config, hhconfig)
            logger.info('-'*30)
            #logger.info(all_vacancy_ids)
            all_data= _get_all_vacancy_details(session, all_vacancy_ids, search_config, hhconfig, show_progress)
            #logger.info(all_data)
            if get_total_found:
                return all_data, total_found
            else:
                return all_data



def _get_all_vacancy_ids(session, search_config: SearchParams, hhconfig: HHConfig):

    all_vacancy_ids=[]
    logger.info("Fetching vacancy pages info")
    params = {
        'text': search_config.vacancy,
        'area': search_config.area_id,
        'per_page': hhconfig.per_page,
        'page': 0
    }

    if search_config.period is not None:
        params['period'] = search_config.period

    elif search_config.start_date and search_config.end_date:
        params['date_from'] = search_config.start_date
        params['date_to'] = search_config.end_date

    else:
        raise ValueError("Provide either period or start_date + end_date")

    data = _request(session, search_config.base_url, params, hhconfig.timeout)
    total_found = data.get('found', 0)
    pages_available = data.get('pages', 0)
    logger.info(f"total_found:{total_found}, pages_available: {pages_available}")
    total_found = min(total_found, hhconfig.max_vacancies)
    pages_available = math.ceil(total_found / hhconfig.per_page)
    logger.info(f"After max_vacancies debug total_found:{total_found}, pages_available: {pages_available}")
    seen = set()
    for i in range(pages_available):
        logger.info("page %s", i)
        params = {
            'text': search_config.vacancy,
            'area': search_config.area_id,
            'per_page': hhconfig.per_page,
            'page': 0
        }

        if search_config.period is not None:
            params['period'] = search_config.period

        elif search_config.start_date and search_config.end_date:
            params['date_from'] = search_config.start_date
            params['date_to'] = search_config.end_date

        else:
            raise ValueError("Provide either period or start_date + end_date")

        data = _request(session, search_config.base_url, params, hhconfig.timeout)
        vacancy_ids = [item['id'] for item in data.get('items', []) if 'id' in item]
        logger.debug("Fetched IDs: %s", vacancy_ids)
        for item in vacancy_ids:
            #if len(all_vacancy_ids) >= hhconfig.max_vacancies:
            #    return all_vacancy_ids
            if item not in seen:
                seen.add(item)
                all_vacancy_ids.append(item)
    return all_vacancy_ids, total_found

def _get_all_vacancy_details(session, all_vacancy_ids, search_config: SearchParams, hhconfig: HHConfig, show_progress: bool = False,):
    all_data = []
    iterator = all_vacancy_ids
    if show_progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(all_vacancy_ids)
        except ImportError:
            logger.warning("tqdm not installed, progress bar disabled")

    for vacancy_id in iterator:
        details_url = f"{search_config.base_url}/{vacancy_id}"
        data = _request(session, details_url, None, hhconfig.timeout)
        if data is None:
            continue
        all_data.append(data)
    return all_data




def _request(session: requests.Session, url: str, params: dict | None, timeout, max_retries: int = 3) -> Dict[str, Any]:
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=timeout)

            # --- 429 ---
            if response.status_code == 429:
                sleep_time = 2 ** attempt
                logger.info(f"Rate limit hit. Retry in {sleep_time}s")
                time.sleep(sleep_time)
                continue

            response.raise_for_status()

            data = response.json()

            # --- CAPTCHA CHECK ---
            if isinstance(data, dict) and "errors" in data:
                for err in data["errors"]:
                    if err.get("value") == "captcha_required":
                        captcha_url = err.get("captcha_url")
                        raise HHCaptchaRequired(captcha_url)

            return data

        except requests.exceptions.Timeout:
            logger.error(f"Timeout on attempt {attempt+1}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error on attempt {attempt+1}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code

            if status == 403:
                logger.warning(f"Access denied (403) for {url}")
                return None

            logger.error(f"HTTP error: {e}")
            raise
        except ValueError:
            logger.error("Invalid JSON response")
            raise


        time.sleep(2 ** attempt)

    raise RuntimeError("Max retries exceeded")