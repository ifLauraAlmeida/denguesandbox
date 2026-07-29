import pandas as pd
import pytest

from dengue_rj.indicators.core import aggregate_incidence, incidence, notification_delay


def test_incidence_and_aggregation():
    assert incidence(10, 1000) == 10
    assert aggregate_incidence(pd.Series([10, 90]), pd.Series([1000, 9000])) == 10


def test_zero_population_fails():
    with pytest.raises(ValueError):
        incidence(1, 0)


def test_notification_delay_masks_negative():
    result = notification_delay(pd.Series(["2024-01-02"]), pd.Series(["2024-01-01"]))
    assert result.isna().all()
