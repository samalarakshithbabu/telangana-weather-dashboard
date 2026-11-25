"""
Weather Forecasting Module
===========================
Provides forecasting capabilities for rainfall and temperature using Prophet
and statistical methods. Integrates with the cleaned SQL database.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WeatherForecaster:
    """Forecasting class for weather predictions."""
    
    def __init__(self, db_path: str = 'telangana_weather.db'):
        self.db_path = db_path
        self.models = {}
        self.forecasts = {}
    
    def load_data(self, query: str = None) -> pd.DataFrame:
        """Load weather data from SQL database."""
        conn = sqlite3.connect(self.db_path)
        
        if query is None:
            query = """
                SELECT date, district, max_temp, min_temp, rainfall_mm, humidity_pct
                FROM weather_data 
                ORDER BY date, district
            """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        logger.info(f"Loaded {len(df)} records from database")
        return df
    
    def prepare_prophet_data(self, df: pd.DataFrame, 
                             target: str = 'rainfall_mm') -> pd.DataFrame:
        """Prepare data for Prophet forecasting."""
        prophet_df = df.groupby('date')[target].sum().reset_index()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
        return prophet_df
    
    def simple_exponential_smoothing(self, series: pd.Series, 
                                     alpha: float = 0.3,
                                     periods: int = 30) -> list:
        """
        Simple exponential smoothing for forecasting.
        
        Args:
            series: Historical data series
            alpha: Smoothing factor (0-1)
            periods: Number of periods to forecast
        
        Returns:
            List of forecast values
        """
        # Fit model
        level = series.iloc[0]
        fitted = [level]
        
        for value in series.iloc[1:]:
            level = alpha * value + (1 - alpha) * level
            fitted.append(level)
        
        # Forecast
        forecast = []
        last_level = level
        
        for _ in range(periods):
            last_level = alpha * last_level + (1 - alpha) * last_level
            forecast.append(last_level)
        
        return forecast
    
    def calculate_trend(self, series: pd.Series) -> float:
        """Calculate linear trend (slope) of a series."""
        x = np.arange(len(series))
        y = series.values
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    def detect_seasonality(self, df: pd.DataFrame, 
                          target: str = 'rainfall_mm') -> dict:
        """Detect seasonal patterns in the data."""
        df = df.copy()
        
        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        df['month'] = df['date'].dt.month
        
        # Calculate monthly averages
        monthly_avg = df.groupby('month')[target].mean()
        
        # Calculate seasonal indices
        overall_avg = df[target].mean()
        seasonal_indices = (monthly_avg / overall_avg).to_dict()
        
        # Identify peak and low seasons
        peak_month = max(seasonal_indices, key=seasonal_indices.get)
        low_month = min(seasonal_indices, key=seasonal_indices.get)
        
        return {
            'monthly_averages': monthly_avg.to_dict(),
            'seasonal_indices': seasonal_indices,
            'peak_month': int(peak_month),
            'low_month': int(low_month),
            'seasonality_strength': max(seasonal_indices.values()) / max(min(seasonal_indices.values()), 0.01)
        }
    
    def forecast_rainfall(self, df: pd.DataFrame, 
                          periods: int = 90) -> pd.DataFrame:
        """Generate rainfall forecast."""
        # Aggregate daily rainfall
        daily_rainfall = df.groupby('date')['rainfall_mm'].sum().reset_index()
        daily_rainfall.columns = ['date', 'rainfall']
        daily_rainfall = daily_rainfall.sort_values('date')
        
        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(daily_rainfall['date']):
            daily_rainfall['date'] = pd.to_datetime(daily_rainfall['date'], errors='coerce')
            daily_rainfall = daily_rainfall.dropna(subset=['date'])
        
        # Detect seasonality
        seasonality = self.detect_seasonality(df, 'rainfall_mm')
        logger.info(f"Rainfall seasonality detected - Peak: Month {seasonality['peak_month']}")
        
        # Calculate trend
        trend = self.calculate_trend(daily_rainfall.set_index('date')['rainfall'])
        
        # Simple exponential smoothing forecast
        forecast_values = self.simple_exponential_smoothing(
            daily_rainfall['rainfall'],
            alpha=0.3,
            periods=periods
        )
        
        # Generate future dates
        last_date = daily_rainfall['date'].max()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), 
                                      periods=periods, freq='D')
        
        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'date': future_dates,
            'forecast_rainfall': forecast_values,
            'trend_contribution': [trend * i for i in range(1, periods + 1)],
            'seasonal_index': [seasonality['seasonal_indices'].get(d.month, 1.0) 
                              for d in future_dates]
        })
        
        # Adjust for seasonality
        forecast_df['adjusted_forecast'] = (
            forecast_df['forecast_rainfall'] * forecast_df['seasonal_index']
        )
        
        self.forecasts['rainfall'] = forecast_df
        logger.info(f"Generated {periods}-day rainfall forecast")
        
        return forecast_df
    
    def forecast_temperature(self, df: pd.DataFrame, 
                             periods: int = 90) -> pd.DataFrame:
        """Generate temperature forecast."""
        # Aggregate daily max temperature
        daily_temp = df.groupby('date')['max_temp'].mean().reset_index()
        daily_temp.columns = ['date', 'max_temp']
        daily_temp = daily_temp.sort_values('date')
        
        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(daily_temp['date']):
            daily_temp['date'] = pd.to_datetime(daily_temp['date'], errors='coerce')
            daily_temp = daily_temp.dropna(subset=['date'])
        
        # Detect seasonality
        seasonality = self.detect_seasonality(df, 'max_temp')
        logger.info(f"Temperature seasonality detected - Peak: Month {seasonality['peak_month']}")
        
        # Calculate trend
        trend = self.calculate_trend(daily_temp.set_index('date')['max_temp'])
        
        # Forecast using exponential smoothing
        forecast_values = self.simple_exponential_smoothing(
            daily_temp['max_temp'],
            alpha=0.3,
            periods=periods
        )
        
        # Generate future dates
        last_date = daily_temp['date'].max()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), 
                                      periods=periods, freq='D')
        
        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'date': future_dates,
            'forecast_max_temp': forecast_values,
            'trend_contribution': [trend * i for i in range(1, periods + 1)],
            'seasonal_index': [seasonality['seasonal_indices'].get(d.month, 1.0) 
                              for d in future_dates]
        })
        
        # Adjust for seasonality
        forecast_df['adjusted_forecast'] = (
            forecast_df['forecast_max_temp'] * forecast_df['seasonal_index']
        )
        
        self.forecasts['temperature'] = forecast_df
        logger.info(f"Generated {periods}-day temperature forecast")
        
        return forecast_df
    
    def generate_heat_wave_alert(self, forecast_df: pd.DataFrame, 
                                  threshold: float = 45) -> dict:
        """Generate heat wave alerts from forecast data."""
        # Check if using renamed dataframe or original
        col = 'adjusted_forecast' if 'adjusted_forecast' in forecast_df.columns else 'forecast_max_temp'
        extreme_days = forecast_df[forecast_df[col] > threshold]
        
        if len(extreme_days) == 0:
            return {'alert_level': 'None', 'days_at_risk': 0}
        
        alert_level = 'Orange' if len(extreme_days) <= 5 else 'Red'
        
        return {
            'alert_level': alert_level,
            'days_at_risk': len(extreme_days),
            'first_extreme_date': extreme_days['date'].min().strftime('%Y-%m-%d'),
            'max_forecasted_temp': extreme_days[col].max(),
            'affected_districts': []
        }
    
    def generate_rainfall_alert(self, forecast_df: pd.DataFrame, 
                                 threshold: float = 100) -> dict:
        """Generate heavy rainfall alerts from forecast data."""
        # Check if using renamed dataframe or original
        col = 'adjusted_forecast' if 'adjusted_forecast' in forecast_df.columns else 'forecast_rainfall'
        heavy_rain_days = forecast_df[forecast_df[col] > threshold]
        
        if len(heavy_rain_days) == 0:
            return {'alert_level': 'None', 'days_at_risk': 0}
        
        alert_level = 'Yellow' if len(heavy_rain_days) <= 2 else 'Orange'
        
        return {
            'alert_level': alert_level,
            'days_at_risk': len(heavy_rain_days),
            'first_heavy_date': heavy_rain_days['date'].min().strftime('%Y-%m-%d'),
            'max_forecasted_rainfall': heavy_rain_days[col].max()
        }
    
    def create_forecast_summary(self, district: str = None) -> dict:
        """Create a summary of forecast for dashboard."""
        summary = {
            'generated_at': datetime.now().isoformat(),
            'forecast_period_days': 90,
            'district': district or 'All Districts'
        }
        
        # Get appropriate data
        conn = sqlite3.connect(self.db_path)
        
        if district:
            query = f"""
                SELECT * FROM weather_data 
                WHERE district = '{district}'
                ORDER BY date
            """
        else:
            query = "SELECT * FROM weather_data ORDER BY date"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) == 0:
            return {'error': 'No data available'}
        
        # Generate forecasts
        rainfall_forecast = self.forecast_rainfall(df)
        temp_forecast = self.forecast_temperature(df)
        
        # Generate alerts
        summary['heat_wave_alert'] = self.generate_heat_wave_alert(
            temp_forecast.copy()
        )
        
        summary['rainfall_alert'] = self.generate_rainfall_alert(
            rainfall_forecast.copy()
        )
        
        # Key metrics
        summary['key_metrics'] = {
            'avg_forecast_rainfall': round(rainfall_forecast['adjusted_forecast'].mean(), 2),
            'max_forecast_temp': round(temp_forecast['adjusted_forecast'].max(), 2),
            'min_forecast_temp': round(temp_forecast['adjusted_forecast'].min(), 2)
        }
        
        # Seasonal outlook
        summary['seasonal_outlook'] = {
            'rainfall_trend': 'Increasing' if self.calculate_trend(
                df.groupby('date')['rainfall_mm'].sum()
            ) > 0 else 'Decreasing',
            'temp_trend': 'Warming' if self.calculate_trend(
                df.groupby('date')['max_temp'].mean()
            ) > 0 else 'Cooling'
        }
        
        return summary
    
    def export_forecasts_to_sql(self, conn: sqlite3.Connection):
        """Export forecasts to SQL database for Power BI consumption."""
        cursor = conn.cursor()
        
        # Create forecast tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rainfall_forecast (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                forecast_rainfall FLOAT,
                trend_contribution FLOAT,
                seasonal_index FLOAT,
                adjusted_forecast FLOAT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temperature_forecast (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                forecast_max_temp FLOAT,
                trend_contribution FLOAT,
                seasonal_index FLOAT,
                adjusted_forecast FLOAT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forecast_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at TIMESTAMP,
                forecast_period_days INTEGER,
                alert_level TEXT,
                days_at_risk INTEGER,
                district TEXT
            )
        ''')
        
        # Export rainfall forecast
        if 'rainfall' in self.forecasts:
            self.forecasts['rainfall'].to_sql(
                'rainfall_forecast', conn, 
                if_exists='replace', index=False
            )
        
        # Export temperature forecast
        if 'temperature' in self.forecasts:
            self.forecasts['temperature'].to_sql(
                'temperature_forecast', conn, 
                if_exists='replace', index=False
            )
        
        conn.commit()
        logger.info("Forecasts exported to SQL database")
    
    def export_forecast_json(self, filepath: str = 'forecasts.json'):
        """Export forecast summary as JSON for documentation."""
        summary = self.create_forecast_summary()
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Forecast summary exported to {filepath}")
        return summary


# Example usage
if __name__ == "__main__":
    forecaster = WeatherForecaster()
    
    # Load data from database
    # df = forecaster.load_data()
    
    # Generate forecasts
    # rainfall_forecast = forecaster.forecast_rainfall(df)
    # temp_forecast = forecaster.forecast_temperature(df)
    
    # Create summary
    # summary = forecaster.create_forecast_summary()
    
    print("Weather Forecaster Ready")
    print("Usage: forecaster.create_forecast_summary()")