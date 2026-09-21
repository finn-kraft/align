# electricity-forecast

Fits a Ridge electricity-usage model from daily weather, billing-period kWh, and daily occupancy, then forecasts normal and extreme-weather scenarios.

```python
from electricity_forecast import ElectricityForecaster

f = ElectricityForecaster(extreme_seasons=7)
f.fit("temps.csv", "usage.csv", "occupancy.csv")

print(f.extreme_years_)
forecast = f.forecast("2028-06-30", scenarios=("normal", "hot_summer", "cold_winter", "worst", "best"))
print(forecast)
```

`fit()` accepts either CSV paths or pandas DataFrames. The default future occupancy schedule repeats Jan 5-May 5 and Aug 10-Dec 11 each year. Pass `occupancy_fn=` to `forecast()` to override it.

Scenarios:
- `normal`: full-record calendar-day climatology
- `hot_summer`: normal weather except Jun-Aug profile from hottest summers by CDD
- `cold_winter`: normal weather except Dec-Feb profile from coldest winters by HDD
- `worst`: cold-winter + hot-summer profiles
- `best`: warm-winter + cool-summer profiles
