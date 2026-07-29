import time
import torch
from diffusers import AutoPipelineForText2Image

print("PyTorch:", torch.__version__)
print("MPS:", torch.backends.mps.is_available())

pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=torch.float16,
    local_files_only=True,
)

pipe = pipe.to("mps")

start = time.time()

image = pipe(
    "A red apple on an old wooden table, photorealistic",
    num_inference_steps=1,
    guidance_scale=0.0,
).images[0]

print("Time:", round(time.time() - start, 2), "seconds")

image.save("apple.png")

print("Saved apple.png")
