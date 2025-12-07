from datetime import date, datetime, timedelta

INPUT_TYPE = dict[str, "MAIN_TYPE"] | list["MAIN_TYPE"]
MAIN_TYPE = INPUT_TYPE | datetime | date | timedelta | str | int | float | bool
