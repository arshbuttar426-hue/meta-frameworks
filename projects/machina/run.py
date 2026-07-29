from diffusers import StableDiffusionXLPipeline
import torch, sys

prompt = sys.argv[1] if len(sys.argv) > 1 else "a cat"
out = sys.argv[2] if len(sys.argv) > 2 else "out.png"

pipe = StableDiffusionXLPipeline.from_pretrained(
    "SG161222/RealVisXL_V4.0",
    torch_dtype=torch.float16,
    use_safetensors=True,
    variant="fp16",
).to("mps")

image = pipe(prompt, num_inference_steps=25, width=1024, height=1024, guidance_scale=3.0).images[0]
image.save(out)
print(f"Saved {out}")
