# SQL Database Schema Documentation

This document describes the SQLite database schema for the Telangana Weather Analytics Dashboard.

---

## Database: `telangana_weather.db`

### Table: `weather_data`

Primary table containing daily weather observations with computed columns and anomaly flags.

```sql
CREATE TABLE weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    district TEXT NOT NULL,
    mandal TEXT,
    max_temp FLOAT,
    min_temp FLOAT,
    rainfall_mm FLOAT,
    humidity_pct FLOAT,
    wind_speed_kmph FLOAT,
    temp_range FLOAT,           -- Computed: max_temp - min_temp
    heat_index FLOAT,           -- Computed: max_temp + (0.5 * humidity * (max_temp - 20))
    month INTEGER,              -- Extracted from date
    year INTEGER,               -- Extracted from date
    season TEXT,                -- Computed: Monsoon/Post-Monsoon/Winter/Pre-Monsoon
    temp_outlier BOOLEAN,       -- Validation flag: temp outside 15-50°C
    rainfall_negative BOOLEAN,  -- Validation flag: negative rainfall
    humidity_outlier BOOLEAN,   -- Validation flag: humidity outside 0-100%
    extreme_rainfall BOOLEAN,   -- Anomaly flag: > 2x rolling avg
    heat_wave BOOLEAN,          -- Anomaly flag: max_temp > 45°C
    drought_flag BOOLEAN,       -- Anomaly flag: low monsoon rainfall
    drought_risk_score FLOAT,   -- Computed: 0-100 composite score
    data_quality_flag TEXT,     -- CLEAN or ISSUES
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_weather_date ON weather_data(date);
CREATE INDEX idx_weather_district ON weather_data(district);
CREATE INDEX idx_weather_district_date ON weather_data(district, date);
CREATE INDEX idx_weather_season ON weather_data(season);
CREATE INDEX idx_weather_anomalies ON weather_data(extreme_rainfall, heat_wave, drought_flag);
```

---

### Table: `district_summary`

Aggregated statistics per district for dashboard KPI cards.

```sql
CREATE TABLE district_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    avg_rainfall FLOAT,
    total_rainfall FLOAT,
    avg_max_temp FLOAT,
    avg_min_temp FLOAT,
    avg_humidity FLOAT,
    avg_wind_speed FLOAT,
    extreme_rainfall_days INTEGER,
    heat_wave_days INTEGER,
    avg_drought_risk_score FLOAT,
    data_quality_score FLOAT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_district_name ON district_summary(district);
```

---

### Table: `monthly_summary`

Monthly rollup data for trend analysis.

```sql
CREATE TABLE monthly_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER,
    month INTEGER,
    district TEXT,
    total_rainfall FLOAT,
    avg_temp FLOAT,
    max_temp FLOAT,
    min_temp FLOAT,
    avg_humidity FLOAT,
    extreme_days INTEGER,
    season TEXT,
    FOREIGN KEY (district) REFERENCES district_summary(district)
);

CREATE INDEX idx_monthly_year_month ON monthly_summary(year, month);
CREATE INDEX idx_monthly_district ON monthly_summary(district);
```

---

### Table: `anomaly_events`

Catalog of detected anomaly events for reporting.

```sql
CREATE TABLE anomaly_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    district TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- Extreme Rainfall, Heat Wave, Drought
    value FLOAT,
    threshold FLOAT,
    severity TEXT,              -- Low, Medium, High
    description TEXT,
    acknowledged BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_anomaly_date ON anomaly_events(date);
CREATE INDEX idx_anomaly_district ON anomaly_events(district);
CREATE INDEX idx_anomaly_type ON anomaly_events(event_type);
```

---

### Table: `rainfall_forecast`

90-day rainfall predictions with seasonal adjustments.

```sql
CREATE TABLE rainfall_forecast (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    forecast_rainfall FLOAT,
    trend_contribution FLOAT,
    seasonal_index FLOAT,
    adjusted_forecast FLOAT
);

CREATE INDEX idx_rainfall_forecast_date ON rainfall_forecast(date);
```

---

### Table: `temperature_forecast`

90-day temperature predictions.

```sql
CREATE TABLE temperature_forecast (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    forecast_max_temp FLOAT,
    trend_contribution FLOAT,
    seasonal_index FLOAT,
    adjusted_forecast FLOAT
);

CREATE INDEX idx_temp_forecast_date ON temperature_forecast(date);
```

---

## Sample Queries

### 1. Get District Ranking by Rainfall
```sql
SELECT district, total_rainfall, 
       RANK() OVER (ORDER BY total_rainfall DESC) as rainfall_rank
FROM district_summary
ORDER BY total_rainfall DESC;
```

### 2. Monthly Trend Comparison
```sql
SELECT year, month, 
       SUM(total_rainfall) as monthly_rainfall,
       AVG(avg_temp) as avg_temperature
FROM monthly_summary
GROUP BY year, month
ORDER BY year, month;
```

### 3. Anomaly Events Summary
```sql
SELECT district, event_type, COUNT(*) as event_count,
       CASE 
           WHEN COUNT(*) > 10 THEN 'High Activity'
           WHEN COUNT(*) > 5 THEN 'Moderate Activity'
           ELSE 'Low Activity'
       END as activity_level
FROM anomaly_events
WHERE date >= DATE('now', '-1 year')
GROUP BY district, event_type;
```

### 4. Drought Risk Alert
```sql
SELECT district, avg_drought_risk_score,
       CASE 
           WHEN avg_drought_risk_score >= 70 THEN '🔴 SEVERE'
           WHEN avg_drought_risk_score >= 50 THEN '🟠 HIGH'
           WHEN avg_drought_risk_score >= 30 THEN '🟡 MODERATE'
           ELSE '🟢 LOW'
       END as risk_level
FROM district_summary
WHERE avg_drought_risk_score >= 50
ORDER BY avg_drought_risk_score DESC;
```

### 5. Heat Wave Days by Month
```sql
SELECT strftime('%Y-%m', date) as month, 
       COUNT(CASE WHEN heat_wave = 1 THEN 1 END) as heat_wave_days
FROM weather_data
WHERE heat_wave = 1
GROUP BY month
ORDER BY month;
```

---

## Power BI Connection

### Using SQLite ODBC Driver

1. Download and install [SQLite ODBC Driver](http://www.ch-werner.de/sqliteodbc/)
2. In Power BI: Get Data → ODBC → Select SQLite3 DSN
3. Connect to `data/telangana_weather.db`

### Connection String
```
Driver=SQLite3 ODBC Driver;Database=data/telangana_weather.db
```

---

*Last Updated: November 2024*