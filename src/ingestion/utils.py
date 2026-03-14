from datetime import date, timedelta


def check_date_range_overlap(range_1: tuple[date, date], range_2: tuple[date, date]) -> bool:
    """Check whether two date ranges overlap or are within one week of each other.

    Returns True if the two date ranges either overlap directly, or if any
    boundary of one range falls within one week of the opposing boundary of
    the other range. This looser-than-strict overlap check is useful for
    matching schedule entries that may span slightly different week boundaries.

    Args:
        range_1: (start, end) dates of the first range.
        range_2: (start, end) dates of the second range.

    Returns:
        True if the ranges overlap or are within one week of each other,
        False otherwise.
    """
    week_start_1, week_end_1 = range_1
    week_start_2, week_end_2 = range_2
    overlap = week_start_1 <= week_end_2 and week_end_1 >= week_start_2
    one_week_or_less1 = abs(week_end_1 - week_start_2) <= timedelta(weeks=1)
    one_week_or_less2 = abs(week_start_1 - week_end_2) <= timedelta(weeks=1)
    return overlap or one_week_or_less1 or one_week_or_less2
