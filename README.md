# Renewable Energy Generation Forecasting & Grid Coordination System

An AI-powered renewable energy monitoring, forecasting, and grid coordination platform developed for the Brightcone AI assignment.

The system combines renewable energy data processing, weather intelligence, machine learning forecasting, battery storage analysis, energy balancing, and AI-assisted operational recommendations through a web-based dashboard.

## 1. Project Overview

Renewable energy generation depends on changing environmental conditions. Solar generation varies with sunlight, cloud cover, and temperature, while wind generation depends on wind speed and other environmental factors.

Electricity demand also changes throughout the day, creating potential generation-demand imbalances.

This project aims to help renewable energy operators:

- Monitor solar and wind generation.
- Retrieve weather information.
- Forecast renewable energy generation.
- Forecast electricity demand.
- Identify potential generation-demand imbalances.
- Analyze renewable energy performance.
- Detect potential anomalies.
- Evaluate battery storage constraints.
- Generate energy coordination recommendations.
- Review operational decisions through a dashboard.
- Track forecast performance and generate PDF reports.

**Important:** This application is a decision-support prototype. It does not directly control physical grid infrastructure or battery equipment.

## 2. Example Renewable Energy Facility

The system uses the following reference configuration from the assignment:

| Component | Capacity |
|---|---:|
| Solar PV plant | 10 MW |
| Wind farm | 6 MW |
| Battery storage | 8 MWh |
| Maximum battery charge/discharge power | 2 MW |
| Initial battery state of charge | 45% |

Example operating conditions:

| Parameter | Value |
|---|---:|
| Solar generation | 7.2 MW |
| Wind generation | 3.1 MW |
| Total renewable generation | 10.3 MW |
| Electricity demand | 8.4 MW |
| Renewable energy surplus | 1.9 MW |

Renewable surplus is calculated as:

`Renewable Surplus = Total Generation - Electricity Demand`

The system evaluates generation, demand, weather conditions, and battery operating limits when analyzing potential energy coordination strategies.

## 3. Technology Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- REST APIs

### Frontend
- React
- TypeScript
- Vite

### Machine Learning and Data Processing
- Pandas
- NumPy
- Scikit-learn
- Joblib

### Weather Integration
- Open-Meteo API
- Historical weather data
- Weather-informed forecasting

### AI Workflow and Coordination
- LangGraph-based agent orchestration
- Specialized operational agents
- Workflow state management
- Reviewer and human-approval concepts

### Database and Reporting
- Configured application database
- Data persistence
- PDF report generation

Refer to `requirements.txt` and `frontend/package.json` for the dependencies used by the project.

## 4. System Architecture

The application follows a modular architecture.

```text
Renewable Energy Data
          |
          v
Data Ingestion and Validation
          |
          v
Asset and Measurement Management
          |
          v
Weather Intelligence
          |
          v
Generation Forecasting
          |
          v
Demand Forecasting
          |
          v
Performance and Anomaly Analysis
          |
          v
Battery Constraint Analysis
          |
          v
Energy Balancing and Optimization
          |
          v
Grid Coordination
          |
          v
Reviewer and Operator Approval
          |
          v
Monitoring, Reports and Feedback
```

The backend exposes APIs for data access and application functionality. The frontend provides a dashboard for inspecting operational information and interacting with the available features.

## 5. Specialized AI Agent Roles

The project architecture is designed around specialized operational responsibilities.

| Agent | Responsibility |
|---|---|
| Asset Monitoring Agent | Reviews assets, measurements, and data quality. |
| Weather Intelligence Agent | Retrieves weather information and identifies relevant changes. |
| Generation Forecasting Agent | Supports solar and wind generation forecasting. |
| Demand Forecasting Agent | Predicts electricity demand. |
| Performance and Anomaly Agent | Evaluates deviations between expected and observed performance. |
| Battery Management Agent | Evaluates battery state and operating constraints. |
| Grid Coordination Agent | Analyzes energy balances and coordinates recommendations. |

A reviewer mechanism checks recommendations before operator approval.

Agent execution, workflow orchestration, and approval functionality should be evaluated against the actual implementation and its test results.

## 6. Data Sources

The project uses both public historical data and development data.

### Historical Energy Data

Public electricity-generation and demand data from Open Power System Data can support model training and retrospective evaluation.

### Historical Weather Data

Historical weather information is obtained through Open-Meteo.

The current historical weather dataset was retrieved for Berlin, Germany, using UTC timestamps covering January 2015 through September 2020.

### Synthetic Data

Synthetic energy data can be used for development, testing, and demonstration.

Synthetic data must remain clearly identified as synthetic. Results obtained from synthetic datasets must not be presented as real-world forecasting performance.

### Dataset and Model Availability

Large datasets and trained model artifacts may be excluded from this GitHub repository to keep the repository manageable.

The corresponding files may need to be downloaded or regenerated locally before running features that depend on them.

Refer to the project's data-processing and model-training scripts when preparing these files.

## 7. Machine Learning and Forecasting

The project includes forecasting components for:

- Solar generation.
- Wind generation.
- Electricity demand.

The models use historical measurements and, where supported, weather-related information to estimate future values.

Forecast evaluation should use chronological training and testing splits to reduce information leakage.

The evaluation process includes:

