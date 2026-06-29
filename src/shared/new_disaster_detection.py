# NEW DISASTER DETECTION
# @author: Takao Kakegawa

import gc
import logging
from typing import Any

logger = logging.getLogger(__name__)

# List of disaster types stated officially by ReliefWeb
disaster_types = [
    "Cold Wave",
    "Drought",
    "Earthquake",
    "Epidemic",
    "Extratropical Cyclone",
    "Fire",
    "Flash Flood",
    "Flood",
    "Heat Wave",
    "Insect Infestation",
    "Land Slide",
    "Mud Slide",
    "Other",
    "Severe Local Storm",
    "Snow Avalanche",
    "Storm Surge",
    "Technological Disaster",
    "Tropical Cyclone",
    "Tsunami",
    "Volcano",
    "Wild Fire",
]

# Cache for models and vectorizers
_model_cache: dict[str, Any] = {}


def disaster_prediction(text, vectorizer_path, model_path):
    """returns predicted disaster type labels from trained NN classifier model.
    @type: str
    @param text: body text of report
    @type: str
    @param vectorizer_path: path to vectorizer
    @type: str
    @param model_path: path to model
    @rtype: list
    @rparam: list of disaster types predicted by NN model.
    """
    import joblib
    import scipy
    import torch

    # Load Model (cached)
    if model_path not in _model_cache:
        logger.info(f"Loading Disaster Detection model from {model_path}...")

        # Define NeuralNetwork class inline to avoid top-level torch import
        class NeuralNetwork(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.linear_relu_stack = torch.nn.Sequential(
                    torch.nn.Linear(3679, 512),
                    torch.nn.ReLU(),
                    torch.nn.Linear(512, 512),
                    torch.nn.ReLU(),
                    torch.nn.Linear(512, 128),
                    torch.nn.ReLU(),
                    torch.nn.Linear(128, 21),
                    torch.nn.Sigmoid(),
                )

            def forward(self, x):
                x = self.linear_relu_stack(x)
                x = torch.round(x)
                return x

        model = NeuralNetwork()
        model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
        model.eval()  # Set to evaluation mode
        _model_cache[model_path] = model
    model = _model_cache[model_path]

    # Load Vectorizer (cached)
    if vectorizer_path not in _model_cache:
        logger.info(f"Loading Disaster Detection vectorizer from {vectorizer_path}...")
        _model_cache[vectorizer_path] = joblib.load(vectorizer_path)
    tfidf = _model_cache[vectorizer_path]

    # Vectorize and Predict
    with torch.no_grad():
        text_vec = torch.tensor(scipy.sparse.csr_matrix.todense(tfidf.transform([text]))).float()
        pred = model(text_vec)[0]
        pred = torch.round(pred.gt(0.35).float()).numpy()

    disasters = [disaster for disaster, val in zip(disaster_types, pred) if val == 1]

    # Cleanup local variables, but keep the cache
    del text_vec
    del pred
    gc.collect()

    return disasters
