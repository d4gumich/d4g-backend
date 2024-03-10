# NEW DISASTER DETECTION
# @author: Takao Kakegawa

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import scipy.sparse as sp

import torch
from torch import nn

# List of disaster types stated officially by ReliefWeb
disaster_types = ['Cold Wave','Drought','Earthquake','Epidemic','Extratropical Cyclone',
 'Fire','Flash Flood','Flood','Heat Wave','Insect Infestation','Land Slide','Mud Slide',
 'Other','Severe Local Storm','Snow Avalanche','Storm Surge','Technological Disaster',
 'Tropical Cyclone','Tsunami','Volcano','Wild Fire']


device = ("cpu")

# Neural Network framework
class NeuralNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear_relu_stack = nn.Sequential(
            nn.Linear(3679, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 21),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.linear_relu_stack(x)
        x = torch.round(x)
        return x

model = NeuralNetwork()
# Load in trained neural network
model.load_state_dict(torch.load('disaster_detection_NN.pth'))

def disaster_prediction(text, vectorizer):
  ''' returns predicted disaster type labels from trained NN classifier model.
      @type: str
      @param text: body text of report
      @type: str
      @param path to vectorizer
      @rtype: list
      @rparam: list of disaster types predicted by NN model.
    '''
  tfidf = joblib.load(vectorizer)
  text_vec = torch.tensor(sp.csr_matrix.todense(tfidf.transform([text]))).float()
  with torch.no_grad():
    pred = model(text_vec)[0]
    pred = torch.round(pred.gt(0.35).float()).numpy()
  disasters = [disaster for disaster, val in zip(disaster_types, pred) if val == 1]
  return disasters