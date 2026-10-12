# Renewable Energy AI — Generation Forecasting & Grid Coordination System

An AI-powered renewable energy monitoring and grid coordination platform that combines weather intelligence, machine learning forecasts, anomaly detection, battery optimization, and human-reviewed operational recommendations.

The system is designed to help operators understand renewable energy generation, anticipate demand, evaluate energy surpluses and deficits, and review feasible battery schedules.

> **Important:** This project is a decision-support prototype. Its forecasts and optimization schedules are recommendations, not commands to physical grid equipment. Model performance must be interpreted according to the provenance and quality of the evaluation data.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [AI Agent Architecture](#ai-agent-architecture)
- [Technology Stack](#technology-stack)
- [Data Sources and Provenance](#data-sources-and-provenance)
- [Forecasting and Optimization](#forecasting-and-optimization)
- [Dashboard Modules](#dashboard-modules)
- [PDF Reporting](#pdf-reporting)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Validation and Testing](#validation-and-testing)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Overview

Renewable energy generation depends on changing environmental conditions, including solar irradiance, cloud cover, temperature, wind speed, and wind direction. Electricity demand also changes over time, making it difficult to maintain a reliable balance between generation and consumption.

This project addresses these challenges through a web-based energy intelligence platform.

The application integrates weather information, generation and demand forecasting, energy balance calculations, battery constraints, optimization, anomaly analysis, and human approval into a unified workflow.

The system is intended to demonstrate how machine learning, numerical optimization, workflow orchestration, and AI-assisted decision support can work together in a renewable energy environment.

### Project Objectives

- Monitor registered renewable energy assets and their measurements.
- Retrieve weather information for forecasting.
- Estimate future solar and wind generation.
- Forecast electricity demand.
- Evaluate generation-demand imbalances.
- Identify anomalies and potential operational issues.
- Calculate battery schedules subject to configured constraints.
- Coordinate forecasting, analysis, optimization, and review through a workflow.
- Support operator approval, rejection, and recalculation of recommendations.
- Generate downloadable PDF reports from stored workflow results.

---

## Key Features

### 1. Renewable Asset Management

- Register and view renewable energy assets.
- Manage asset configuration and installed capacity.
- Distinguish active and inactive assets.
- Track recorded energy measurements.

### 2. Weather Intelligence

- Retrieve current and forecast weather information.
- Display hourly weather forecasts.
- Include temperature, cloud cover, wind speed, wind direction, and solar radiation where available.
- Display weather source and relevant timestamps.

### 3. Generation Forecasting

- Generate solar power forecasts.
- Generate wind power forecasts.
- Associate forecasts with their valid timestamps.
- Display forecast information and model provenance.
- Distinguish forecasts from recorded generation measurements.

### 4. Demand Forecasting

- Estimate future electricity demand.
- Use historical demand information where available.
- Compare predictions against a previous-day demand baseline.
- Evaluate forecasts using error metrics.
- Validate timestamp requirements for historical demand comparisons.

### 5. Energy Balance Analysis

- Evaluate renewable generation against demand.
- Calculate energy surplus or deficit.
- Display balance results returned by the backend.
- Support configurable balance tolerance where implemented.

### 6. Battery Storage Management

- Configure battery energy capacity.
- Configure maximum charging and discharging power.
- Define minimum and maximum state-of-charge limits.
- Configure charging and discharging efficiencies.
- Calculate energy availability from configured battery parameters.

### 7. Energy Optimization

- Evaluate generation and demand forecasts.
- Calculate candidate battery charging and discharging schedules.
- Account for battery energy and power constraints.
- Evaluate grid imports, grid exports, unmet demand, curtailed generation, and conversion losses where returned by the optimizer.
- Display the resulting schedule and battery state-of-charge trajectory.

### 8. Performance and Anomaly Analysis

- Analyze workflow findings.
- Compare forecasts with actual measurements when timestamps align.
- Identify potential generation-demand imbalances.
- Distinguish forecast-based findings from measured deviations.

### 9. Human Review and Approval

- Inspect stored workflow results.
- Review the generated optimization plan.
- Approve or reject a plan when the workflow is awaiting operator review.
- Provide rejection feedback.
- Support recalculation with modified assumptions where available.
- Associate decisions with plan versions.

### 10. Operational PDF Reports

- Select a stored workflow run.
- Apply a reporting date range.
- Generate a downloadable PDF report.
- Include available asset, measurement, forecasting, optimization, anomaly, and approval information.
- Preserve the distinction between measured values, forecasts, simulated values, and recommendations.

---

## System Architecture

The application uses a frontend-backend architecture.

```text
                    Renewable Energy AI
                            |
              +-------------+-------------+
              |                           |
        React Frontend              FastAPI Backend
              |                           |
       Dashboard Pages             REST API Endpoints
              |                           |
              |                 +---------+----------+
              |                 |         |          |
              |              Database  ML Models  Weather API
              |                 |         |          |
              |                 +---------+----------+
              |                           |
              |                  Workflow Orchestration
              |                           |
              |                +----------+----------+
              |                |                     |
              |          AI/Workflow Agents     Numerical Services
              |                |                     |
              |                +----------+----------+
              |                           |
              |                 Forecasts and Analysis
              |                           |
              |                 Grid Optimization
              |                           |
              |                  Reviewer / Operator
              |                           |
              +---------------------------+
                            |
                    PDF Report Generation
```

### Architecture Components

**Frontend**

Provides the dashboard interface for assets, generation, weather, forecasting, energy balance, battery storage, optimization, anomalies, alerts, AI operations, and reports.

**Backend**

Provides REST APIs, input validation, database access, forecasting services, optimization, workflow execution, and report generation.

**Database**

Stores configured assets, measurements, workflow records, alerts, and other persisted application data.

**Machine Learning Services**

Generate solar, wind, and demand forecasts using the configured forecasting models.

**Workflow Orchestration**

Coordinates the execution of specialized processing stages and manages workflow results, review states, and plan decisions.

**Numerical Services**

Perform energy balance calculations, battery constraint checks, and optimization calculations.

**Reporting Service**

Generates PDF reports using stored workflow information and available operational records.

---

## AI Agent Architecture

The project organizes energy-system analysis into specialized roles.

### 1. Asset Monitoring Agent

**Responsibility:** Examine registered assets and available measurements.

Typical responsibilities include:

- Reviewing asset information.
- Checking measurement availability.
- Identifying relevant data-quality issues.
- Providing validated information to subsequent workflow stages.

### 2. Weather Intelligence Agent

**Responsibility:** Obtain and organize weather information for the forecasting workflow.

Typical responsibilities include:

- Retrieving weather data.
- Providing weather information to forecasting components.
- Preserving relevant timestamps and source information.
- Identifying weather-related context for subsequent analysis.

### 3. Generation Forecasting Agent

**Responsibility:** Coordinate solar and wind generation predictions.

Typical responsibilities include:

- Preparing forecasting inputs.
- Invoking generation forecasting services.
- Returning timestamped generation estimates.
- Providing model provenance and relevant warnings.

### 4. Demand Forecasting Agent

**Responsibility:** Estimate future electricity demand.

Typical responsibilities include:

- Preparing demand forecasting inputs.
- Invoking the demand prediction service.
- Returning demand estimates.
- Supporting comparison against historical baselines.

### 5. Performance and Anomaly Agent

**Responsibility:** Analyze forecast performance and identify potential irregularities.

Typical responsibilities include:

- Comparing forecasts against aligned actual measurements.
- Identifying generation-demand imbalances.
- Producing investigation findings.
- Distinguishing observed deviations from forecast-based warnings.

### 6. Battery Management Agent

**Responsibility:** Evaluate battery availability and operating constraints.

Typical responsibilities include:

- Checking configured battery capacity.
- Evaluating charging and discharging limits.
- Considering state-of-charge bounds.
- Accounting for conversion efficiencies.
- Providing constraint information to the optimizer.

### 7. Grid Coordination Agent

**Responsibility:** Coordinate energy balance and grid optimization.

Typical responsibilities include:

- Combining generation and demand forecasts.
- Evaluating battery constraints.
- Invoking the numerical optimizer.
- Producing a candidate schedule.
- Reporting grid imports, exports, and residual energy requirements where available.

### Reviewer and Human Approval

A reviewer mechanism evaluates the candidate plan before operator approval.

The operator can review the available findings and make an approval or rejection decision when the workflow supports human review. Recalculation can be used to generate an updated plan when the relevant workflow state permits it.

**Design principle:** Machine learning models estimate numerical values, deterministic services perform calculations, workflow orchestration coordinates processing, and human review provides an additional decision checkpoint.

---

## Technology Stack

The project uses the following technologies in its architecture.

| Component | Technology |
|---|---|
| Frontend | React |
| Programming Language | TypeScript |
| Frontend Build Tool | Vite |
| UI Icons | Lucide React |
| Charts | Recharts |
| Backend Framework | FastAPI |
| Backend Language | Python |
| API Communication | REST APIs |
| Database | PostgreSQL / SQLAlchemy |
| Workflow Orchestration | LangGraph, where configured in the workflow |
| Machine Learning | Python-based forecasting services and model artifacts |
| Weather Integration | Open-Meteo API |
| PDF Generation | ReportLab |
| Version Control | Git and GitHub |

The exact installed dependency versions are defined by the project's dependency files.

---

## Data Sources and Provenance

Reliable forecasts require a clear distinction between historical observations, weather information, simulated data, and model predictions.

### Weather Data

The application integrates with Open-Meteo for current and forecast weather information.

Official documentation:

- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)

Weather information can include:

- Solar radiation.
- Cloud cover.
- Temperature.
- Wind speed.
- Wind direction.
- Forecast timestamps.

The weather provider's output represents weather information, not a direct measurement of renewable electricity generation.

### Historical Energy Data

Historical energy datasets can be used to train and evaluate forecasting models.

One public source is Open Power System Data:

- [Open Power System Data — Time Series](https://data.open-power-system-data.org/time_series/2020-10-06)

When using public datasets, the geographic region, measurement units, timestamps, and aggregation level must be compatible with the intended forecasting scenario.

National energy totals should not be treated as measurements from an individual facility.

### Synthetic Data

Synthetic datasets may be used for development, testing, or model training when suitable historical facility data is unavailable.

Synthetic data must be clearly labeled.

Model scores calculated using synthetic data do not establish real-world forecasting accuracy.

### Data Quality Principles

The application should:

- Normalize timestamps consistently.
- Preserve source and timestamp information.
- Validate measurements before using them.
- Avoid treating missing values as zero.
- Respect configured asset capacities.
- Distinguish recorded measurements from model predictions.
- Compare forecasts against actual observations only when the timestamps align.

---

## Forecasting and Optimization

### Generation Forecasting

Solar and wind forecasting components estimate renewable generation using available weather information and model inputs.

Forecast outputs should include relevant valid timestamps and model provenance.

Predictions must be interpreted within the physical limits of the configured assets.

### Demand Forecasting

The demand forecasting component estimates electricity demand using the available historical information and forecasting inputs.

Where an exact previous-day observation is required for comparison, the system should not silently substitute a different historical value when that observation is missing.

### Evaluation Metrics

Forecast evaluation can include:

**Mean Absolute Error (MAE)**

The average absolute difference between predictions and actual observations.

**Root Mean Squared Error (RMSE)**

The square root of the average squared prediction error. Larger errors have a greater influence on this metric.

Evaluation should use held-out observations and an appropriate baseline.

Reported metrics should identify their evaluation dataset and should not be presented as real-world performance when they were obtained using synthetic data.

### Energy Balance

Energy balance calculations compare renewable generation with electricity demand.

A simplified balance is:

```text
Energy Balance = Total Generation - Demand
```

- Positive balance indicates a generation surplus before other system effects.
- Negative balance indicates a generation deficit before other system effects.
- A complete operational balance must account for battery operation and grid imports or exports where applicable.

### Battery Optimization

The optimizer evaluates candidate schedules subject to configured constraints.

These may include:

- Battery energy capacity.
- Maximum charging power.
- Maximum discharging power.
- Minimum and maximum state of charge.
- Charging efficiency.
- Discharging efficiency.
- Initial and terminal state-of-charge requirements.
- Energy balance requirements.

The optimizer's output is a calculated recommendation. It does not imply that the battery or electrical grid has physically executed the schedule.

---

## Dashboard Modules

The frontend is organized into operational pages covering the following areas:

| Module | Purpose |
|---|---|
| Overview | High-level renewable energy and operational metrics |
| Assets | Renewable asset registration and configuration |
| Live Generation | Recorded generation measurements and trends |
| Weather | Current weather and hourly forecast information |
| Generation Forecast | Solar and wind generation predictions |
| Demand Forecast | Electricity demand prediction and evaluation |
| Energy Balance | Generation-demand balance analysis |
| Battery Storage | Battery configuration and calculated energy limits |
| Optimization | Candidate grid coordination and battery schedules |
| Anomalies | Workflow findings and performance analysis |
| Alerts | Persisted operational alerts and acknowledgement |
| AI Operations | Workflow results, execution traces, and operator decisions |
| Reports | Stored workflow selection and PDF report generation |

Displayed values depend on the availability and quality of the underlying backend data.

---

## PDF Reporting

The reporting service generates downloadable PDF reports from stored workflow results and available operational records.

Depending on the selected run and available data, a report can include:

- Workflow identification and reporting period.
- Asset information and installed capacity.
- Recorded generation and demand.
- Weather information and forecast provenance.
- Generation and demand forecasts.
- Energy balance and optimization schedules.
- Battery configuration and schedule details.
- Anomaly findings and alerts.
- Optimization recommendations.
- Reviewer findings and operator decisions.

The reporting period is expressed using UTC date boundaries.

Missing or unavailable information should remain explicitly identified rather than being replaced with fabricated values.

Optimization schedules and recommendations are not evidence of physical grid dispatch.

---

## Project Structure

The repository is organized around the frontend and backend applications.

```text
renewable-energy-ai/
|
+-- backend/
|   +-- app/
|   |   +-- api/
|   |   |   +-- alerts.py
|   |   |   +-- assets.py
|   |   |   +-- battery.py
|   |   |   +-- demand_forecasting.py
|   |   |   +-- forecasting.py
|   |   |   +-- grid.py
|   |   |   +-- reports.py
|   |   |   +-- workflow.py
|   |   |
|   |   +-- db/
|   |   |   +-- database.py
|   |   |   +-- models.py
|   |   |
|   |   +-- services/
|   |   |   +-- alerts.py
|   |   |   +-- forecasting.py
|   |   |   +-- grid_optimizer.py
|   |   |   +-- weather.py
|   |   |
|   |   +-- workflows/
|   |       +-- battery_management.py
|   |       +-- demand_forecasting.py
|   |       +-- generation_forecasting.py
|   |       +-- nodes.py
|   |       +-- performance_anomaly.py
|   |       +-- replanning.py
|   |       +-- reviewer.py
|   |       +-- state.py
|   |
|   +-- requirements.txt
|
+-- frontend/
|   +-- src/
|   |   +-- components/
|   |   +-- services/
|   |   +-- App.tsx
|   |   +-- App.css
|   |
|   +-- package.json
|
+-- models/
+-- data/
+-- README.md
```

This is a logical overview. The exact files and folders may differ depending on which optional scripts, datasets, and model artifacts are included in the repository.

---

## Prerequisites

Install the following before running the application:

- Python 3.12 or a compatible version specified by the backend dependencies.
- Node.js and npm.
- PostgreSQL, configured for the backend database.
- Git.

An internet connection is required for external weather API requests.

Additional environment variables or model artifacts may be required by the configured backend services.

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd renewable-energy-ai
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the URL of your GitHub repository.

### 2. Configure the Backend

Open a terminal in the repository root.

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the virtual environment's Python executable directly.

Install backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables

Create the environment configuration file required by the backend.

Configure the database connection and any other variables expected by the application's settings.

For example, a database URL may use this format:

```text
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE_NAME
```

Replace the placeholders with your own database credentials.

**Never commit real credentials, API keys, or passwords to GitHub.**

Use a `.env.example` file containing placeholders to document the required configuration.

### 4. Prepare the Database

Create the PostgreSQL database and apply the database initialization or migration commands provided by the project.

Ensure that the backend can connect to the configured database before starting the application.

### 5. Configure the Frontend

Open another terminal:

```bash
cd frontend
npm install
```

Configure the frontend API base URL using the environment variable expected by the frontend API client.

For a local development setup, the backend is expected to run at:

```text
http://127.0.0.1:8001
```

The frontend API URL must match the actual backend address and port.

---

## Running the Application

### Start the Backend

From the repository root, activate the Python virtual environment and run:

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

If the application requires a different working directory or import configuration, follow the existing backend setup for this repository.

The backend should expose its health endpoint and API documentation when configured successfully.

### Start the Frontend

Open another terminal:

```bash
cd frontend
npm run dev
```

Open the local URL printed by Vite in the terminal.

### API Documentation

When the backend is running, open:

```text
http://127.0.0.1:8001/docs
```

The Swagger UI allows you to inspect available endpoints and submit API requests.

**Note:** These are local development instructions. A public deployment is not included unless deployment URLs are explicitly provided.

---

## API Documentation

The backend provides REST endpoints for application functionality.

The following endpoint groups are used by the application:

| Endpoint Group | Purpose |
|---|---|
| Assets | Register, list, and manage renewable energy assets |
| Measurements | Access recorded energy measurements |
| Weather | Retrieve current and forecast weather information |
| Generation Forecasting | Request solar and wind generation predictions |
| Demand Forecasting | Request electricity demand predictions |
| Energy Balance | Calculate generation-demand balance |
| Battery | Retrieve and update battery configuration and status |
| Grid Optimization | Calculate candidate energy schedules |
| Workflow | Start and inspect workflow runs, and manage review decisions |
| Alerts | Retrieve and acknowledge persisted alerts |
| Reports | List reportable workflow runs and download PDF reports |

For exact paths, request formats, response schemas, and validation requirements, refer to the running Swagger documentation.

---

## Validation and Testing

The project includes backend services and frontend components for energy forecasting, optimization, workflow analysis, and reporting.

Testing should cover:

- Asset and measurement validation.
- Invalid or missing timestamps.
- Generation limits and battery constraints.
- Solar, wind, and demand forecast responses.
- Energy balance calculations.
- Optimization feasibility.
- Workflow state transitions.
- Operator approval and rejection.
- Anomaly analysis with aligned and unaligned measurements.
- PDF generation for stored workflow runs.
- Frontend production build.

### Frontend Production Build

From the frontend directory:

```bash
npm run build
```

A successful build verifies that the frontend compiles. It does not, by itself, verify every API integration or dashboard interaction.

### Backend Validation

Run the tests available in the repository using the configured Python environment.

For example, if the project uses pytest:

```bash
python -m pytest
```

Only treat tests that actually exist and have been executed as verified results.

---

## Limitations

The system is a prototype for renewable energy forecasting and decision support.

### Forecasting Limitations

- Model performance depends on training data, feature quality, and evaluation methodology.
- Predictions trained or evaluated on synthetic data do not establish real-world accuracy.
- Forecasts must be compared against actual measurements at matching timestamps.
- Missing historical observations can prevent certain forecast comparisons.

### Weather Limitations

- Weather information depends on the external provider and network availability.
- Weather conditions alone do not constitute measured renewable generation.
- Forecast provenance and timestamps should be considered when interpreting predictions.

### Battery Limitations

- Calculated battery state may be based on configuration rather than physical telemetry.
- A configured state of charge is not equivalent to a live battery measurement.
- Optimization results depend on the configured battery parameters and input forecasts.

### Workflow Limitations

- Workflow outputs depend on the available inputs, configured services, and successful execution of the relevant stages.
- A generated plan is a recommendation and requires appropriate review.
- Workflow persistence and checkpoint recovery depend on the configured storage implementation.

### Deployment Limitations

- Local development instructions do not imply that the application has been deployed publicly.
- Production deployment requires appropriate database security, environment configuration, monitoring, and operational testing.

---

## Future Improvements

Potential improvements include:

- Evaluating forecasts against additional real-world historical datasets.
- Expanding forecast evaluation across multiple horizons.
- Improving forecast uncertainty estimation.
- Adding live battery and renewable asset telemetry.
- Strengthening persistent workflow checkpointing and recovery.
- Expanding automated tests for workflow and optimization edge cases.
- Improving deployment automation and observability.
- Adding more detailed historical performance reports.
- Evaluating the system under additional renewable generation and demand scenarios.

---
