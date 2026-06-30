# Food Delivery Time Prediction System

A production-grade, end-to-end machine learning system that predicts food delivery time in minutes. This isn't just a Jupyter notebook — it has a full MLOps stack with experiment tracking, model registry, automated CI/CD, and live cloud deployment on AWS.

I built this as a B.Tech fresher to understand what real ML engineering looks like beyond just training a model.

---

## Live Demo

API is deployed on AWS EC2 and served via FastAPI:

```
GET  http://<ec2-public-ip>/
POST http://<ec2-public-ip>/predict
```

Interactive docs at: `http://<ec2-public-ip>/docs`

---

## Architecture

![Architecture Diagram](reports/figures/architecture.png)

---

## Demo

[![Demo Video](https://github.com/user-attachments/assets/b80a1246-2cff-4526-a8c5-f5264b1ca65a)](https://github.com/user-attachments/assets/3a6a574e-d620-4af0-8267-6771ba277a3d)

---

## Tech Stack

| Area | Tools |
|---|---|
| ML & Training | Scikit-learn, LightGBM, Optuna |
| Experiment Tracking | MLflow + DagsHub |
| Data Versioning | DVC + AWS S3 |
| API | FastAPI + Uvicorn |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Cloud | AWS EC2, ECR, CodeDeploy, S3, Auto Scaling Group |
| Pipeline Orchestration | DVC Pipelines |

---

## Model Performance

I deliberately chose **MAE (Mean Absolute Error)** as the key metric over RMSE/MSE. Delivery time data has natural outliers — accidents, traffic jams, festival rush — and squaring the errors (RMSE) would let those dominate training. MAE treats every minute equally, which is what actually matters in a delivery prediction use case.

| Metric | Value |
|---|---|
| Test MAE | **< 5 minutes** |
| CV MAE (5-fold) | **3.160 minutes** |
| Train R² | tracked per run on DagsHub |
| Test R² | tracked per run on DagsHub |

All metrics, parameters, artifacts and experiment comparisons are tracked on DagsHub:
👉 https://dagshub.com/saabiqcs/swiggy-time-prediction

### Benchmark vs IBM AutoAI

To validate the model, I ran IBM AutoAI on the same cleaned dataset (`swiggy_cleaned.csv`) with MAE as the optimization metric. Here's how they compare:

| Model | Approach | CV MAE |
|---|---|---|
| **Stacking Regressor** (this project) | RF + LGBM → Linear meta-learner, Optuna-tuned, PowerTransformer on target | **3.160 min** |
| IBM AutoAI best pipeline | Ensemble Snap Random Forest (automated HPO) | 4.9 min |

AutoAI's best pipeline was an automated Snap Random Forest ensemble — it achieved 4.9 min MAE without any manual feature engineering or hyperparameter tuning. The hand-crafted stacking model outperforms it by **~1.7 minutes**, validating that the deliberate model design choices (target transformation, stacking, Optuna tuning) made a meaningful difference over fully automated ML.

---

## Model Architecture

I ran multiple experiments before landing on the final model. Here's what I tried and why I ended up with stacking:

**Final Model: Stacking Regressor with Power-Transformed Target**

```
TransformedTargetRegressor
    └── StackingRegressor (cv=5)
            ├── RandomForestRegressor   ← base learner 1
            ├── LGBMRegressor           ← base learner 2
            └── LinearRegression        ← meta learner
```

- The target `time_taken` is **power-transformed** before training using `PowerTransformer` — delivery times are right-skewed and transforming the target before fitting made a real difference in MAE
- Stacking RF + LGBM with a linear meta-learner gave better generalization than either model alone — RF handles non-linear interactions well, LGBM is fast and handles ordinal features naturally
- The meta-learner (Linear Regression) learns how to best blend both base model predictions

**Hyperparameters are tuned with Optuna (TPE sampler) and stored in `params.yaml`:**

```yaml
Random_Forest:
  n_estimators: 479
  max_depth: 17
  max_features: 1
  min_samples_split: 9
  min_samples_leaf: 2
  max_samples: 0.6603673526197066

LightGBM:
  n_estimators: 154
  max_depth: 27
  learning_rate: 0.22234435854395157
  subsample: 0.7592213724048168
  min_child_weight: 20
  min_split_gain: 0.004604680609280751
  reg_lambda: 97.81002379097947
```

---

## Experiments (tracked in MLflow on DagsHub)

| Experiment | What I tested |
|---|---|
| Exp 1: Drop vs Impute | Whether dropping rows with missing values vs imputing gave better MAE |
| Exp 2: Missing Indicator | Adding binary flags for missing values as extra features |
| RF HP Tuning | Optuna study for Random Forest hyperparameters |
| LGBM HP Tuning | Optuna study for LightGBM hyperparameters |
| Stacking HP Tuning | Optuna study on the full stacking ensemble |
| Final Estimator | Comparing different meta-learners (LR, Ridge, etc.) |
| Model Selection | Final comparison across all experiments, best model picked |
| DVC Pipeline | Production pipeline run — metrics logged here on every `dvc repro` |

---

## Feature Engineering

Raw Swiggy data comes with messy strings, GPS coordinates, timestamps and invalid values. The full cleaning pipeline does:

- **Haversine distance** — calculated from restaurant GPS → delivery GPS coordinates (great-circle distance in km)
- **Distance type** — binned into `short / medium / long / very_long` (0–5, 5–10, 10–15, 15–25 km)
- **Pickup time (minutes)** — time between order placed and order picked up by rider
- **Time of day** — binned from order hour into `after_midnight / morning / afternoon / evening / night`
- **Is weekend** — binary flag from order date
- **City name** — extracted from rider ID string (e.g. `BANGRES19DEL01` → `BANG`)
- Dropped riders with **age < 18** (data quality issue)
- Dropped **6-star ratings** (invalid, max is 5)
- GPS coordinates **< 1.0** replaced with NaN (invalid readings near null island)

**Preprocessing pipeline (fit on train only, applied to test — no leakage):**

| Transformer | Columns |
|---|---|
| `MinMaxScaler` | age, ratings, pickup_time_minutes, distance |
| `OneHotEncoder` (drop first) | weather, type_of_order, type_of_vehicle, festival, city_type, is_weekend, order_time_of_day |
| `OrdinalEncoder` | traffic (low→medium→high→jam), distance_type (short→medium→long→very_long) |

---

## DVC Pipeline

The entire ML pipeline is orchestrated with DVC. One command runs everything:

```bash
dvc repro
```

Pipeline stages in order:

```
data_cleaning
    └── data_preparation
            └── data_preprocessing
                    └── train
                            └── evaluation  (logs to MLflow)
                                    └── register_model  (pushes to MLflow registry)
```

Raw data is versioned on AWS S3. Pull it with:

```bash
dvc pull -r myremote
```

---

## CI/CD Pipeline

Every `git push` triggers the full automated pipeline on GitHub Actions:

```
git push
    │
    ├── 1. Checkout code
    ├── 2. Install dependencies
    ├── 3. DVC pull data from S3
    ├── 4. pytest: test_model_registry.py   → checks model exists in DagsHub registry
    ├── 5. pytest: test_model_perf.py        → asserts test MAE <= 5 minutes
    ├── 6. promote_model_to_prod.py          → promotes model Staging → Production in MLflow registry
    ├── 7. docker build + push to Amazon ECR
    ├── 8. zip appspec + deploy scripts
    ├── 9. upload zip to S3
    └── 10. aws deploy create-deployment    → triggers CodeDeploy on EC2
```

If any test fails, the pipeline stops — no bad model ever gets deployed.

---

## AWS Deployment Architecture

```
Developer pushes code
        │
        ▼
GitHub Actions (CI/CD)
        │  builds & tests
        ▼
Amazon ECR  ←── Docker image pushed
        │
        ▼
AWS CodeDeploy
        │  runs start_docker.sh on EC2
        ▼
EC2 Instance (t3.micro, ap-south-1)
│   managed by Auto Scaling Group
│   config via Launch Template (EBS, AMI, instance type)
│
└── Docker Container
        └── FastAPI app  (port 8000 → 80)
                └── loads model from DagsHub MLflow Registry on startup
```

**Key infrastructure details:**
- EC2 is managed by an **Auto Scaling Group** — to update instance config (e.g. disk size), create a new Launch Template version and terminate the current instance; ASG auto-launches a fresh one
- Docker image is stored and versioned in **Amazon ECR**
- Deployment bundle (appspec + scripts) lives in **AWS S3**
- Deployment strategy: `CodeDeployDefault.OneAtATime`
- Raw training data versioned in **AWS S3** via DVC remote

---

## Project Structure

```
├── src/
│   ├── data/
│   │   ├── data_cleaning.py          # full cleaning + feature engineering pipeline
│   │   └── data_preparation.py       # train/test split
│   ├── features/
│   │   └── data_preprocessing.py     # column transformer, fits + saves preprocessor.joblib
│   └── models/
│       ├── train.py                  # builds and trains stacking regressor
│       ├── evaluation.py             # computes metrics, logs everything to MLflow
│       └── register_model.py         # registers model in MLflow registry (Staging)
├── scripts/
│   ├── promote_model_to_prod.py      # promotes Staging → Production (runs in CI/CD)
│   └── data_clean_utils.py           # inference-time cleaning (no target column)
├── tests/
│   ├── test_model_registry.py        # checks model is registered and loadable
│   └── test_model_perf.py            # gates deployment: MAE must be <= 5 min
├── deploy/
│   └── scripts/
│       ├── install_dependencies.sh   # installs docker + codedeploy agent on EC2
│       └── start_docker.sh           # pulls ECR image, starts container
├── app.py                            # FastAPI prediction API
├── Dockerfile                        # python:3.12-slim based image
├── dvc.yaml                          # pipeline stage definitions
├── params.yaml                       # model hyperparameters (Optuna tuned)
├── run_information.json              # latest MLflow run_id + model name (auto-updated by DVC)
└── .github/workflows/ci_cd.yaml     # full CI/CD workflow
```

---

## Running Locally

**1. Clone and install**
```bash
git clone https://github.com/MDsaabiq/delivery-time-prediction-system
cd delivery-time-prediction-system
pip install -r requirements.txt
```

**2. Set environment variables**
```bash
export DAGSHUB_USER_TOKEN=<your_dagshub_token>
export MLFLOW_TRACKING_USERNAME=<your_dagshub_username>
export MLFLOW_TRACKING_PASSWORD=<your_dagshub_token>
```

**3. Pull data from S3**
```bash
dvc pull -r myremote
```

**4. Run the full ML pipeline**
```bash
dvc repro
```

**5. Start the API**
```bash
python app.py
```
API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

---

## Running with Docker

```bash
docker build -t delivery-time-pred .

docker run -p 8000:8000 \
  -e DAGSHUB_USER_TOKEN=<your_token> \
  -e MLFLOW_TRACKING_USERNAME=<your_username> \
  -e MLFLOW_TRACKING_PASSWORD=<your_token> \
  delivery-time-pred
```

---

## API Reference

**POST /predict**

```json
{
  "ID": "12345",
  "Delivery_person_ID": "BANGRES19DEL01",
  "Delivery_person_Age": "29",
  "Delivery_person_Ratings": "4.7",
  "Restaurant_latitude": 12.9141,
  "Restaurant_longitude": 77.6101,
  "Delivery_location_latitude": 13.0012,
  "Delivery_location_longitude": 77.5921,
  "Order_Date": "15-03-2022",
  "Time_Orderd": "11:30:00",
  "Time_Order_picked": "11:45:00",
  "Weatherconditions": "conditions Sunny",
  "Road_traffic_density": "High",
  "Vehicle_condition": 2,
  "Type_of_order": "Snack",
  "Type_of_vehicle": "motorcycle",
  "multiple_deliveries": "0",
  "Festival": "No",
  "City": "Metropolitian"
}
```

Response: predicted delivery time in minutes (float)

---

## Environment Variables

| Variable | Where used | Description |
|---|---|---|
| `DAGSHUB_USER_TOKEN` | Docker container, local | DagsHub personal access token |
| `MLFLOW_TRACKING_USERNAME` | Docker container, local | DagsHub username |
| `MLFLOW_TRACKING_PASSWORD` | Docker container, local | Same as DagsHub token |
| `AWS_ACCESS_KEY_ID` | GitHub Secrets (CI/CD only) | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | GitHub Secrets (CI/CD only) | AWS credentials |
| `DAGSHUB_TOKEN` | GitHub Secrets (CI/CD only) | Passed as both MLflow username/password |

---

## Author

sk Saabiq — B.Tech Student  
GitHub: [@MDsaabiq](https://github.com/MDsaabiq)
DagsHub: [saabiqcs/swiggy-time-prediction](https://dagshub.com/saabiqcs/swiggy-time-prediction)



<!-- Swiggy Food Delivery Time Prediction | Python, Scikit-learn, LightGBM, MLflow, DVC, FastAPI, Docker, AWS
GitHub | DagsHub

Built an end-to-end ML system predicting food delivery time with < 5 min MAE on test data, deployed live on AWS EC2

Chose MAE over RMSE as the optimization metric — delivery data has natural outliers (traffic, accidents) and MAE treats every minute equally without letting extremes dominate

Engineered features from raw GPS coordinates (Haversine distance), timestamps (pickup time, time of day), and rider IDs (city extraction); handled invalid data like minor-age riders, 6-star ratings, and near-zero GPS coordinates

Ran 8 tracked MLflow experiments on DagsHub — tested drop vs impute strategies, missing indicators, and meta-learner selection before finalizing the model

Tuned Random Forest and LightGBM hyperparameters independently using Optuna (TPE sampler), then stacked them with a Linear Regression meta-learner wrapped inside a TransformedTargetRegressor for power-transformed target prediction

Built a DVC pipeline with 6 stages (clean → prepare → preprocess → train → evaluate → register) with raw data versioned on AWS S3 — full pipeline reruns with dvc repro

Built a FastAPI inference API serving predictions via POST /predict; containerized with Docker and deployed on AWS EC2 (t3.micro, ap-south-1) behind an Auto Scaling Group managed via Launch Template

Set up a full CI/CD pipeline on GitHub Actions — on every push: DVC pull → pytest model registry check → pytest MAE gate (≤ 5 min) → MLflow stage promotion (Staging → Production) → Docker build → ECR push → CodeDeploy deployment to EC2 -->