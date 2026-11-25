# DAX Measures Documentation

This document provides complete documentation of all DAX measures used in the Telangana Weather Analytics Dashboard.

---

## 1. Core Aggregations

### Total Rainfall
```dax
Total Rainfall = SUM(weather_data[rainfall_mm])
```
**Description:** Calculates the total rainfall across all districts and time periods.

### Average Rainfall
```dax
Avg Rainfall = AVERAGE(weather_data[rainfall_mm])
```
**Description:** Returns the arithmetic mean of rainfall values.

### Max Temperature
```dax
Max Temperature = MAX(weather_data[max_temp])
```
**Description:** Returns the highest temperature recorded.

### Min Temperature
```dax
Min Temperature = MIN(weather_data[min_temp])
```
**Description:** Returns the lowest temperature recorded.

### Average Temperature
```dax
Avg Temperature = AVERAGE(weather_data[max_temp])
```
**Description:** Returns the average of maximum temperatures.

### Diurnal Temperature Range
```dax
Avg Diurnal Range = AVERAGE(weather_data[temp_range])
```
**Description:** Calculates the average difference between daily max and min temperatures.

---

## 2. Anomaly Detection Measures

### Extreme Rainfall Flag
```dax
Extreme Rainfall Flag = 
VAR RollingAvg = CALCULATE(
    AVERAGE(weather_data[rainfall_mm]),
    DATESINPERIOD(
        'Calendar'[Date],
        LASTDATE('Calendar'[Date]),
        -7,
        DAY
    )
)
VAR CurrentRainfall = SUM(weather_data[rainfall_mm])
RETURN
IF(
    CurrentRainfall > RollingAvg * 2,
    "Extreme",
    "Normal"
)
```
**Description:** Flags rainfall events that exceed 2x the 7-day rolling average. Useful for identifying sudden heavy rainfall events that could indicate flooding risk.

### Heat Wave Flag
```dax
Heat Wave Flag = 
IF(
    MAX(weather_data[max_temp]) > 45,
    "Heat Wave",
    "Normal"
)
```
**Description:** Flags days with maximum temperature exceeding 45°C. This threshold is based on IMD (India Meteorological Department) heat wave criteria.

### Extreme Temperature Count
```dax
Extreme Temp Days = 
COUNTROWS(
    FILTER(
        weather_data,
        weather_data[max_temp] > 45 || weather_data[min_temp] < 10
    )
)
```
**Description:** Counts days with extreme temperatures (max > 45°C or min < 10°C).

---

## 3. Drought & Risk Score Measures

### Drought Risk Score (District Level)
```dax
Drought Risk Score (District) = 
VAR AvgRainfall = CALCULATE(
    AVERAGE(weather_data[rainfall_mm]),
    ALLEXCEPT(weather_data, weather_data[district])
)
VAR AvgTemp = CALCULATE(
    AVERAGE(weather_data[max_temp]),
    ALLEXCEPT(weather_data, weather_data[district])
)
VAR AvgHumidity = CALCULATE(
    AVERAGE(weather_data[humidity_pct]),
    ALLEXCEPT(weather_data, weather_data[district])
)
VAR MaxRainfall = CALCULATE(
    MAX(weather_data[rainfall_mm]),
    ALLEXCEPT(weather_data, weather_data[district])
)
VAR MaxTemp = CALCULATE(
    MAX(weather_data[max_temp]),
    ALLEXCEPT(weather_data, weather_data[district])
)
RETURN
(
    (1 - (AvgRainfall / MaxRainfall)) * 0.4 +  -- Rainfall risk (lower = higher risk)
    ((MaxTemp - MIN(weather_data[max_temp])) / 
        (MAX(weather_data[max_temp]) - MIN(weather_data[max_temp]))) * 0.35 +  -- Temp risk
    (1 - (AvgHumidity / 100)) * 0.25  -- Humidity risk (lower = higher risk)
) * 100
```
**Description:** Calculates a composite drought/crop risk score (0-100) for each district. Higher scores indicate greater drought risk.

**Components:**
- Rainfall component (40%): Districts with below-average rainfall score higher
- Temperature component (35%): Districts with higher average max temperatures score higher
- Humidity component (25%): Districts with lower humidity score higher

