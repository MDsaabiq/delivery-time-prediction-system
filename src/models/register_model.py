import mlflow
import dagshub
import json
from pathlib import Path
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
import logging


# create logger
logger = logging.getLogger("register_model")
logger.setLevel(logging.INFO)

# console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# add handler to logger
logger.addHandler(handler)

# create a fomratter
formatter = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to handler
handler.setFormatter(formatter)

# initialize dagshub
import dagshub
import mlflow.client
dagshub.init(repo_owner='saabiqcs', repo_name='swiggy-time-prediction', mlflow=True)

# set the tracking server
mlflow.set_tracking_uri("https://dagshub.com/saabiqcs/swiggy-time-prediction.mlflow")

def load_model_information(file_path):
    with open(file_path) as f:
        run_info = json.load(f)
        
    return run_info


if __name__ == "__main__":
    # root path
    root_path = Path(__file__).parent.parent.parent
    
    # run information file path
    run_info_path = root_path / "run_information.json"
    
    # register the model
    run_info = load_model_information(run_info_path)
    
    # get the run id
    run_id = run_info["run_id"]
    model_name = run_info["model_name"]
    artifact_path = run_info["artifact_path"]
    
    # model source path inside the tracked run artifacts
    model_source = f"{artifact_path.rstrip('/')}/{model_name}"
    
    client = MlflowClient()
    try:
        client.create_registered_model(model_name)
    except MlflowException:
        pass

    # register the model version from the logged artifact source
    model_version = client.create_model_version(
        name=model_name,
        source=model_source,
        run_id=run_id,
    )
    
    
    # get the model version
    registered_model_version = model_version.version
    registered_model_name = model_version.name
    logger.info(f"The latest model version in model registry is {registered_model_version}")
    
    # update the stage of the model to staging
    client = MlflowClient()
    client.transition_model_version_stage(
        name=registered_model_name,
        version=registered_model_version,
        stage="Staging"
    )
    
    logger.info("Model pushed to Staging stage")
    