import os
import sys
from langsmith import Client
from langsmith.evaluation import evaluate


sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from agent import process_customer_message

# 1. Create/select dataset
client = Client()
dataset_name = "case_dataset"

# 2. Define evaluator
def is_concise(outputs: dict, reference_outputs: dict) -> dict:
    out = outputs["output"]
    ref = reference_outputs["output"]
    score = len(out) < 2 * len(ref)
    return {"key": "is_concise", "score": int(score)}

def target_function(inputs: dict):
    answer = process_customer_message(inputs["message_content"], inputs["username"])  # returns a string
    return {"output": answer}

evaluate(
    target_function,
    data=client.list_examples(dataset_name=dataset_name, splits=["test1"]),
    evaluators=[is_concise],
    experiment_prefix="case_dataset_experiment",
    metadata = {"model_name": "gpt-4o"}
)