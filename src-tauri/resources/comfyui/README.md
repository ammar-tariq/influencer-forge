# ComfyUI bundle location

Clone or sync ComfyUI into `ComfyUI/` here (or set `IFORGE_COMFYUI_ROOT`):

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI
```

Then enable:

```bash
export IFORGE_ENABLE_COMFYUI=1
# optional model downloads
export IFORGE_ENABLE_MODEL_DOWNLOADS=1
```

Place checkpoints under the ComfyUI models directory or the app data `models/` folder according to your install.
Do not commit weight files into this repository.