### Crop Risk Category
```dax
Crop Risk Category = 
SWITCH(
    TRUE(),
    [Drought Risk Score (District)] < 30, "Low Risk",
    [Drought Risk Score (District)] < 50, "Moderate Risk",
    [Drought Risk Score (District)] < 70, "High Risk",
    "Severe Risk"
)
```
**Description:** Categorizes districts into risk categories based on drought risk score.

---

## 4. Time Intelligence Measures

### Year-over-Year Rainfall Change
```dax
YoY Rainfall Change = 
VAR CurrentYear = SELECTEDVALUE('Calendar'[Year])
VAR PreviousYear = CurrentYear - 1
VAR CurrentRainfall = CALCULATE(
    SUM(weather_data[rainfall_mm]),
    'Calendar'[Year] = CurrentYear
)
VAR PreviousRainfall = CALCULATE(
    SUM(weather_data[rainfall_mm]),
    'Calendar'[Year] = PreviousYear
)
RETURN
DIVIDE(CurrentRainfall - PreviousRainfall, PreviousRainfall, 0)
```
**Description:** Calculates percentage change in rainfall compared to the previous year.

### Same Period Last Year Rainfall
```dax
SPLY Rainfall = 
CALCULATE(
    SUM(weather_data[rainfall_mm]),
    SAMEPERIODLASTYEAR('Calendar'[Date])
)
```
**Description:** Returns rainfall for the same period in the previous year.

### Moving Average (7-Day)
```dax
7-Day Moving Avg Rainfall = 
CALCULATE(
    AVERAGE(weather_data[rainfall_mm]),
    DATESINPERIOD(
        'Calendar'[Date],
        LASTDATE('Calendar'[Date]),
        -7,
        DAY
    )
)
```
**Description:** Calculates a 7-day rolling average of rainfall.

### Year-to-Date Rainfall
```dax
YTD Rainfall = 
TOTALYTD(
    SUM(weather_data[rainfall_mm]),
    'Calendar'[Date]
)
```
**Description:** Cumulative rainfall from start of year to current date.

---

## 5. Ranking & Comparison Measures

### District Rainfall Rank
```dax
District Rainfall Rank = 
RANKX(
    ALL(weather_data[district]),
    CALCULATE(SUM(weather_data[rainfall_mm])),
    ,
    DESC,
    Dense
)
```
**Description:** Ranks districts by total rainfall (1 = highest).

### Top District Selection
```dax
Top District by Rainfall = 
TOPN(
    1,
    SUMMARIZE(weather_data, weather_data[district], "Total", SUM(weather_data[rainfall_mm])),
    [Total],
    DESC
)
```
**Description:** Returns the district with the highest total rainfall.

### Percent of Total Rainfall
```dax
% of Total Rainfall = 
DIVIDE(
    SUM(weather_data[rainfall_mm]),
    CALCULATE(SUM(weather_data[rainfall_mm]), ALL(weather_data))
)
```
**Description:** Shows each district's contribution to total rainfall as a percentage.

---

## 6. Anomaly Event Measures

### Total Anomaly Events
```dax
Total Anomaly Events = 
COUNTROWS(
    FILTER(
        weather_data,
        weather_data[extreme_rainfall] = TRUE() || 
        weather_data[heat_wave] = TRUE() || 
        weather_data[drought_flag] = TRUE()
    )
)
```
**Description:** Counts total anomaly events (extreme rainfall, heat waves, drought flags).

### Anomaly Events by Type
```dax
Anomaly Events by Type = 
SWITCH(
    SELECTEDVALUE('Anomaly Type'[Type]),
    "Extreme Rainfall", 
        CALCULATE(
            COUNTROWS(weather_data),
            weather_data[extreme_rainfall] = TRUE()
        ),
    "Heat Wave", 
        CALCULATE(
            COUNTROWS(weather_data),
            weather_data[heat_wave] = TRUE()
        ),
    "Drought", 
        CALCULATE(
            COUNTROWS(weather_data),
            weather_data[drought_flag] = TRUE()
        )
)
```
**Description:** Categorizes and counts anomaly events by type.

