import pytest
import mlflow
from mlflow import MlflowClient
import dagshub
import json

dagshub.init(repo_owner='saabiqcs', repo_name='swiggy-time-prediction', mlflow=True)

# set the tracking server
mlflow.set_tracking_uri("https://dagshub.com/saabiqcs/swiggy-time-prediction.mlflow")

def load_model_information(file_path):
    with open(file_path) as f:
        run_info = json.load(f)
        
    return run_info

# set model name
run_info = load_model_information("run_information.json")
model_name = run_info["model_name"]
run_id = run_info["run_id"]



def test_load_model_from_registry():
    client = MlflowClient()
    latest_versions = client.search_model_versions(f"name='{model_name}'")
    latest_version = latest_versions[0].version if latest_versions else None

    assert latest_version is not None, f"No registered model found for {model_name}"

    # load the model logged by the current run
    model_path = f"runs:/{run_id}/delivery_time_pred_model"

    # load the latest model artifact
    model = mlflow.sklearn.load_model(model_path)
    
    assert model is not None, "Failed to load model from registry"
    print(f"The {model_name} model with version {latest_version} was loaded successfully")
    
