from dataclasses import dataclass
from typing import Optional

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
