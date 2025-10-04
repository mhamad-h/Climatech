#!/usr/bin/env python3
"""
Simple ML training pipeline runner.
Runs the complete ML pipeline: data download -> dataset building -> training -> evaluation
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_command(cmd, description):
    """Run a command and log the result."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✓ {description} completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ {description} failed")
        logger.error(f"Error: {e.stderr}")
        return False


def setup_directories():
    """Create necessary directories."""
    logger.info("Setting up directories...")
    
    directories = [
        'data',
        'data/cache', 
        'models',
        'evaluation',
        'evaluation/visualizations'
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(exist_ok=True)
    
    logger.info("✓ Directories created")


def install_requirements():
    """Install Python requirements."""
    logger.info("Installing Python requirements...")
    
    requirements = [
        'pandas>=1.5.0',
        'numpy>=1.21.0',
        'scikit-learn>=1.0.0',
        'lightgbm>=3.3.0',
        'xgboost>=1.6.0',
        'matplotlib>=3.5.0',
        'seaborn>=0.11.0',
        'tqdm>=4.64.0',
        'httpx>=0.24.0',
        'geopy>=2.2.0',
        'timezonefinder>=6.0.0'
    ]
    
    for requirement in requirements:
        cmd = f"{sys.executable} -m pip install '{requirement}'"
        if not run_command(cmd, f"Installing {requirement}"):
            logger.warning(f"Failed to install {requirement}, continuing anyway...")
    
    logger.info("✓ Requirements installation completed")


def run_ml_pipeline():
    """Run the complete ML pipeline."""
    logger.info("Starting ML training pipeline...")
    
    # Change to ml directory
    ml_dir = Path(__file__).parent / 'ml'
    os.chdir(ml_dir)
    
    # Pipeline steps
    steps = [
        (f"{sys.executable} download_data.py", "Download training data"),
        (f"{sys.executable} build_dataset.py", "Build ML dataset"),
        (f"{sys.executable} train.py", "Train models"),
        (f"{sys.executable} evaluate.py", "Evaluate models")
    ]
    
    for cmd, description in steps:
        if not run_command(cmd, description):
            logger.error(f"Pipeline failed at step: {description}")
            return False
    
    logger.info("✓ Complete ML pipeline finished successfully!")
    return True


def check_model_outputs():
    """Check that models were created successfully."""
    logger.info("Checking model outputs...")
    
    expected_files = [
        'data/train_dataset.parquet',
        'data/val_dataset.parquet', 
        'data/test_dataset.parquet',
        'models/baseline_models.pkl',
        'models/gradient_boosted_models.pkl',
        'models/model_metadata.json',
        'evaluation/evaluation_report.json'
    ]
    
    missing_files = []
    for file_path in expected_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.warning(f"Missing output files: {missing_files}")
        return False
    
    logger.info("✓ All expected model files created successfully")
    return True


def main():
    """Main training pipeline."""
    logger.info("="*60)
    logger.info("PRECIPITATION FORECASTING ML TRAINING PIPELINE")
    logger.info("="*60)
    
    try:
        # Setup
        setup_directories()
        
        # Install requirements
        install_requirements()
        
        # Run ML pipeline
        if not run_ml_pipeline():
            logger.error("ML pipeline failed")
            sys.exit(1)
        
        # Check outputs
        if not check_model_outputs():
            logger.warning("Some model files may be missing")
        
        logger.info("="*60)
        logger.info("TRAINING COMPLETED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("Models are ready for use in the application.")
        logger.info("Check 'models/' directory for trained models.")
        logger.info("Check 'evaluation/' directory for performance reports.")
        
    except KeyboardInterrupt:
        logger.error("Training interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Training failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()