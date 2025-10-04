#!/usr/bin/env python3
"""
Quick test of ML pipeline components.
Tests basic functionality without full training.
"""

import sys
import os
from pathlib import Path

# Add ml directory to path
ml_dir = Path(__file__).parent / 'ml'
sys.path.append(str(ml_dir))

def test_imports():
    """Test that all ML components can be imported."""
    print("Testing imports...")
    
    try:
        from feature_defs import FeatureDefinitions
        print("✓ FeatureDefinitions imported")
        
        from download_data import DataDownloader
        print("✓ DataDownloader imported")
        
        from model_inference import ModelInferenceService
        print("✓ ModelInferenceService imported")
        
        # Test backend integration
        sys.path.append(str(Path(__file__).parent / 'backend'))
        from services.model_inference import ModelInferenceService as BackendService
        print("✓ Backend ModelInferenceService imported")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_feature_definitions():
    """Test feature engineering definitions."""
    print("\nTesting feature definitions...")
    
    try:
        from feature_defs import FeatureDefinitions
        import pandas as pd
        from datetime import datetime
        
        # Create sample data
        data = {
            'datetime': [pd.Timestamp('2024-01-15 12:00:00')],
            'precipitation_mm': [1.5]
        }
        df = pd.DataFrame(data)
        
        feature_defs = FeatureDefinitions()
        
        # Test temporal features
        result = feature_defs.temporal_features(df)
        assert 'hour' in result.columns
        assert 'day_of_year' in result.columns
        print("✓ Temporal features working")
        
        # Test location features
        result = feature_defs.location_features(result, 40.7, -74.0, 10)
        assert 'latitude' in result.columns
        assert 'distance_to_coast' in result.columns
        print("✓ Location features working")
        
        return True
    except Exception as e:
        print(f"✗ Feature definitions test failed: {e}")
        return False

def test_model_inference():
    """Test model inference service."""
    print("\nTesting model inference...")
    
    try:
        from model_inference import ModelInferenceService
        from datetime import datetime
        
        # Create inference service (will use fallbacks if no models)
        service = ModelInferenceService()
        print("✓ ModelInferenceService initialized")
        
        # Test prediction (should use fallback)
        current_weather = {
            'datetime': datetime.now(),
            'temperature': 22.5,
            'humidity': 65.0,
            'pressure': 1015.0,
            'precipitation': 0.0
        }
        
        location_info = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'elevation': 10.0
        }
        
        forecasts = service.predict_precipitation(
            current_weather, location_info, [1, 6, 24]
        )
        
        assert '1h' in forecasts
        assert 'precipitation_mm' in forecasts['1h']
        assert 'precipitation_probability' in forecasts['1h']
        print("✓ Basic prediction working")
        
        return True
    except Exception as e:
        print(f"✗ Model inference test failed: {e}")
        return False

def test_backend_integration():
    """Test backend service integration."""
    print("\nTesting backend integration...")
    
    try:
        sys.path.append(str(Path(__file__).parent / 'backend'))
        from services.model_inference import inference_service
        
        print("✓ Backend service imported")
        
        # The service should initialize without errors
        assert hasattr(inference_service, 'predict_precipitation')
        print("✓ Backend service initialized")
        
        return True
    except Exception as e:
        print(f"✗ Backend integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("CLIMATECH ML PIPELINE COMPONENT TESTS")
    print("="*60)
    
    tests = [
        test_imports,
        test_feature_definitions, 
        test_model_inference,
        test_backend_integration
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("✓ All tests passed! ML pipeline components are working.")
        print("\nNext steps:")
        print("1. Run 'python train_models.py' to train ML models")
        print("2. Start the backend: 'cd backend && python app.py'")
        print("3. Start the frontend: 'cd client && npm run dev'")
    else:
        print("✗ Some tests failed. Check error messages above.")
        print("Make sure all dependencies are installed correctly.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())