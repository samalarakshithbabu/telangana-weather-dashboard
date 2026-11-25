# 🌤️ Telangana Weather Analytics & Climate Dashboard (Enhanced Edition)

An interactive Business Intelligence dashboard built using **Microsoft Power BI** to analyze historical climate, precipitation, and thermal patterns across various districts in Telangana. This enhanced version includes Python data pipelines, SQL integration, anomaly detection, drought risk scoring, and forecasting capabilities.

---

## 📸 Dashboard Preview

### Dashboard Overview
![Overview Landing Page](docs/images/01_overview.png)
*Landing hub with core metrics across four environmental pillars.*

### Rainfall Analytics
![Rainfall Analytics](docs/images/02_rainfall.png)
*District-wise rainfall distribution with anomaly highlighting.*

### Temperature Insights
![Temperature Insights](docs/images/03_temperature.png)
*Thermal range analysis with heat wave flag indicators.*

### Drought Risk Assessment
![Drought Risk Score](docs/images/04_drought_risk.png)
*District-level crop risk scoring and early warning system.*

### Forecast Page
![Weather Forecast](docs/images/05_forecast.png)
*90-day rainfall and temperature forecasts with alerts.*

---

## 📊 Key Features

### 1. Data Pipeline & Database Layer
- **Python ETL Pipeline** (`src/data_cleaning.py`): Reproducible data cleaning with validation
- **SQLite Database** (`data/telangana_weather.db`): Structured data storage with optimized queries
- **Anomaly Detection**: Automated flagging of extreme events

### 2. Dashboard Pages

| Page | KPIs | Key Visuals |
|------|------|-------------|
| **Overview** | Total Rainfall, Avg Temp, Humidity, Wind Speed | District comparison cards |
| **Rainfall Analytics** | 604.44K mm total, 2.52 mm avg | Monthly trends, anomaly markers |
| **Temperature Insights** | Max: 46.80°C, Min: 21.09°C | Heat wave flags, diurnal range |
| **Humidity Patterns** | Peak: 100%, Min: 10.49% | Dual-bar seasonal comparison |
| **Wind Speed Analysis** | Min: 0.18 Kmph, extreme events | Circulation patterns |
| **Drought Risk Assessment** | 0-100 risk score | Choropleth district map |
| **Weather Forecast** | 90-day predictions | Trend lines, alerts |

### 3. Anomaly Detection
- **Extreme Rainfall**: Events exceeding 2x 7-day rolling average
- **Heat Waves**: Days with max temperature > 45°C
- **Drought Flags**: Low rainfall during monsoon season

### 4. Drought/Crop Risk Score
Composite score (0-100) based on:
- Rainfall deficit (40% weight)
- High temperatures (35% weight)  
- Low humidity (25% weight)

| Risk Level | Score Range | Action |
|------------|-------------|--------|
| 🟢 Low | 0-30 | Normal operations |
| 🟡 Moderate | 30-50 | Monitor closely |
| 🟠 High | 50-70 | Early warning |
| 🔴 Severe | 70-100 | Emergency response |

### 5. Forecasting (90-Day)
- **Rainfall Forecast**: Exponential smoothing with seasonal adjustment
- **Temperature Forecast**: Trend analysis with anomaly detection
- **Alert System**: Color-coded warnings for extreme events

---

## 🔧 Technical Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Raw Data      │     │  Python ETL     │     │   SQLite DB     │
│   (CSV/Excel)   │────▶│  Pipeline       │────▶│   (4 tables)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │  Forecasting    │              │
                        │  Module         │◀─────────────┘
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   Power BI      │
                        │   Dashboard     │
                        └─────────────────┘
```

### Database Schema
| Table | Purpose | Key Fields |
|-------|---------|------------|
| `weather_data` | Daily observations | date, district, temps, rainfall, flags |
| `district_summary` | Aggregated metrics | district, avg rainfall, risk score |
| `monthly_summary` | Monthly rollups | year, month, totals, seasonal |
| `anomaly_events` | Flagged events | date, district, event_type, severity |
| `rainfall_forecast` | 90-day predictions | date, forecast, seasonal_index |
| `temperature_forecast` | 90-day predictions | date, forecast, trend |

### DAX Measures (see `docs/dax_measures.md`)
- Core aggregations (SUM, AVG, MIN, MAX)
- Anomaly detection flags
- Drought risk scoring
- Time intelligence (YoY, YTD, Moving Avg)
- Forecasting metrics

---

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install pandas numpy matplotlib prophet
```

