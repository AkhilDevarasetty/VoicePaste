import time
import config

t0 = time.time()
from transcriber import load_model

print(f"[{time.time() - t0:.1f}s] imports OK")
model = load_model()
print(f"[{time.time() - t0:.1f}s] model loaded: {type(model).__name__}")
print(f"   model_size = {config.MODEL_SIZE}, device = {config.DEVICE}, compute_type = {config.COMPUTE_TYPE}")