- Mean Absolute Error (MAE).
- Root Mean Squared Error (RMSE).
- Comparison with baseline forecasting methods.

### Important Model Evaluation Note

Historical model results are retrospective measurements, not guarantees of future accuracy.

Models trained on synthetic data must not be represented as validated real-world forecasting models.

Weather-informed models must also be evaluated carefully because weather observations from historical periods do not necessarily represent the forecasts that would have been available at the time of operation.

## 8. Energy Balancing and Battery Analysis

The application evaluates the relationship between renewable generation and electricity demand.

The basic energy balance is:

`Energy Balance = Solar Generation + Wind Generation - Demand`

A positive balance indicates a surplus, while a negative balance indicates a deficit.

Battery analysis considers relevant operating constraints, including:

- Installed energy capacity.
- State of charge (SoC).
- Maximum charging power.
- Maximum discharging power.
- Available charging and discharging energy.
- Battery operating limits.

Any proposed schedule must be checked against the configured constraints before it is presented as feasible.

## 9. Weather Intelligence

Weather information supports the interpretation of renewable generation variability.

The weather integration uses Open-Meteo for weather retrieval.

Weather information can help explain changes in solar and wind generation and provide inputs for weather-informed forecasting models.

Weather data retrieval and model forecasting are separate operations. A successful API request does not, by itself, establish that a forecast is accurate.

## 10. Application Features

The frontend and backend provide components for renewable energy monitoring and operational analysis.

The dashboard is organized around capabilities such as:

- Renewable energy overview.
- Asset management.
- Live generation.
- Weather intelligence.
- Generation forecasting.
- Demand forecasting.
- Energy balance.
- Battery storage.
- Energy optimization.
- Performance and anomaly analysis.
- Alerts.
- AI operations.
- Reports.

The availability and completeness of individual features depend on the current implementation and configuration.

## 11. Project Structure

The repository is organized into the following major areas.

```text
renewable-energy-ai/
│
├── backend/                 # FastAPI backend
├── frontend/                # React and TypeScript application
├── data/                    # Historical and development datasets
├── models/                  # Trained model artifacts
├── reports/                 # Generated reports
├── tests/                   # Automated tests
├── requirements.txt         # Python dependencies
├── .gitignore               # Git exclusion rules
└── README.md                # Project documentation
```

Some generated artifacts and large datasets are intentionally excluded from version control.

## 12. Prerequisites

Install the following before running the application:

- Python 3.12 or a compatible version supported by the installed dependencies.
- Node.js and npm.
- Git.
- A configured application database, if required by the current environment.
- Access to the weather API for live weather retrieval.

The required Python packages are listed in `requirements.txt`.

The frontend dependencies are listed in `frontend/package.json`.

## 13. Backend Setup

Open PowerShell in the project root directory.

Create a virtual environment if one does not already exist:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure the environment variables required by the application.

Start the backend from the project root:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

The backend should be available at:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

Health endpoint:

`http://127.0.0.1:8000/health`

If the database, environment variables, or required model artifacts are not configured, resolve those dependencies before testing the corresponding functionality.

## 14. Frontend Setup

Open a second terminal in the project root.

Navigate to the frontend directory:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Vite normally makes the frontend available at:

`http://localhost:5173`

If the backend URL is configurable through an environment variable, configure it according to the frontend's existing implementation.

Keep API credentials and other secrets out of frontend code.

## 15. Testing

Run the automated tests from the project root using the configured Python environment:

```powershell
python -m pytest
```

Review the test results to identify failures.

Important scenarios to evaluate include:

1. Normal solar and wind generation.
2. Changes in cloud cover and solar generation.
3. Generation underperformance.
4. Renewable generation exceeding demand.
5. Forecast demand exceeding renewable generation.
6. Battery recommendations exceeding configured power limits.
7. Material weather changes requiring replanning.
8. Comparison of forecasts with actual measurements.

The final evaluation should record actual test outcomes rather than assuming that every scenario passes.

## 16. Reports

The application includes report-generation functionality.

Generated reports may summarize energy measurements, forecasts, energy balances, battery analysis, anomalies, and operational recommendations, depending on the information available in the selected reporting period.

Generated reports are outputs of the application and should be distinguished from the source code required to reproduce them.

## 17. Limitations

The following considerations are important when interpreting results:

- Forecast accuracy depends on data quality, feature availability, and evaluation methodology.
- Historical weather observations are not equivalent to operational weather forecasts.
- Synthetic datasets are intended for development and testing unless independently validated for another purpose.
- Trained model files excluded from GitHub must be made available locally before dependent features can run.
- Weather API availability depends on the external service.
- Battery recommendations must respect the configured technical constraints.
- The application is a decision-support prototype and must not directly control physical electrical infrastructure.

## 18. Future Improvements

Potential improvements include:

- More extensive real-world model validation.
- Additional weather and energy data sources.
- Improved forecast uncertainty estimation.
- More comprehensive automated tests.
- Persistent workflow checkpoints and approval history.
- Enhanced anomaly detection.
- Reproducible model-training pipelines.
- Deployment and production monitoring.
- Expanded reporting and forecast-accuracy tracking.

## 19. Repository

GitHub:

https://github.com/praneethj18/renewable-energy-ai

---

**Project:** Renewable Energy Generation Forecasting & Grid Coordination System
