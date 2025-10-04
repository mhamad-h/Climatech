"""
Comprehensive model evaluation and analysis.
Provides detailed metrics, visualizations, and skill scores.
"""

import os
import sys
import json
import pickle
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# ML and stats
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    roc_auc_score, roc_curve, precision_recall_curve,
    brier_score_loss, accuracy_score, confusion_matrix,
    classification_report
)
from scipy import stats
import lightgbm as lgb

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


class ModelEvaluator:
    """Comprehensive model evaluation and analysis."""
    
    def __init__(self, models_dir: str = "models", data_dir: str = "data", output_dir: str = "evaluation"):
        self.models_dir = Path(models_dir)
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load models and data
        self.load_models()
        self.load_data()
        
        # Results storage
        self.detailed_results = {}
        self.skill_scores = {}
    
    def load_models(self):
        """Load trained models."""
        logger.info("Loading trained models...")
        
        # Load baseline models
        baseline_path = self.models_dir / "baseline_models.pkl"
        if baseline_path.exists():
            with open(baseline_path, 'rb') as f:
                self.baseline_models = pickle.load(f)
        else:
            self.baseline_models = {}
        
        # Load gradient boosted models
        gb_path = self.models_dir / "gradient_boosted_models.pkl"
        if gb_path.exists():
            with open(gb_path, 'rb') as f:
                self.gb_models = pickle.load(f)
        else:
            self.gb_models = {}
        
        # Load feature importance
        importance_path = self.models_dir / "feature_importance.json"
        if importance_path.exists():
            with open(importance_path, 'r') as f:
                self.feature_importance = json.load(f)
        else:
            self.feature_importance = {}
        
        # Load metadata
        metadata_path = self.models_dir / "model_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self.model_metadata = json.load(f)
        else:
            self.model_metadata = {}
        
        logger.info(f"Loaded {len(self.baseline_models)} baseline and {len(self.gb_models)} GB models")
    
    def load_data(self):
        """Load test dataset."""
        logger.info("Loading test data...")
        
        self.test_df = pd.read_parquet(self.data_dir / "test_dataset.parquet")
        
        # Load feature info
        with open(self.data_dir / "dataset_info.json", 'r') as f:
            self.dataset_info = json.load(f)
        
        self.feature_columns = self.dataset_info['feature_columns']
        self.target_columns = self.dataset_info['target_columns']
        
        # Prepare feature matrix
        self.X_test = self.test_df[self.feature_columns].fillna(0)
        
        logger.info(f"Test data: {len(self.test_df)} samples, {len(self.feature_columns)} features")
    
    def predict_all_models(self):
        """Generate predictions from all models."""
        logger.info("Generating predictions from all models...")
        
        self.predictions = {}
        
        for target in tqdm(self.target_columns, desc="Generating predictions"):
            target_predictions = {}
            
            # Get valid test samples for this target
            mask = ~self.test_df[target].isna()
            if mask.sum() < 10:
                continue
            
            X_test_target = self.X_test[mask]
            y_true = self.test_df[target][mask].values
            
            # Baseline model predictions
            for model_name, model in self.baseline_models.items():
                if target in model_name:
                    try:
                        if 'persistence' in model_name:
                            # Use current precipitation for persistence
                            pred_input = self.test_df[mask][['precipitation_mm']].values
                        else:
                            pred_input = np.zeros((len(X_test_target), 1))
                        
                        if 'binary' in target:
                            if hasattr(model, 'predict_proba'):
                                y_pred = model.predict_proba(pred_input)[:, 1]
                            else:
                                y_pred = model.predict(pred_input)
                        else:
                            y_pred = model.predict(pred_input)
                        
                        model_type = 'persistence' if 'persistence' in model_name else 'climatology'
                        target_predictions[model_type] = {
                            'y_true': y_true,
                            'y_pred': y_pred,
                            'mask': mask
                        }
                        
                    except Exception as e:
                        logger.error(f"Prediction failed for {model_name}: {e}")
            
            # Gradient boosted model predictions
            for model_name, model in self.gb_models.items():
                if target in model_name:
                    try:
                        if isinstance(model, lgb.Booster):
                            y_pred = model.predict(X_test_target)
                        else:
                            if 'binary' in target and hasattr(model, 'predict_proba'):
                                y_pred = model.predict_proba(X_test_target)[:, 1]
                            else:
                                y_pred = model.predict(X_test_target)
                        
                        model_type = 'lightgbm' if 'lightgbm' in model_name else 'xgboost'
                        target_predictions[model_type] = {
                            'y_true': y_true,
                            'y_pred': y_pred,
                            'mask': mask
                        }
                        
                    except Exception as e:
                        logger.error(f"Prediction failed for {model_name}: {e}")
            
            if target_predictions:
                self.predictions[target] = target_predictions
        
        logger.info(f"Generated predictions for {len(self.predictions)} targets")
    
    def compute_detailed_metrics(self):
        """Compute comprehensive metrics for all models."""
        logger.info("Computing detailed metrics...")
        
        for target, target_predictions in tqdm(self.predictions.items(), desc="Computing metrics"):
            target_results = {}
            is_binary = 'binary' in target
            
            for model_type, pred_data in target_predictions.items():
                y_true = pred_data['y_true']
                y_pred = pred_data['y_pred']
                
                metrics = {}
                
                if is_binary:
                    # Binary classification metrics
                    metrics['auc_roc'] = roc_auc_score(y_true, y_pred)
                    metrics['brier_score'] = brier_score_loss(y_true, y_pred)
                    
                    # Threshold-based metrics
                    y_pred_binary = (y_pred > 0.5).astype(int)
                    metrics['accuracy'] = accuracy_score(y_true, y_pred_binary)
                    
                    # Confusion matrix components
                    tn, fp, fn, tp = confusion_matrix(y_true, y_pred_binary).ravel()
                    metrics['precision'] = tp / (tp + fp) if (tp + fp) > 0 else 0
                    metrics['recall'] = tp / (tp + fn) if (tp + fn) > 0 else 0
                    metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
                    
                    # F1 score
                    if metrics['precision'] + metrics['recall'] > 0:
                        metrics['f1_score'] = 2 * metrics['precision'] * metrics['recall'] / (metrics['precision'] + metrics['recall'])
                    else:
                        metrics['f1_score'] = 0
                    
                    # False alarm rate
                    metrics['false_alarm_rate'] = fp / (tn + fp) if (tn + fp) > 0 else 0
                    
                    # Probability of detection
                    metrics['pod'] = metrics['recall']
                    
                    # Critical Success Index (CSI)
                    metrics['csi'] = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0
                    
                else:
                    # Regression metrics
                    metrics['rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
                    metrics['mae'] = mean_absolute_error(y_true, y_pred)
                    metrics['r2'] = r2_score(y_true, y_pred)
                    
                    # Mean bias
                    metrics['bias'] = np.mean(y_pred - y_true)
                    
                    # Correlation
                    if np.std(y_true) > 0 and np.std(y_pred) > 0:
                        metrics['correlation'] = np.corrcoef(y_true, y_pred)[0, 1]
                    else:
                        metrics['correlation'] = 0
                    
                    # Normalized metrics
                    if np.std(y_true) > 0:
                        metrics['normalized_rmse'] = metrics['rmse'] / np.std(y_true)
                        metrics['normalized_mae'] = metrics['mae'] / np.mean(np.abs(y_true))
                    else:
                        metrics['normalized_rmse'] = 0
                        metrics['normalized_mae'] = 0
                
                target_results[model_type] = metrics
            
            self.detailed_results[target] = target_results
        
        logger.info("Detailed metrics computed")
    
    def compute_skill_scores(self):
        """Compute skill scores relative to baseline models."""
        logger.info("Computing skill scores...")
        
        for target, target_results in self.detailed_results.items():
            target_skill = {}
            is_binary = 'binary' in target
            
            # Use climatology as reference
            if 'climatology' not in target_results:
                continue
            
            ref_metrics = target_results['climatology']
            
            for model_type, metrics in target_results.items():
                if model_type == 'climatology':
                    continue
                
                skill = {}
                
                if is_binary:
                    # Brier Skill Score (higher is better)
                    ref_brier = ref_metrics['brier_score']
                    model_brier = metrics['brier_score']
                    skill['brier_skill_score'] = (ref_brier - model_brier) / ref_brier if ref_brier > 0 else 0
                    
                    # AUC improvement
                    skill['auc_improvement'] = metrics['auc_roc'] - 0.5  # Improvement over random
                    
                else:
                    # Nash-Sutcliffe Efficiency (similar to R²)
                    ref_rmse = ref_metrics['rmse']
                    model_rmse = metrics['rmse']
                    skill['nse'] = 1 - (model_rmse**2) / (ref_rmse**2) if ref_rmse > 0 else -np.inf
                    
                    # RMSE skill score
                    skill['rmse_skill_score'] = (ref_rmse - model_rmse) / ref_rmse if ref_rmse > 0 else 0
                    
                    # Correlation improvement
                    skill['correlation_improvement'] = metrics['correlation'] - ref_metrics['correlation']
                
                target_skill[model_type] = skill
            
            self.skill_scores[target] = target_skill
        
        logger.info("Skill scores computed")
    
    def create_visualizations(self):
        """Create comprehensive visualizations."""
        logger.info("Creating visualizations...")
        
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # Set style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # 1. Model performance comparison
        self._plot_model_comparison(viz_dir)
        
        # 2. Skill scores visualization
        self._plot_skill_scores(viz_dir)
        
        # 3. Feature importance plots
        self._plot_feature_importance(viz_dir)
        
        # 4. Prediction vs truth scatter plots
        self._plot_predictions_scatter(viz_dir)
        
        # 5. ROC curves for binary targets
        self._plot_roc_curves(viz_dir)
        
        logger.info(f"Visualizations saved to {viz_dir}")
    
    def _plot_model_comparison(self, viz_dir: Path):
        """Plot model performance comparison."""
        # Collect metrics for comparison
        binary_metrics = []
        continuous_metrics = []
        
        for target, target_results in self.detailed_results.items():
            is_binary = 'binary' in target
            
            for model_type, metrics in target_results.items():
                if is_binary:
                    binary_metrics.append({
                        'target': target,
                        'model': model_type,
                        'auc': metrics['auc_roc'],
                        'brier_score': metrics['brier_score'],
                        'accuracy': metrics['accuracy']
                    })
                else:
                    continuous_metrics.append({
                        'target': target,
                        'model': model_type,
                        'rmse': metrics['rmse'],
                        'mae': metrics['mae'],
                        'r2': metrics['r2']
                    })
        
        # Binary targets plot
        if binary_metrics:
            df_binary = pd.DataFrame(binary_metrics)
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            
            # AUC comparison
            sns.boxplot(data=df_binary, x='model', y='auc', ax=axes[0,0])
            axes[0,0].set_title('AUC-ROC by Model Type')
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # Brier Score comparison (lower is better)
            sns.boxplot(data=df_binary, x='model', y='brier_score', ax=axes[0,1])
            axes[0,1].set_title('Brier Score by Model Type (Lower is Better)')
            axes[0,1].tick_params(axis='x', rotation=45)
            
            # Accuracy comparison
            sns.boxplot(data=df_binary, x='model', y='accuracy', ax=axes[1,0])
            axes[1,0].set_title('Accuracy by Model Type')
            axes[1,0].tick_params(axis='x', rotation=45)
            
            # AUC heatmap by target
            pivot_auc = df_binary.pivot(index='target', columns='model', values='auc')
            sns.heatmap(pivot_auc, annot=True, fmt='.3f', ax=axes[1,1], cmap='viridis')
            axes[1,1].set_title('AUC by Target and Model')
            
            plt.tight_layout()
            plt.savefig(viz_dir / "binary_model_comparison.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # Continuous targets plot
        if continuous_metrics:
            df_continuous = pd.DataFrame(continuous_metrics)
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            
            # RMSE comparison
            sns.boxplot(data=df_continuous, x='model', y='rmse', ax=axes[0,0])
            axes[0,0].set_title('RMSE by Model Type (Lower is Better)')
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # MAE comparison  
            sns.boxplot(data=df_continuous, x='model', y='mae', ax=axes[0,1])
            axes[0,1].set_title('MAE by Model Type (Lower is Better)')
            axes[0,1].tick_params(axis='x', rotation=45)
            
            # R² comparison
            sns.boxplot(data=df_continuous, x='model', y='r2', ax=axes[1,0])
            axes[1,0].set_title('R² by Model Type')
            axes[1,0].tick_params(axis='x', rotation=45)
            
            # R² heatmap by target
            pivot_r2 = df_continuous.pivot(index='target', columns='model', values='r2')
            sns.heatmap(pivot_r2, annot=True, fmt='.3f', ax=axes[1,1], cmap='viridis')
            axes[1,1].set_title('R² by Target and Model')
            
            plt.tight_layout()
            plt.savefig(viz_dir / "continuous_model_comparison.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_skill_scores(self, viz_dir: Path):
        """Plot skill scores."""
        skill_data = []
        
        for target, target_skills in self.skill_scores.items():
            for model_type, skills in target_skills.items():
                for skill_name, skill_value in skills.items():
                    skill_data.append({
                        'target': target,
                        'model': model_type,
                        'skill_metric': skill_name,
                        'skill_value': skill_value
                    })
        
        if skill_data:
            df_skills = pd.DataFrame(skill_data)
            
            # Create separate plots for different skill metrics
            skill_metrics = df_skills['skill_metric'].unique()
            
            n_metrics = len(skill_metrics)
            fig, axes = plt.subplots(1, min(n_metrics, 3), figsize=(15, 5))
            if n_metrics == 1:
                axes = [axes]
            
            for i, metric in enumerate(skill_metrics[:3]):
                metric_data = df_skills[df_skills['skill_metric'] == metric]
                
                if len(axes) > i:
                    sns.barplot(data=metric_data, x='model', y='skill_value', 
                              hue='target', ax=axes[i])
                    axes[i].set_title(f'{metric.replace("_", " ").title()}')
                    axes[i].tick_params(axis='x', rotation=45)
                    axes[i].axhline(y=0, color='red', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(viz_dir / "skill_scores.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_feature_importance(self, viz_dir: Path):
        """Plot feature importance for gradient boosted models."""
        if not self.feature_importance:
            return
        
        # Aggregate feature importance across all models
        feature_scores = {}
        
        for model_name, importance in self.feature_importance.items():
            for feature, score in importance.items():
                if feature not in feature_scores:
                    feature_scores[feature] = []
                feature_scores[feature].append(score)
        
        # Average importance across models
        avg_importance = {
            feature: np.mean(scores) 
            for feature, scores in feature_scores.items()
        }
        
        # Get top features
        top_features = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:20]
        
        if top_features:
            features, scores = zip(*top_features)
            
            plt.figure(figsize=(10, 8))
            sns.barplot(x=list(scores), y=list(features), orient='h')
            plt.title('Top 20 Features by Average Importance')
            plt.xlabel('Average Feature Importance')
            plt.tight_layout()
            plt.savefig(viz_dir / "feature_importance.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_predictions_scatter(self, viz_dir: Path):
        """Plot prediction vs truth scatter plots."""
        for target, target_predictions in list(self.predictions.items())[:3]:  # Limit to first 3
            is_binary = 'binary' in target
            
            if is_binary:
                continue  # Skip binary targets for scatter plots
            
            fig, axes = plt.subplots(1, len(target_predictions), figsize=(15, 4))
            if len(target_predictions) == 1:
                axes = [axes]
            
            for i, (model_type, pred_data) in enumerate(target_predictions.items()):
                y_true = pred_data['y_true']
                y_pred = pred_data['y_pred']
                
                if i < len(axes):
                    axes[i].scatter(y_true, y_pred, alpha=0.5, s=1)
                    
                    # Perfect prediction line
                    min_val = min(y_true.min(), y_pred.min())
                    max_val = max(y_true.max(), y_pred.max())
                    axes[i].plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
                    
                    axes[i].set_xlabel('True Values')
                    axes[i].set_ylabel('Predictions')
                    axes[i].set_title(f'{model_type.title()}: {target}')
                    
                    # Add correlation coefficient
                    corr = np.corrcoef(y_true, y_pred)[0, 1]
                    axes[i].text(0.05, 0.95, f'r = {corr:.3f}', 
                               transform=axes[i].transAxes, 
                               verticalalignment='top',
                               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            plt.savefig(viz_dir / f"predictions_scatter_{target}.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_roc_curves(self, viz_dir: Path):
        """Plot ROC curves for binary classification targets."""
        binary_targets = [target for target in self.predictions.keys() if 'binary' in target]
        
        for target in binary_targets[:3]:  # Limit to first 3 binary targets
            target_predictions = self.predictions[target]
            
            plt.figure(figsize=(8, 6))
            
            for model_type, pred_data in target_predictions.items():
                y_true = pred_data['y_true']
                y_pred = pred_data['y_pred']
                
                fpr, tpr, _ = roc_curve(y_true, y_pred)
                auc = roc_auc_score(y_true, y_pred)
                
                plt.plot(fpr, tpr, label=f'{model_type} (AUC = {auc:.3f})')
            
            # Random classifier line
            plt.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Random')
            
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')  
            plt.title(f'ROC Curves: {target}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(viz_dir / f"roc_curves_{target}.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    def generate_report(self):
        """Generate comprehensive evaluation report."""
        logger.info("Generating evaluation report...")
        
        report = {
            'evaluation_date': datetime.now().isoformat(),
            'dataset_info': self.dataset_info,
            'model_metadata': self.model_metadata,
            'detailed_metrics': self.detailed_results,
            'skill_scores': self.skill_scores,
            'summary': self._create_summary()
        }
        
        # Save JSON report
        report_path = self.output_dir / "evaluation_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Create markdown summary
        self._create_markdown_summary()
        
        logger.info(f"Evaluation report saved to {self.output_dir}")
        
        return report
    
    def _create_summary(self):
        """Create summary statistics."""
        summary = {}
        
        # Model performance summary
        for target, target_results in self.detailed_results.items():
            is_binary = 'binary' in target
            
            best_model = None
            best_score = -np.inf if is_binary else np.inf
            
            for model_type, metrics in target_results.items():
                if is_binary:
                    score = metrics['auc_roc']
                    if score > best_score:
                        best_score = score
                        best_model = model_type
                else:
                    score = metrics['r2']
                    if score > best_score:
                        best_score = score
                        best_model = model_type
            
            summary[target] = {
                'best_model': best_model,
                'best_score': best_score,
                'metric_type': 'auc_roc' if is_binary else 'r2'
            }
        
        return summary
    
    def _create_markdown_summary(self):
        """Create markdown summary report."""
        md_content = """# Precipitation Forecasting Model Evaluation Report

## Overview
This report provides a comprehensive evaluation of precipitation forecasting models trained on historical weather data.

## Dataset Information
"""
        
        md_content += f"- **Training samples**: {self.dataset_info['dataset_stats']['train_samples']:,}\n"
        md_content += f"- **Validation samples**: {self.dataset_info['dataset_stats']['val_samples']:,}\n" 
        md_content += f"- **Test samples**: {self.dataset_info['dataset_stats']['test_samples']:,}\n"
        md_content += f"- **Number of features**: {self.dataset_info['dataset_stats']['n_features']}\n"
        md_content += f"- **Number of locations**: {self.dataset_info['dataset_stats']['n_locations']}\n"
        
        md_content += "\n## Model Performance Summary\n\n"
        
        # Create performance table
        md_content += "| Target | Best Model | Score | Metric |\n"
        md_content += "|--------|------------|-------|--------|\n"
        
        summary = self._create_summary()
        for target, info in summary.items():
            md_content += f"| {target} | {info['best_model']} | {info['best_score']:.3f} | {info['metric_type']} |\n"
        
        md_content += "\n## Key Findings\n\n"
        
        # Add key findings based on results
        binary_aucs = []
        continuous_r2s = []
        
        for target, target_results in self.detailed_results.items():
            is_binary = 'binary' in target
            
            for model_type, metrics in target_results.items():
                if model_type in ['lightgbm', 'xgboost']:  # Focus on ML models
                    if is_binary:
                        binary_aucs.append(metrics['auc_roc'])
                    else:
                        continuous_r2s.append(metrics['r2'])
        
        if binary_aucs:
            avg_auc = np.mean(binary_aucs)
            md_content += f"- **Binary Classification**: Average AUC-ROC = {avg_auc:.3f}\n"
            
        if continuous_r2s:
            avg_r2 = np.mean(continuous_r2s)
            md_content += f"- **Regression**: Average R² = {avg_r2:.3f}\n"
        
        md_content += "\n## Model Types Evaluated\n\n"
        md_content += "1. **Climatology Baseline**: Long-term averages\n"
        md_content += "2. **Persistence Baseline**: Current conditions\n"
        md_content += "3. **LightGBM**: Gradient boosted trees\n"
        md_content += "4. **XGBoost**: Gradient boosted trees\n"
        
        md_content += "\n## Files Generated\n\n"
        md_content += "- `evaluation_report.json`: Detailed metrics and results\n"
        md_content += "- `visualizations/`: Performance plots and charts\n"
        md_content += "- Model comparison plots and feature importance analysis\n"
        
        # Save markdown report
        with open(self.output_dir / "evaluation_summary.md", 'w') as f:
            f.write(md_content)
    
    def run_complete_evaluation(self):
        """Run complete model evaluation pipeline."""
        logger.info("Starting complete model evaluation...")
        
        # Generate predictions
        self.predict_all_models()
        
        # Compute detailed metrics
        self.compute_detailed_metrics()
        
        # Compute skill scores
        self.compute_skill_scores()
        
        # Create visualizations
        self.create_visualizations()
        
        # Generate final report
        report = self.generate_report()
        
        logger.info("Model evaluation completed successfully!")
        
        return report


def main():
    """Main evaluation function."""
    setup_logging()
    
    evaluator = ModelEvaluator()
    
    try:
        report = evaluator.run_complete_evaluation()
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("EVALUATION SUMMARY")
        logger.info("="*60)
        
        for target, info in report['summary'].items():
            logger.info(f"{target:30s}: {info['best_model']:12s} ({info['best_score']:.3f})")
        
        logger.info("\nEvaluation completed successfully!")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise


if __name__ == "__main__":
    main()