### 2. Run Data Pipeline
```bash
# Clean and load data
python src/data_cleaning.py --input data/raw/weather_data.csv --output data/telangana_weather.db
```

### 3. Generate Forecasts
```python
from src.forecasting import WeatherForecaster

forecaster = WeatherForecaster('data/telangana_weather.db')
summary = forecaster.create_forecast_summary()
print(summary)
```

### 4. Open Power BI
1. Open `TELANGANA DASHBOARD (1).pbix`
2. Connect to `data/telangana_weather.db` using SQLite ODBC driver
3. Refresh all data sources

---

## 💡 Key Insights

### Climate Patterns
- **Monsoon Concentration**: 75% of annual rainfall occurs July-September
- **Temperature Extremes**: Summer highs reach 46.8°C, winter lows drop to 21°C
- **Diurnal Range**: Average 12.73°C variation affects crop water needs

### District Rankings
| Rank | District | Avg Rainfall | Drought Risk | Recommendation |
|------|----------|--------------|--------------|----------------|
| 1 | Nizamabad | 125.8 mm/mo | Low (28) | Continue current agriculture |
| 2 | Warangal | 118.5 mm/mo | Moderate (35) | Monitor soil moisture |
| 3 | Rangareddy | 112.5 mm/mo | Moderate (38) | Diversify crops |
| 4 | Hyderabad | 98.5 mm/mo | High (52) | Water conservation |
| 5 | Nalgonda | 85.5 mm/mo | High (58) | Drought-resistant varieties |

### Anomaly Events (2021-2024)
- **Extreme Rainfall**: 45 events detected (>2x rolling avg)
- **Heat Waves**: 28 days above 45°C
- **Drought Flags**: 15 low-rainfall monsoon periods

### Agricultural Recommendations
1. **Kharif Season (June-Oct)**: Ensure irrigation backup for Nalgonda and Hyderabad
2. **Rabi Season (Nov-Feb)**: Leverage stored monsoon water in Warangal
3. **Heat Mitigation**: Implement shade structures for livestock in high-risk districts
4. **Drought Preparedness**: Create water harvesting structures in Rangareddy

### Policy Implications
- **Water Resource Allocation**: Prioritize Nalgonda for reservoir releases
- **Crop Insurance**: High-risk districts need enhanced coverage
- **Urban Planning**: Hyderabad's high heat requires green infrastructure investment
- **Early Warning System**: Integrate 90-day forecasts into agricultural advisory

---

## 📁 Project Structure

```
telangana-dashboard/
├── src/
│   ├── data_cleaning.py     # ETL pipeline with anomaly detection
│   └── forecasting.py       # Weather forecasting module
├── data/
│   ├── raw/                 # Source data files
│   │   └── sample_weather_data.csv
│   ├── processed/           # Cleaned datasets
│   └── telangana_weather.db # SQLite database
├── docs/
│   ├── dax_measures.md      # Complete DAX documentation
│   └── images/              # Dashboard screenshots
├── POWERBI.pdf              # Original documentation
├── README.md                # This file
└── TELANGANA DASHBOARD (1).pbix
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **BI Tool** | Microsoft Power BI Desktop |
| **Data Source** | District-level historical weather (CSV/Excel) |
| **ETL** | Python (pandas, numpy) |
| **Database** | SQLite |
| **Forecasting** | Prophet, Exponential Smoothing |
| **Documentation** | Markdown, DAX |

---

## 📈 Enhancement Roadmap

- [ ] Add district-level population data for risk impact analysis
- [ ] Integrate satellite imagery for vegetation indices (NDVI)
- [ ] Build automated data ingestion from IMD API
- [ ] Add real-time weather station integration
- [ ] Create mobile-friendly report view
- [ ] Implement R/Python scripting in Power BI for advanced analytics

---

## 👨‍💻 Author

**SAI LAKSHMI RAJULapati**

B.Tech in CSE [DATA SCIENCE]

GitHub: https://github.com/SAI-798

LinkedIn: https://www.linkedin.com/in/sai-lakshmi-rajulapati/

---

## 📄 License

MIT License - Feel free to use and enhance this project.

---

⭐ If you found this project useful, please star the repository!