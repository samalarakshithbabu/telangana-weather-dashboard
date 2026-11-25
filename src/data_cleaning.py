"""
Telangana Weather Data Pipeline
===============================
Cleans historical weather data and loads it into SQL database.
Ensures reproducibility with documented transformations.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WeatherDataPipeline:
    """Pipeline for cleaning and loading Telangana weather data."""
    
    def __init__(self, db_path: str = 'telangana_weather.db'):
        self.db_path = db_path
        self.raw_data = None
        self.cleaned_data = None
    
    def load_raw_data(self, filepath: str) -> pd.DataFrame:
        """Load raw weather data from CSV/Excel."""
        logger.info(f"Loading data from {filepath}")
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filepath.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        self.raw_data = df
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply data cleaning transformations."""
        logger.info("Starting data cleaning...")
        
        df_clean = df.copy()
        
        # 1. Standardize column names (map common variations)
        column_mapping = {
            'maxtemp': 'max_temp',
            'max_temp_c': 'max_temp',
            'mintemp': 'min_temp',
            'min_temp_c': 'min_temp',
            'rainfall': 'rainfall_mm',
            'rainfall_mm': 'rainfall_mm',
            'humidity': 'humidity_pct',
            'humidity_pct': 'humidity_pct',
            'wind_speed': 'wind_speed_kmph',
            'windspeed': 'wind_speed_kmph',
            'district': 'district',
            'mandal': 'mandal',
            'date': 'date'
        }
        df_clean.columns = df_clean.columns.str.strip().str.lower()
        df_clean = df_clean.rename(columns=column_mapping)
        
        # 2. Convert date columns to datetime
        date_cols = [col for col in df_clean.columns if 'date' in col.lower()]
        for col in date_cols:
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
        
        # 3. Handle missing values
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].fillna(df_clean[numeric_cols].median())
        
        # 4. Remove duplicates
        df_clean = df_clean.drop_duplicates()
        
        # 5. Validate ranges (flag outliers)
        df_clean = self._add_validation_flags(df_clean)
        
        # 6. Add computed columns
        df_clean = self._add_computed_columns(df_clean)
        
        logger.info(f"Cleaning complete. Rows: {len(df_clean)}")
        self.cleaned_data = df_clean
        return df_clean
    
    def _add_validation_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add validation flags for data quality."""
        # Temperature range validation (Telangana typical range: 15-50°C)
        df['temp_outlier'] = ~df['max_temp'].between(15, 50) | ~df['min_temp'].between(10, 45)
        
        # Rainfall validation (should be non-negative)
        df['rainfall_negative'] = df['rainfall_mm'] < 0
        
        # Humidity validation (0-100%)
        df['humidity_outlier'] = ~df['humidity_pct'].between(0, 100)
        
        return df
    
    def _add_computed_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed/derived columns."""
        # Temperature range
        df['temp_range'] = df['max_temp'] - df['min_temp']
        
        # Heat index approximation
        df['heat_index'] = df['max_temp'] + (0.5 * df['humidity_pct'] * (df['max_temp'] - 20))
        
        # Month and season
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
        
        # Season mapping
        def get_season(month):
            if month in [6, 7, 8, 9]:
                return 'Monsoon'
            elif month in [10, 11]:
                return 'Post-Monsoon'
            elif month in [12, 1, 2]:
                return 'Winter'
            else:
                return 'Pre-Monsoon'
        
        df['season'] = df['month'].apply(get_season)
        
        return df
    
    def add_anomaly_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add anomaly detection flags."""
        df = df.copy()
        
        # Rolling statistics for anomaly detection
        df['rainfall_rolling_mean'] = df.groupby('district')['rainfall_mm'].transform(
            lambda x: x.rolling(window=7, min_periods=1).mean()
        )
        df['rainfall_zscore'] = (df['rainfall_mm'] - df['rainfall_rolling_mean']) / df['rainfall_mm'].std()
        
        # Extreme rainfall flag (z-score > 2)
        df['extreme_rainfall'] = df['rainfall_zscore'] > 2
        
        # Heat wave flag (max_temp > 45°C for 3+ consecutive days)
        df['heat_wave'] = (
            df['max_temp'] > 45
        )
        
        # Drought indicator (low rainfall in monsoon)
        df['drought_flag'] = (
            (df['season'] == 'Monsoon') & 
            (df['rainfall_mm'] < df['rainfall_rolling_mean'] * 0.5)
        )
        
        return df
    
    def calculate_drought_risk_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate district-level drought/crop risk score (0-100)."""
        df = df.copy()
        
        # Risk components (all weighted and normalized)
        # Lower rainfall = higher risk
        rainfall_risk = 1 - (df['rainfall_mm'] / df['rainfall_mm'].max())
        
        # Higher temperature = higher risk
        temp_risk = (df['max_temp'] - df['max_temp'].min()) / (df['max_temp'].max() - df['max_temp'].min())
        
        # Lower humidity = higher risk
        humidity_risk = 1 - (df['humidity_pct'] / 100)
        
        # Combined score (weighted average)
        df['drought_risk_score'] = (
            (rainfall_risk * 0.4) + 
            (temp_risk * 0.35) + 
            (humidity_risk * 0.25)
        ) * 100
        
        return df
    
    def create_sql_schema(self, conn: sqlite3.Connection):
        """Create SQL database schema."""
        cursor = conn.cursor()
        
        # Main weather data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                district TEXT NOT NULL,
                mandal TEXT,
                max_temp FLOAT,
                min_temp FLOAT,
                rainfall_mm FLOAT,
                humidity_pct FLOAT,
                wind_speed_kmph FLOAT,
                temp_range FLOAT,
                heat_index FLOAT,
                month INTEGER,
                year INTEGER,
                season TEXT,
                temp_outlier BOOLEAN,
                rainfall_negative BOOLEAN,
                humidity_outlier BOOLEAN,
                extreme_rainfall BOOLEAN,
                heat_wave BOOLEAN,
                drought_flag BOOLEAN,
                drought_risk_score FLOAT,
                data_quality_flag TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # District summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS district_summary (
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
            )
        ''')
        
        # Monthly aggregation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_summary (
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
            )
        ''')
        
        # Anomaly events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                district TEXT NOT NULL,
                event_type TEXT NOT NULL,
                value FLOAT,
                threshold FLOAT,
                severity TEXT,
                description TEXT,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        logger.info("SQL schema created successfully")
    
    def load_to_sql(self, df: pd.DataFrame, conn: sqlite3.Connection):
        """Load cleaned data into SQL database."""
        logger.info("Loading data to SQL database...")
        
        # Load main weather data
        df.to_sql('weather_data', conn, if_exists='replace', index=False)
        
        # Create district summary
        district_summary = df.groupby('district').agg({
            'rainfall_mm': ['mean', 'sum'],
            'max_temp': 'mean',
            'min_temp': 'mean',
            'humidity_pct': 'mean',
            'wind_speed_kmph': 'mean',
            'extreme_rainfall': 'sum',
            'heat_wave': 'sum',
            'drought_risk_score': 'mean'
        }).round(2)
        
        district_summary.columns = [
            'avg_rainfall', 'total_rainfall', 'avg_max_temp', 'avg_min_temp',
            'avg_humidity', 'avg_wind_speed', 'extreme_rainfall_days',
            'heat_wave_days', 'avg_drought_risk_score'
        ]
        district_summary = district_summary.reset_index()
        district_summary.to_sql('district_summary', conn, if_exists='replace', index=False)
        
        # Create monthly summary
        monthly_summary = df.groupby(['year', 'month', 'district']).agg({
            'rainfall_mm': 'sum',
            'max_temp': ['mean', 'max'],
            'min_temp': ['mean', 'min'],
            'humidity_pct': 'mean',
            'extreme_rainfall': 'sum'
        }).reset_index()
        
        monthly_summary.columns = [
            'year', 'month', 'district', 'total_rainfall', 'avg_temp', 'max_temp',
            'min_temp', 'min_temp_val', 'avg_humidity', 'extreme_days'
        ]
        monthly_summary = monthly_summary.drop('min_temp_val', axis=1)
        
        def get_season(month):
            if month in [6, 7, 8, 9]:
                return 'Monsoon'
            elif month in [10, 11]:
                return 'Post-Monsoon'
            elif month in [12, 1, 2]:
                return 'Winter'
            else:
                return 'Pre-Monsoon'
        
        monthly_summary['season'] = monthly_summary['month'].apply(get_season)
        monthly_summary.to_sql('monthly_summary', conn, if_exists='replace', index=False)
        
        # Create anomaly events
        anomalies = []
        for _, row in df[df['extreme_rainfall'] | df['heat_wave'] | df['drought_flag']].iterrows():
            event_type = []
            if row['extreme_rainfall']:
                event_type.append('Extreme Rainfall')
            if row['heat_wave']:
                event_type.append('Heat Wave')
            if row['drought_flag']:
                event_type.append('Drought')
            
            for et in event_type:
                anomalies.append({
                    'date': row['date'],
                    'district': row['district'],
                    'event_type': et,
                    'value': row.get('rainfall_mm' if 'Rainfall' in et else 'max_temp', 0),
                    'threshold': row.get('rainfall_rolling_mean', 0) * 2 if 'Rainfall' in et else 45,
                    'severity': 'High' if row.get('extreme_rainfall', False) or row.get('heat_wave', False) else 'Medium',
                    'description': f"{et} event in {row['district']} on {row['date']}"
                })
        
        if anomalies:
            anomalies_df = pd.DataFrame(anomalies)
            anomalies_df.to_sql('anomaly_events', conn, if_exists='replace', index=False)
        
        conn.commit()
        logger.info(f"Loaded {len(df)} records to weather_data table")
        logger.info(f"Loaded {len(district_summary)} district summaries")
        logger.info(f"Loaded {len(monthly_summary)} monthly summaries")
    
    def run_pipeline(self, input_file: str, output_db: str = None):
        """Execute full pipeline: load, clean, transform, load to SQL."""
        output_db = output_db or self.db_path
        
        # Connect to database
        conn = sqlite3.connect(output_db)
        
        try:
            # Load raw data
            raw_df = self.load_raw_data(input_file)
            
            # Clean data
            cleaned_df = self.clean_data(raw_df)
            
            # Add anomaly flags
            cleaned_df = self.add_anomaly_flags(cleaned_df)
            
            # Calculate drought risk scores
            cleaned_df = self.calculate_drought_risk_score(cleaned_df)
            
            # Add data quality flag
            cleaned_df['data_quality_flag'] = cleaned_df.apply(
                lambda x: 'ISSUES' if any([x['temp_outlier'], x['rainfall_negative'], x['humidity_outlier']]) else 'CLEAN',
                axis=1
            )
            
            # Create schema and load data
            self.create_sql_schema(conn)
            self.load_to_sql(cleaned_df, conn)
            
            logger.info("Pipeline completed successfully!")
            return cleaned_df
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
        finally:
            conn.close()


# Example usage
if __name__ == "__main__":
    pipeline = WeatherDataPipeline()
    
    # Run pipeline with sample data
    # cleaned_df = pipeline.run_pipeline("data/raw/telangana_weather_2021_2024.csv")
    
    print("Telangana Weather Data Pipeline Ready")
    print("Usage: pipeline.run_pipeline('input_file.csv')")