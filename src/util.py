import datetime
from typing import Optional, List

import dateparser
from asyncpg import Record

from dialog_manager import DialogResponse, DialogStatus


def transform_date(date: datetime.date | Record) -> str:
    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

    if date.year != date.today().year:
        year_str = f'{date.year} года'
    else:
        year_str = ''

    return f'{date.day} {months[int(date.month) - 1]}' + year_str


def parse_date(res: DialogResponse, date: str) -> Optional[datetime.date]:
    try:
        return dateparser.parse(date).date()
    except AttributeError:
        res.send_message('Некорректная дата, попробуйте ещё раз.')
        return None


def send_date_list(res: DialogResponse, notes: List[Record]) -> None:
    date_list: List[str] = [transform_date(i[3]) for i in notes]
    res.send_message(f"Запись с таким названием была сделана {', '.join(date_list[:-1])} и {date_list[-1]}. "
                     f"Выберите интересующий Вас день.")
