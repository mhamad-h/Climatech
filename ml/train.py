"""
Train precipitation forecasting models.
Implements baseline models and gradient boosted trees.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import pickle
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from tqdm import tqdm

# ML libraries
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, roc_auc_score, brier_score_loss
from sklearn.dummy import DummyClassifier, DummyRegressor
import lightgbm as lgb
import xgboost as xgb

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


class BaselineModels:
    """Baseline models for precipitation forecasting."""
    
    def __init__(self):
        self.models = {}
    
    def train_climatology(self, train_df: pd.DataFrame, targets: list):
        """Train climatology baseline (long-term averages by time of year)."""
        logger.info("Training climatology baseline...")
        
        for target in targets:
            if 'binary' in target:
                # For binary targets, use probability of precipitation
                model = DummyClassifier(strategy='prior')
                y = train_df[target].dropna()
                if len(y) > 0:
                    model.fit(np.zeros((len(y), 1)), y)
                    self.models[f'climatology_{target}'] = model
                    logger.info(f"Climatology for {target}: P(precip) = {y.mean():.3f}")
            else:
                # For continuous targets, use mean precipitation
                model = DummyRegressor(strategy='mean')
                y = train_df[target].dropna()
                if len(y) > 0:
                    model.fit(np.zeros((len(y), 1)), y)
                    self.models[f'climatology_{target}'] = model
                    logger.info(f"Climatology for {target}: mean = {y.mean():.3f} mm")
    
    def train_persistence(self, train_df: pd.DataFrame, targets: list):
        """Train persistence baseline (use current conditions)."""
        logger.info("Training persistence baseline...")
        
        for target in targets:
            # Persistence uses current precipitation value
            if 'binary' in target:
                # Use current binary precipitation state
                current_precip = (train_df['precipitation_mm'] > 0.1).astype(float)
            else:
                # Use current precipitation amount
                current_precip = train_df['precipitation_mm']
            
            # Simple persistence model
            class PersistenceModel:
                def __init__(self, strategy='binary' if 'binary' in target else 'continuous'):
                    self.strategy = strategy
                
                def predict(self, X):
                    # X should contain current precipitation
                    if self.strategy == 'binary':
                        return (X[:, 0] > 0.1).astype(float)
                    else:
                        return X[:, 0]
                
                def predict_proba(self, X):
                    probs = (X[:, 0] > 0.1).astype(float)
                    return np.column_stack([1 - probs, probs])
            
            self.models[f'persistence_{target}'] = PersistenceModel()
    
    def predict(self, model_name: str, X: np.ndarray) -> np.ndarray:
        """Make predictions with a baseline model."""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        model = self.models[model_name]
        
        if hasattr(model, 'predict'):
            return model.predict(X)
        else:
            raise ValueError(f"Model {model_name} doesn't have predict method")


class GradientBoostedModels:
    """Gradient boosted tree models for precipitation forecasting."""
    
    def __init__(self):
        self.models = {}
        self.feature_importance = {}
    
    def get_lgb_params(self, is_binary: bool = False) -> dict:
        """Get LightGBM parameters."""
        params = {
            'boosting_type': 'gbdt',
            'num_leaves': 100,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42,
            'n_estimators': 500,
            'early_stopping_rounds': 50
        }
        
        if is_binary:
            params.update({
                'objective': 'binary',
                'metric': 'auc',
                'is_unbalance': True
            })
        else:
            params.update({
                'objective': 'regression',
                'metric': 'rmse'
            })
        
        return params
    
    def get_xgb_params(self, is_binary: bool = False) -> dict:
        """Get XGBoost parameters."""
        params = {
            'max_depth': 8,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_estimators': 500
        }
        
        if is_binary:
            params.update({
                'objective': 'binary:logistic',
                'eval_metric': 'auc'
            })
        else:
            params.update({
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse'
            })
        
        return params
    
    def train_model(
        self, 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        target_name: str,
        model_type: str = 'lightgbm'
    ):
        """Train a gradient boosted model."""
        logger.info(f"Training {model_type} for {target_name}...")
        
        is_binary = 'binary' in target_name
        
        if model_type == 'lightgbm':
            params = self.get_lgb_params(is_binary)
            
            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            
            model = lgb.train(
                params,
                train_data,
                valid_sets=[val_data],
                callbacks=[lgb.log_evaluation(0)]  # Silent training
            )
            
        elif model_type == 'xgboost':
            params = self.get_xgb_params(is_binary)
            
            model = xgb.XGBRegressor(**params) if not is_binary else xgb.XGBClassifier(**params)
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Store model and feature importance
        model_key = f"{model_type}_{target_name}"
        self.models[model_key] = model
        
        # Get feature importance
        if model_type == 'lightgbm':
            importance = model.feature_importance(importance_type='gain')
            feature_names = X_train.columns
        else:
            importance = model.feature_importances_
            feature_names = X_train.columns
        
        self.feature_importance[model_key] = dict(zip(feature_names, importance))
        
        logger.info(f"Trained {model_key} successfully")
        
        return model
    
    def predict(self, model_name: str, X: pd.DataFrame) -> np.ndarray:
        """Make predictions with a trained model."""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        model = self.models[model_name]
        
        if 'binary' in model_name:
            # For binary classification, return probabilities
            if isinstance(model, lgb.Booster):
                return model.predict(X)
            else:
                return model.predict_proba(X)[:, 1]
        else:
            # For regression, return predictions
            if isinstance(model, lgb.Booster):
                return model.predict(X)
            else:
                return model.predict(X)


class ModelTrainer:
    """Main model training orchestrator."""
    
    def __init__(self, data_dir: str = "data", models_dir: str = "models"):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        self.baseline_models = BaselineModels()
        self.gb_models = GradientBoostedModels()
        
        self.training_results = {}
    
    def load_datasets(self):
        """Load train/validation/test datasets."""
        logger.info("Loading datasets...")
        
        self.train_df = pd.read_parquet(self.data_dir / "train_dataset.parquet")
        self.val_df = pd.read_parquet(self.data_dir / "val_dataset.parquet")
        self.test_df = pd.read_parquet(self.data_dir / "test_dataset.parquet")
        
        # Load feature info
        with open(self.data_dir / "dataset_info.json", 'r') as f:
            self.dataset_info = json.load(f)
        
        self.feature_columns = self.dataset_info['feature_columns']
        self.target_columns = self.dataset_info['target_columns']
        
        logger.info(f"Loaded datasets:")
        logger.info(f"  Features: {len(self.feature_columns)}")
        logger.info(f"  Targets: {len(self.target_columns)}")
        logger.info(f"  Train: {len(self.train_df)} samples")
        logger.info(f"  Val: {len(self.val_df)} samples")
        logger.info(f"  Test: {len(self.test_df)} samples")
    
    def prepare_data(self):
        """Prepare feature matrices and target vectors."""
        logger.info("Preparing data for training...")
        
        # Feature matrices
        self.X_train = self.train_df[self.feature_columns].fillna(0)
        self.X_val = self.val_df[self.feature_columns].fillna(0)
        self.X_test = self.test_df[self.feature_columns].fillna(0)
        
        logger.info(f"Feature matrix shape: {self.X_train.shape}")
        
        # Target vectors (will iterate through each target)
        self.targets_train = {}
        self.targets_val = {}
        self.targets_test = {}
        
        for target in self.target_columns:
            self.targets_train[target] = self.train_df[target].fillna(0)
            self.targets_val[target] = self.val_df[target].fillna(0)  
            self.targets_test[target] = self.test_df[target].fillna(0)
    
    def train_baselines(self):
        """Train baseline models."""
        logger.info("Training baseline models...")
        
        # Train climatology and persistence baselines
        self.baseline_models.train_climatology(self.train_df, self.target_columns)
        self.baseline_models.train_persistence(self.train_df, self.target_columns)
        
        logger.info("Baseline models trained successfully")
    
    def train_gradient_boosted(self):
        """Train gradient boosted models."""
        logger.info("Training gradient boosted models...")
        
        for target in tqdm(self.target_columns, desc="Training GB models"):
            # Get target data (remove NaN values)
            mask_train = ~self.targets_train[target].isna()
            mask_val = ~self.targets_val[target].isna()
            
            if mask_train.sum() < 100 or mask_val.sum() < 10:
                logger.warning(f"Insufficient data for target {target}, skipping")
                continue
            
            X_train_target = self.X_train[mask_train]
            y_train_target = self.targets_train[target][mask_train]
            X_val_target = self.X_val[mask_val]  
            y_val_target = self.targets_val[target][mask_val]
            
            # Train LightGBM
            try:
                self.gb_models.train_model(
                    X_train_target, y_train_target,
                    X_val_target, y_val_target,
                    target, 'lightgbm'
                )
            except Exception as e:
                logger.error(f"LightGBM training failed for {target}: {e}")
            
            # Train XGBoost
            try:
                self.gb_models.train_model(
                    X_train_target, y_train_target,
                    X_val_target, y_val_target,
                    target, 'xgboost'
                )
            except Exception as e:
                logger.error(f"XGBoost training failed for {target}: {e}")
        
        logger.info("Gradient boosted models trained successfully")
    
    def evaluate_models(self):
        """Evaluate all trained models."""
        logger.info("Evaluating models...")
        
        results = {}
        
        for target in self.target_columns:
            target_results = {}
            
            # Get test data for this target
            mask_test = ~self.targets_test[target].isna()
            if mask_test.sum() < 10:
                continue
                
            X_test_target = self.X_test[mask_test]
            y_test_target = self.targets_test[target][mask_test]
            
            is_binary = 'binary' in target
            
            # Evaluate baseline models
            for baseline_type in ['climatology', 'persistence']:
                model_name = f"{baseline_type}_{target}"
                try:
                    if baseline_type == 'persistence':
                        # Persistence uses current precipitation
                        pred_input = self.test_df[mask_test][['precipitation_mm']].values
                    else:
                        pred_input = np.zeros((len(X_test_target), 1))
                    
                    if model_name in self.baseline_models.models:
                        if is_binary:
                            y_pred = self.baseline_models.models[model_name].predict_proba(pred_input)[:, 1]
                        else:
                            y_pred = self.baseline_models.models[model_name].predict(pred_input)
                        
                        target_results[baseline_type] = self._compute_metrics(
                            y_test_target, y_pred, is_binary
                        )
                        
                except Exception as e:
                    logger.error(f"Baseline evaluation failed for {model_name}: {e}")
            
            # Evaluate gradient boosted models
            for model_type in ['lightgbm', 'xgboost']:
                model_name = f"{model_type}_{target}"
                try:
                    if model_name in self.gb_models.models:
                        y_pred = self.gb_models.predict(model_name, X_test_target)
                        
                        target_results[model_type] = self._compute_metrics(
                            y_test_target, y_pred, is_binary
                        )
                        
                except Exception as e:
                    logger.error(f"GB evaluation failed for {model_name}: {e}")
            
            if target_results:
                results[target] = target_results
        
        self.training_results = results
        logger.info("Model evaluation completed")
        
        return results
    
    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, is_binary: bool) -> dict:
        """Compute evaluation metrics."""
        metrics = {}
        
        if is_binary:
            # Binary classification metrics
            metrics['auc'] = roc_auc_score(y_true, y_pred)
            metrics['brier_score'] = brier_score_loss(y_true, y_pred)
            
            # Convert probabilities to binary predictions
            y_pred_binary = (y_pred > 0.5).astype(int)
            metrics['accuracy'] = (y_true == y_pred_binary).mean()
            
        else:
            # Regression metrics
            metrics['rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
            metrics['mae'] = np.mean(np.abs(y_true - y_pred))
            
            # Correlation
            if np.std(y_true) > 0 and np.std(y_pred) > 0:
                metrics['correlation'] = np.corrcoef(y_true, y_pred)[0, 1]
            else:
                metrics['correlation'] = 0.0
        
        return metrics
    
    def save_models(self):
        """Save trained models and results."""
        logger.info("Saving models...")
        
        # Save baseline models
        baseline_path = self.models_dir / "baseline_models.pkl"
        with open(baseline_path, 'wb') as f:
            pickle.dump(self.baseline_models.models, f)
        
        # Save gradient boosted models
        gb_path = self.models_dir / "gradient_boosted_models.pkl"
        with open(gb_path, 'wb') as f:
            pickle.dump(self.gb_models.models, f)
        
        # Save feature importance
        importance_path = self.models_dir / "feature_importance.json"
        with open(importance_path, 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            importance_serializable = {}
            for model_name, importance in self.gb_models.feature_importance.items():
                importance_serializable[model_name] = {
                    k: float(v) for k, v in importance.items()
                }
            json.dump(importance_serializable, f, indent=2)
        
        # Save training results
        results_path = self.models_dir / "training_results.json"
        with open(results_path, 'w') as f:
            json.dump(self.training_results, f, indent=2)
        
        # Save metadata
        metadata = {
            'training_date': datetime.now().isoformat(),
            'feature_columns': self.feature_columns,
            'target_columns': self.target_columns,
            'dataset_info': self.dataset_info,
            'model_types': {
                'baseline': list(self.baseline_models.models.keys()),
                'gradient_boosted': list(self.gb_models.models.keys())
            }
        }
        
        metadata_path = self.models_dir / "model_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Models saved to {self.models_dir}")
    
    def train_all_models(self):
        """Complete model training pipeline."""
        logger.info("Starting complete model training pipeline...")
        
        # Load data
        self.load_datasets()
        
        # Prepare data
        self.prepare_data()
        
        # Train baselines
        self.train_baselines()
        
        # Train gradient boosted models
        self.train_gradient_boosted()
        
        # Evaluate all models
        results = self.evaluate_models()
        
        # Save everything
        self.save_models()
        
        logger.info("Training pipeline completed successfully!")
        
        return results


def main():
    """Main training function."""
    setup_logging()
    
    trainer = ModelTrainer()
    
    try:
        results = trainer.train_all_models()
        
        # Print summary of results
        logger.info("\n" + "="*50)
        logger.info("TRAINING RESULTS SUMMARY")
        logger.info("="*50)
        
        for target, target_results in results.items():
            logger.info(f"\nTarget: {target}")
            for model_type, metrics in target_results.items():
                logger.info(f"  {model_type:12s}: {metrics}")
        
        logger.info("\nTraining completed successfully!")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    main()