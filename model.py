import torch as th
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

class PokemonFeatureExtractor(BaseFeaturesExtractor):
    """Custom PyTorch Feature Extractor for encoding Pokemon TCG state space."""
    def __init__(self, observation_space, features_dim=128):
        super().__init__(observation_space, features_dim)
        
        # Simple multi-layer perceptron to encode the 1D state representation vector
        self.encoder = nn.Sequential(
            nn.Linear(observation_space.shape[0], 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, features_dim),
            nn.ReLU()
        )

    def forward(self, observations: th.Tensor) -> th.Tensor:
        return self.encoder(observations)
