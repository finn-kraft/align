from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

TMAX = 'TMAX (Degrees Fahrenheit)'
TMIN = 'TMIN (Degrees Fahrenheit)'


def _read(data, *, skiprows=0):
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.read_csv(data, skiprows=skiprows)


def _clean_weather(data):
    df = _read(data, skiprows=1)
    df.columns = df.columns.str.strip()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df[['Date', TMAX, TMIN]].sort_values('Date').set_index('Date')
    idx = pd.date_range(df.index.min(), df.index.max(), freq='D')
    df = df.reindex(idx)
    df.index.name = 'Date'
    df[[TMAX, TMIN]] = df[[TMAX, TMIN]].interpolate(method='time', limit_direction='both')
    df = df.reset_index()
    df['TAVG'] = (df[TMAX] + df[TMIN]) / 2
    return df


def _occupancy_for_date(date):
    md = (date.month, date.day)
    return int((1, 5) <= md <= (5, 5) or (8, 10) <= md <= (12, 11))


@dataclass
class Tariff:
    supply_rate: float = 0.1029
    delivery_rate: float = 0.0907
    fixed_fee: float = 9.75

    def cost(self, kwh):
        kwh = np.asarray(kwh, dtype=float)
        return self.fixed_fee + kwh * (self.supply_rate + self.delivery_rate)


