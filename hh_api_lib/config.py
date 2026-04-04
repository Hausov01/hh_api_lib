from dataclasses import dataclass

@dataclass
class HHConfig:
    per_page: int = 100
    max_vacancies: int = 2000
    timeout: tuple = (3, 10)

@dataclass
class SearchParams_period:
    period: int
    area_id: str
    vacancy: str
    base_url: str
    access_token: str
    email: str

@dataclass
class SearchParams_dateTodate:
    start_date: str
    end_date: str
    area_id: str
    vacancy: str
    base_url: str
    access_token: str
    email: str
