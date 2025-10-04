"""
Build training dataset from downloaded weather data.
Combines data from multiple locations and applies feature engineering.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

import pandas as pd
import numpy as np
from tqdm import tqdm

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from utils.logging import setup_logging, get_logger

from feature_defs import FeatureDefinitions

logger = get_logger(__name__)


class DatasetBuilder:
    """Build ML training dataset from historical weather data."""
    
    def __init__(self, cache_dir="data/cache", output_dir="data"):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.feature_defs = FeatureDefinitions()
    
    def load_all_location_data(self) -> pd.DataFrame:
        """Load and combine data from all cached locations."""
        logger.info("Loading data from all cached locations")
        
        all_data = []
        cache_files = list(self.cache_dir.glob("historical_*.parquet"))
        
        if not cache_files:
            logger.error("No cached data files found. Run download_data.py first.")
            raise FileNotFoundError("No cached data files found")
        
        logger.info(f"Found {len(cache_files)} cached data files")
        
        for cache_file in tqdm(cache_files, desc="Loading data files"):
            try:
                # Extract location info from filename
                parts = cache_file.stem.split('_')
                if len(parts) >= 4:
                    lat = float(parts[1])
                    lng = float(parts[2])
                    
                    # Load data
                    df = pd.read_parquet(cache_file)
                    df['source_latitude'] = lat
                    df['source_longitude'] = lng
                    df['location_id'] = f"{lat:.2f}_{lng:.2f}"
                    
                    all_data.append(df)
                    logger.debug(f"Loaded {len(df)} records from {cache_file}")
                
            except Exception as e:
                logger.warning(f"Failed to load {cache_file}: {e}")
        
        if not all_data:
            raise ValueError("No valid data files could be loaded")
        
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined dataset: {len(combined_df)} records from {len(all_data)} locations")
        
        return combined_df
    
    def create_forecast_targets(
        self, 
        df: pd.DataFrame, 
        horizons: list = None,
        max_horizon: int = 720
    ) -> pd.DataFrame:
        """
        Create forecast targets for multiple horizons.
        
        Args:
            df: Input weather data (sorted by location and time)
            horizons: List of forecast horizons in hours
            max_horizon: Maximum forecast horizon
            
        Returns:
            DataFrame with targets for each horizon
        """
        if horizons is None:
            # Create targets for multiple horizons (1h to 30 days)
            horizons = [1, 3, 6, 12, 24, 48, 72, 168, 336, 720]
        
        logger.info(f"Creating forecast targets for horizons: {horizons}")
        
        # Sort by location and time
        df = df.sort_values(['location_id', 'datetime']).reset_index(drop=True)
        
        target_columns = []
        
        for horizon in horizons:
            if horizon > max_horizon:
                continue
                
            # Create target columns for this horizon
            precip_target = f'target_precip_{horizon}h'
            precip_binary = f'target_precip_binary_{horizon}h'
            
            # Initialize with NaN
            df[precip_target] = np.nan
            df[precip_binary] = np.nan
            
            # For each location, create targets
            for location_id in df['location_id'].unique():
                mask = df['location_id'] == location_id
                location_data = df.loc[mask, 'precipitation_mm'].values
                
                # Create targets (future precipitation)
                targets = np.concatenate([location_data[horizon:], [np.nan] * horizon])
                binary_targets = (targets > 0.1).astype(float)
                
                df.loc[mask, precip_target] = targets
                df.loc[mask, precip_binary] = binary_targets
            
            target_columns.extend([precip_target, precip_binary])
        
        # Remove rows where we can't make predictions (end of time series)
        valid_mask = ~df[target_columns].isnull().all(axis=1)
        df = df[valid_mask].reset_index(drop=True)
        
        logger.info(f"Created targets for {len(df)} valid samples")
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply comprehensive feature engineering.
        
        Args:
            df: Raw weather data with targets
            
        Returns:
            DataFrame with engineered features
        """
        logger.info("Engineering features...")
        
        # Process each location separately for lagged features
        location_dfs = []
        
        for location_id in tqdm(df['location_id'].unique(), desc="Engineering features by location"):
            location_df = df[df['location_id'] == location_id].copy()
            location_df = location_df.sort_values('datetime')
            
            # Get location coordinates
            lat = location_df['source_latitude'].iloc[0]
            lng = location_df['source_longitude'].iloc[0]
            elevation = 0  # We don't have elevation data in our synthetic dataset
            
            # Add temporal features
            location_df = self.feature_defs.temporal_features(location_df)
            
            # Add location features
            location_df = self.feature_defs.location_features(location_df, lat, lng, elevation)
            
            # Add lagged features (need sorted time series)
            location_df = self.feature_defs.lagged_features(location_df, 'precipitation_mm')
            
            # Add meteorological features
            location_df = self.feature_defs.meteorological_features(location_df)
            
            # Add climatology features (use location's own data as "historical")
            # Split data to avoid lookahead bias
            split_date = location_df['datetime'].quantile(0.7)  # Use first 70% as "history"
            historical_data = location_df[location_df['datetime'] < split_date]
            
            if len(historical_data) > 100:  # Need sufficient historical data
                location_df = self.feature_defs.climatology_features(
                    location_df, historical_data, 'precipitation_mm'
                )
            else:
                # Add default climatology features
                location_df['climatology_precip_mean'] = location_df['precipitation_mm'].mean()
                location_df['climatology_precip_std'] = location_df['precipitation_mm'].std()
                location_df['climatology_precip_prob'] = (location_df['precipitation_mm'] > 0.1).mean()
                location_df['climatology_precip_p75'] = location_df['precipitation_mm'].quantile(0.75)
                location_df['climatology_precip_p90'] = location_df['precipitation_mm'].quantile(0.90)
            
            # Add anomaly features
            location_df = self.feature_defs.anomaly_features(
                location_df, historical_data, 
                ['precipitation_mm', 'temperature_c', 'humidity_percent', 'pressure_hpa']
            )
            
            location_dfs.append(location_df)
        
        # Combine all locations
        final_df = pd.concat(location_dfs, ignore_index=True)
        
        logger.info(f"Feature engineering complete. Dataset shape: {final_df.shape}")
        
        return final_df
    
    def create_train_test_splits(
        self, 
        df: pd.DataFrame,
        test_size: float = 0.2,
        val_size: float = 0.1
    ) -> tuple:
        """
        Create train/validation/test splits ensuring no temporal leakage.
        
        Args:
            df: Complete dataset
            test_size: Fraction for test set
            val_size: Fraction for validation set
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        logger.info("Creating train/validation/test splits...")
        
        # Sort by time globally
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Split by time to avoid leakage
        n_samples = len(df)
        
        # Calculate split indices
        test_start = int(n_samples * (1 - test_size))
        val_start = int(n_samples * (1 - test_size - val_size))
        
        train_df = df[:val_start].copy()
        val_df = df[val_start:test_start].copy()
        test_df = df[test_start:].copy()
        
        logger.info(f"Data splits:")
        logger.info(f"  Train: {len(train_df)} samples ({len(train_df)/n_samples:.1%})")
        logger.info(f"  Val:   {len(val_df)} samples ({len(val_df)/n_samples:.1%})")
        logger.info(f"  Test:  {len(test_df)} samples ({len(test_df)/n_samples:.1%})")
        
        # Log date ranges
        logger.info(f"Date ranges:")
        logger.info(f"  Train: {train_df['datetime'].min()} to {train_df['datetime'].max()}")
        logger.info(f"  Val:   {val_df['datetime'].min()} to {val_df['datetime'].max()}")
        logger.info(f"  Test:  {test_df['datetime'].min()} to {test_df['datetime'].max()}")
        
        return train_df, val_df, test_df
    
    def save_datasets(
        self, 
        train_df: pd.DataFrame, 
        val_df: pd.DataFrame, 
        test_df: pd.DataFrame
    ):
        """Save processed datasets to disk."""
        logger.info("Saving datasets...")
        
        # Save as parquet (efficient) and CSV (readable)
        train_df.to_parquet(self.output_dir / "train_dataset.parquet", index=False)
        val_df.to_parquet(self.output_dir / "val_dataset.parquet", index=False)
        test_df.to_parquet(self.output_dir / "test_dataset.parquet", index=False)
        
        # Save smaller CSV files for inspection
        train_df.sample(min(10000, len(train_df))).to_csv(
            self.output_dir / "train_sample.csv", index=False
        )
        val_df.to_csv(self.output_dir / "val_dataset.csv", index=False)
        test_df.to_csv(self.output_dir / "test_dataset.csv", index=False)
        
        # Save feature information
        feature_info = {
            'feature_columns': [col for col in train_df.columns 
                              if col not in ['datetime', 'location_id', 'source_latitude', 
                                           'source_longitude', 'precipitation_mm'] 
                              and not col.startswith('target_')],
            'target_columns': [col for col in train_df.columns if col.startswith('target_')],
            'metadata_columns': ['datetime', 'location_id', 'source_latitude', 'source_longitude'],
            'dataset_stats': {
                'n_locations': train_df['location_id'].nunique(),
                'date_range': f"{train_df['datetime'].min()} to {test_df['datetime'].max()}",
                'n_features': len([col for col in train_df.columns 
                                 if col not in ['datetime', 'location_id', 'source_latitude', 
                                              'source_longitude', 'precipitation_mm'] 
                                 and not col.startswith('target_')]),
                'train_samples': len(train_df),
                'val_samples': len(val_df),
                'test_samples': len(test_df)
            }
        }
        
        import json
        with open(self.output_dir / "dataset_info.json", 'w') as f:
            json.dump(feature_info, f, indent=2, default=str)
        
        logger.info(f"Datasets saved to {self.output_dir}")
        logger.info(f"Feature info saved with {len(feature_info['feature_columns'])} features")
    
    def build_complete_dataset(self):
        """Build the complete ML dataset from scratch."""
        logger.info("Building complete ML dataset...")
        
        # Load all location data
        df = self.load_all_location_data()
        
        # Create forecast targets
        df = self.create_forecast_targets(df)
        
        # Engineer features
        df = self.engineer_features(df)
        
        # Remove rows with too many missing features (due to lags)
        initial_rows = len(df)
        # Keep only rows where we have sufficient lagged features
        df = df.dropna(subset=['precipitation_mm_lag_24h', 'precipitation_mm_sum_24h'])
        logger.info(f"Dropped {initial_rows - len(df)} rows due to insufficient lagged features")
        
        # Create train/val/test splits
        train_df, val_df, test_df = self.create_train_test_splits(df)
        
        # Save datasets
        self.save_datasets(train_df, val_df, test_df)
        
        logger.info("Dataset building complete!")
        
        return train_df, val_df, test_df


def main():
    """Main function to build the dataset."""
    setup_logging()
    
    builder = DatasetBuilder()
    
    try:
        train_df, val_df, test_df = builder.build_complete_dataset()
        
        logger.info("Success! Dataset built and saved.")
        logger.info(f"Ready for training with {len(train_df)} training samples")
        
    except Exception as e:
        logger.error(f"Dataset building failed: {e}")
        raise


if __name__ == "__main__":
    main()