class ElectricityForecaster:
    def __init__(self, heating_base=60.0, cooling_base=70.0, ridge_alpha=10.0,
                 supply_rate=0.1029, delivery_rate=0.0907, fixed_fee=9.75,
                 extreme_seasons=7):
        self.heating_base = heating_base
        self.cooling_base = cooling_base
        self.ridge_alpha = ridge_alpha
        self.extreme_seasons = extreme_seasons
        self.tariff = Tariff(supply_rate, delivery_rate, fixed_fee)
        self.features = ['Bill Days', 'Occupied Days', 'Occupied HDD', 'Occupied CDD', 'Unoccupied HDD']

    def fit(self, weather, usage, occupancy):
        self.weather_ = _clean_weather(weather)
        usage = _read(usage)
        occupancy = _read(occupancy)
        usage.columns = usage.columns.str.strip()
        occupancy.columns = occupancy.columns.str.strip()
        usage['Billing From'] = pd.to_datetime(usage['Billing From'])
        usage['Billing To'] = pd.to_datetime(usage['Billing To'])
        occupancy['Date'] = pd.to_datetime(occupancy['Date'])
        self.usage_ = usage.sort_values('Billing From').reset_index(drop=True)
        self.occupancy_ = occupancy
        daily = self.weather_.merge(occupancy[['Date','Occupied']], on='Date', how='left')
        daily['Occupied'] = daily['Occupied'].fillna(0).astype(int)
        daily = self._daily_features(daily, temp_col='TAVG')
        rows = []
        for _, bill in self.usage_.iterrows():
            p = daily[(daily.Date >= bill['Billing From']) & (daily.Date <= bill['Billing To'])]
            rows.append(self._aggregate(p, bill['Billing From'], bill['Billing To'], bill['kWh Used']))
        self.model_data_ = pd.DataFrame(rows)
        X = self.model_data_[self.features].to_numpy(float)
        y = self.model_data_['kWh Used'].to_numpy(float)
        self.model_ = Ridge(alpha=self.ridge_alpha).fit(X, y)
        self._build_scenarios()
        return self

    def _daily_features(self, df, temp_col):
        out = df.copy()
        out['Unoccupied'] = 1 - out['Occupied']
        out['HDD'] = np.maximum(self.heating_base - out[temp_col], 0)
        out['CDD'] = np.maximum(out[temp_col] - self.cooling_base, 0)
        out['Occupied_HDD'] = out.Occupied * out.HDD
        out['Occupied_CDD'] = out.Occupied * out.CDD
        out['Unoccupied_HDD'] = out.Unoccupied * out.HDD
        return out

    def _aggregate(self, p, start, end, kwh=None):
        row = {'Billing From': start, 'Billing To': end, 'Bill Days': len(p),
               'Occupied Days': p.Occupied.sum(), 'Unoccupied Days': p.Unoccupied.sum(),
               'Occupied HDD': p.Occupied_HDD.sum(), 'Occupied CDD': p.Occupied_CDD.sum(),
               'Unoccupied HDD': p.Unoccupied_HDD.sum()}
        if kwh is not None: row['kWh Used'] = kwh
        return row

    def _build_scenarios(self):
        w = self.weather_.copy()
        w['year'] = w.Date.dt.year
        w['month'] = w.Date.dt.month
        w['calendar_day'] = w.Date.dt.strftime('%m-%d')
        w['HDD'] = np.maximum(self.heating_base - w.TAVG, 0)
        w['CDD'] = np.maximum(w.TAVG - self.cooling_base, 0)
        normal = w.groupby('calendar_day').TAVG.mean()

        # Winter season year is the year containing Jan/Feb (Dec belongs to next winter year).
        winter = w[w.month.isin([12,1,2])].copy()
        winter['season_year'] = winter.year + (winter.month == 12).astype(int)
        wc = winter.groupby('season_year').agg(days=('Date','size'), hdd=('HDD','sum'))
        wc = wc[wc.days >= 80]
        n = min(self.extreme_seasons, len(wc))
        cold_years = wc.nlargest(n, 'hdd').index
        warm_years = wc.nsmallest(n, 'hdd').index
        winter['season_year'] = winter.year + (winter.month == 12).astype(int)
        cold = winter[winter.season_year.isin(cold_years)].groupby('calendar_day').TAVG.mean()
        warm = winter[winter.season_year.isin(warm_years)].groupby('calendar_day').TAVG.mean()

        summer = w[w.month.isin([6,7,8])].copy()
        sc = summer.groupby('year').agg(days=('Date','size'), cdd=('CDD','sum'))
        sc = sc[sc.days >= 85]
        n2 = min(self.extreme_seasons, len(sc))
        hot_years = sc.nlargest(n2, 'cdd').index
        cool_years = sc.nsmallest(n2, 'cdd').index
        hot = summer[summer.year.isin(hot_years)].groupby('calendar_day').TAVG.mean()
        cool = summer[summer.year.isin(cool_years)].groupby('calendar_day').TAVG.mean()

        self.scenario_profiles_ = {'normal': normal, 'cold_winter': normal.copy(), 'hot_summer': normal.copy(),
                                   'worst': normal.copy(), 'best': normal.copy()}
        winter_days = [d for d in normal.index if d[:2] in ('12','01','02')]
        summer_days = [d for d in normal.index if d[:2] in ('06','07','08')]
        for d in winter_days:
            if d in cold.index:
                self.scenario_profiles_['cold_winter'].loc[d] = cold.loc[d]
                self.scenario_profiles_['worst'].loc[d] = cold.loc[d]
            if d in warm.index:
                self.scenario_profiles_['best'].loc[d] = warm.loc[d]
        for d in summer_days:
            if d in hot.index:
                self.scenario_profiles_['hot_summer'].loc[d] = hot.loc[d]
                self.scenario_profiles_['worst'].loc[d] = hot.loc[d]
            if d in cool.index:
                self.scenario_profiles_['best'].loc[d] = cool.loc[d]
        self.extreme_years_ = {'coldest_winters': list(map(int, cold_years)), 'warmest_winters': list(map(int, warm_years)),
                               'hottest_summers': list(map(int, hot_years)), 'coolest_summers': list(map(int, cool_years))}

    def forecast(self, through, start=None, scenarios=('normal','worst','best'), occupancy_fn=None):
        if not hasattr(self, 'model_'): raise RuntimeError('Call fit() first.')
        start = pd.Timestamp(start) if start is not None else self.usage_['Billing To'].max() + pd.Timedelta(days=1)
        end = pd.Timestamp(through)
        occupancy_fn = occupancy_fn or _occupancy_for_date
        outputs = []
        for scenario in scenarios:
            profile = self.scenario_profiles_[scenario]
            fd = pd.DataFrame({'Date': pd.date_range(start, end, freq='D')})
            fd['calendar_day'] = fd.Date.dt.strftime('%m-%d')
            fd['TAVG'] = fd.calendar_day.map(profile)
            # Feb 29 or any missing day: interpolate from adjacent mapped values.
            fd['TAVG'] = fd.TAVG.interpolate(limit_direction='both')
            fd['Occupied'] = fd.Date.map(occupancy_fn).astype(int)
            fd = self._daily_features(fd, 'TAVG')
            bill_rows = []
            bs = start
            while bs <= end:
                be = min(bs + pd.DateOffset(months=1) - pd.Timedelta(days=1), end)
                p = fd[(fd.Date >= bs) & (fd.Date <= be)]
                bill_rows.append(self._aggregate(p, bs, be))
                bs = be + pd.Timedelta(days=1)
            out = pd.DataFrame(bill_rows)
            pred = np.maximum(self.model_.predict(out[self.features].to_numpy(float)), 0)
            out['Scenario'] = scenario
            out['Predicted kWh'] = pred
            out['Supply Cost'] = pred * self.tariff.supply_rate
            out['Delivery Usage Cost'] = pred * self.tariff.delivery_rate
            out['Delivery Fixed Cost'] = self.tariff.fixed_fee
            out['Predicted Bill'] = self.tariff.cost(pred)
            outputs.append(out)
        return pd.concat(outputs, ignore_index=True)
