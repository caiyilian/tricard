import sys
sys.path.insert(0, r"E:\case\tricard\third_party\DouZero")

import torch
import numpy as np
from douzero.dmc.models import LandlordLstmModel, FarmerLstmModel

print("torch:", torch.__version__, "cuda:", torch.cuda.is_available())

z = torch.randn(2, 15, 162)
x = torch.randn(2, 373)
model = LandlordLstmModel().cuda()
out = model.forward(z.cuda(), x.cuda(), return_value=True)
v = out["values"].detach().cpu().numpy()
print("landlord value shape:", v.shape, "sample:", v[:, 0].tolist())

z2 = torch.randn(2, 15, 162)
x2 = torch.randn(2, 484)
model_f = FarmerLstmModel().cuda()
out2 = model_f.forward(z2.cuda(), x2.cuda(), return_value=True)
v2 = out2["values"].detach().cpu().numpy()
print("farmer value shape:", v2.shape, "sample:", v2[:, 0].tolist())

print("SMOKE OK: models instantiated and forward pass works")