### Days Since Last Anomaly
```dax
Days Since Last Anomaly = 
VAR LastAnomalyDate = 
CALCULATE(
    MAX(weather_data[date]),
    FILTER(
        weather_data,
        weather_data[extreme_rainfall] = TRUE() || 
        weather_data[heat_wave] = TRUE() || 
        weather_data[drought_flag] = TRUE()
    )
)
RETURN
DATEDIFF(LastAnomalyDate, TODAY(), DAY)
```
**Description:** Calculates days since the last recorded anomaly event.

---

## 7. Forecast Measures (for Forecasting Page)

### Simple Moving Average Forecast
```dax
SMA Forecast (30 Days) = 
VAR HistoricalAvg = 
CALCULATE(
    AVERAGE(weather_data[rainfall_mm]),
    DATESINPERIOD(
        'Calendar'[Date],
        LASTDATE('Calendar'[Date]),
        -30,
        DAY
    )
)
VAR SeasonalFactor = 
DIVIDE(
    CALCULATE(
        AVERAGE(weather_data[rainfall_mm]),
        FILTER(
            ALL('Calendar'),
            'Calendar'[Month] = SELECTEDVALUE('Calendar'[Month])
        )
    ),
    CALCULATE(AVERAGE(weather_data[rainfall_mm]), ALL('Calendar'))
)
RETURN
HistoricalAvg * SeasonalFactor
```
**Description:** Simple 30-day moving average forecast adjusted for seasonal factors.

### Temperature Forecast Trend
```dax
Temperature Trend = 
LINESTX(
    VALUES('Calendar'[Date]),
    weather_data[max_temp],
    'Calendar'[Date]
)
```
**Description:** Calculates linear trend of temperature over time using regression.

---

## 8. Data Quality Measures

### Records with Issues
```dax
Data Quality Issues = 
COUNTROWS(
    FILTER(
        weather_data,
        weather_data[temp_outlier] = TRUE() || 
        weather_data[rainfall_negative] = TRUE() || 
        weather_data[humidity_outlier] = TRUE()
    )
)
```
**Description:** Counts records that failed validation checks.

### Data Quality Score
```dax
Data Quality Score (%) = 
1 - DIVIDE(
    [Data Quality Issues],
    COUNTROWS(weather_data)
)
```
**Description:** Percentage of records that passed all validation checks.

---

## 9. Conditional Formatting Rules

### Rainfall Intensity
| Value Range | Color | Interpretation |
|-------------|-------|----------------|
| 0-10 mm | Light Blue | Light Rain |
| 10-50 mm | Medium Blue | Moderate Rain |
| 50-100 mm | Dark Blue | Heavy Rain |
| 100+ mm | Purple | Very Heavy Rain |

### Temperature Risk
| Value Range | Color | Interpretation |
|-------------|-------|----------------|
| < 25°C | Green | Comfortable |
| 25-35°C | Yellow | Warm |
| 35-42°C | Orange | Hot |
| 42-45°C | Red | Very Hot |
| > 45°C | Dark Red | Extreme Heat |

### Drought Risk Score
| Score Range | Color | Interpretation |
|-------------|-------|----------------|
| 0-30 | Green | Low Risk |
| 30-50 | Yellow | Moderate Risk |
| 50-70 | Orange | High Risk |
| 70-100 | Red | Severe Risk |

---

## 10. Calculation Groups (Optional)

For multi-measure comparisons, consider creating a calculation group with:
- Total (SUM)
- Average (AVERAGE)
- Min (MIN)
- Max (MAX)
- YoY Change (%)

This allows users to toggle between different aggregation types without creating separate measures for each.

---

## Usage Notes

1. **Calendar Table:** All time intelligence measures require a proper Calendar table with continuous dates.
2. **Mark as Date Table:** The Calendar table should be marked as the date table in the model.
3. **Relationship:** Ensure one-to-many relationship between Calendar[Date] and weather_data[date].
4. **Filter Context:** Measures respect visual and report-level filters.

---

*Last Updated: November 2024*
*Author: SAI LAKSHMI RAJULAPATI*