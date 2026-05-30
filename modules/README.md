# IoT Healthcare Platform - Modules

This directory contains the modular components of the IoT Healthcare Monitoring Platform. The modular architecture separates concerns and makes the codebase maintainable, testable, and extensible.

## Module Overview

### 1. `data_module.py` - Data Loading and Preprocessing

**Purpose:** Handles all data-related operations including loading, parsing, cleaning, and validation.

**Key Classes:**
- `DataLoader`: Load data from CSV files or uploaded files
- `DataParser`: Parse JSON sensor data and extract features
- `DataPreprocessor`: Clean data, handle missing values, validate ranges
- `DataPipeline`: Complete end-to-end data processing pipeline

**Usage Example:**
```python
from modules.data_module import DataPipeline

pipeline = DataPipeline()
df_clean = pipeline.process_file("iot_data.csv")
```

### 2. `ml_module.py` - Machine Learning

**Purpose:** Handles ML model training, prediction, and health risk scoring.

**Key Classes:**
- `ModelTrainer`: Train Random Forest classifier for anomaly detection
- `ModelPredictor`: Load models and make predictions on new data
- `HealthRiskScorer`: Calculate health risk scores based on sensor readings

**Usage Example:**
```python
from modules.ml_module import ModelPredictor

predictor = ModelPredictor()
predictor.load_model()
predictions = predictor.predict(df)
```

### 3. `visualization_module.py` - Plotly Visualizations

**Purpose:** Create interactive Plotly charts for data visualization.

**Key Classes:**
- `TimeSeriesVisualizer`: Time series charts for sensor data
- `AnomalyVisualizer`: Scatter plots and 3D visualizations for anomalies
- `MetricsVisualizer`: Gauge charts, distributions, and box plots
- `FeatureImportanceVisualizer`: Feature importance bar charts
- `RiskVisualizer`: Risk score timelines and gauges

**Usage Example:**
```python
from modules.visualization_module import AnomalyVisualizer

fig = AnomalyVisualizer.create_scatter_plot(df, x_col="BPM", y_col="SPO2")
st.plotly_chart(fig)
```

### 4. `simulation_module.py` - Sensor Data Simulation

**Purpose:** Generate realistic sensor data for testing and demonstration.

**Key Classes:**
- `VitalSignSimulator`: Simulate vital signs (BPM, SPO2, Body_Temp)
- `EnvironmentalSimulator`: Simulate environmental sensors (Temp, Humidity)
- `ActivitySimulator`: Simulate readings based on patient activity
- `CompleteSensorSimulator`: Generate complete datasets with all sensors

**Usage Example:**
```python
from modules.simulation_module import CompleteSensorSimulator

simulator = CompleteSensorSimulator(random_state=42)
df = simulator.generate_complete_dataset(n_samples=100, anomaly_rate=0.1)
```

### 5. `utils_module.py` - Helper Functions and Constants

**Purpose:** Provide utility functions, constants, and configuration helpers.

**Key Components:**
- `SensorConstants`: Sensor field IDs, normal ranges, display names, icons
- `AlertConstants`: Alert levels, colors, icons, messages
- `ModelConstants`: Model paths and hyperparameters
- `AlertManager`: Manage health alerts based on sensor readings
- `DataValidator`: Validate data quality and integrity
- `FormatUtils`: Format data for display
- `ConfigHelper`: Configuration management

**Usage Example:**
```python
from modules.utils_module import AlertManager, SensorConstants

alert_mgr = AlertManager()
alerts = alert_mgr.check_all_sensors({"BPM": 120, "SPO2": 92})
```

## Architecture Benefits

### Separation of Concerns
Each module has a single, well-defined responsibility:
- Data operations are isolated in `data_module`
- ML logic is contained in `ml_module`
- Visualization code is in `visualization_module`
- Simulation is separate in `simulation_module`
- Shared utilities are in `utils_module`

### Maintainability
- Easy to locate and modify specific functionality
- Changes in one module don't affect others
- Clear interfaces between modules

### Testability
- Each module can be tested independently
- Mock dependencies easily for unit testing
- Integration testing is straightforward

### Reusability
- Modules can be imported and used in different contexts
- Functions and classes are designed for reuse
- Easy to extend with new functionality

### Backward Compatibility
- Maintains compatibility with existing ESP32 hardware integration
- Preserves existing data formats and APIs
- Gradual migration path from monolithic to modular

## Integration with Existing Code

The modular structure is designed to work alongside the existing `app.py`, `server.py`, and `reader.py` files:

- **app.py**: Can be refactored to use modules for cleaner code
- **server.py**: Flask API server continues to work unchanged
- **reader.py**: Serial reader continues to work unchanged
- **Existing models**: `anomaly_model.pkl` and `scaler.pkl` remain compatible

## Next Steps

1. **Refactor app.py**: Update the main Streamlit app to use the new modules
2. **Add tests**: Create unit tests for each module
3. **Implement Random Forest**: Replace Isolation Forest with Random Forest classifier
4. **Add new features**: Implement risk scoring, activity recognition, and explainability
5. **Enhance visualizations**: Replace matplotlib with Plotly charts

## Testing

Run the module verification script to ensure everything is working:

```bash
python test_modules.py
```

This will test all modules and verify that they can be imported and initialized correctly.
