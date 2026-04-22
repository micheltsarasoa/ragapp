on uv run uvicorn main:app

error : 
File "C:\Users\iadev\repo\ragapp\.venv\Lib\site-packages\onnxruntime\capi\onnxruntime_inference_collection.py", line 599, in _create_inference_session
    sess = C.InferenceSession(session_options, self._model_path, True, self._read_config_from_model)
onnxruntime.capi.onnxruntime_pybind11_state.NoSuchFile: [ONNXRuntimeError] : 3 : NO_SUCHFILE : Load model from C:\Users\iadev\AppData\Local\Temp\6\fastembed_cache\models--qdrant--bge-small-en-v1.5-onnx-q\snapshots\52398278842ec682c6f32300af41344b1c0b0bb2\model_optimized.onnx failed:Load model C:\Users\iadev\AppData\Local\Temp\6\fastembed_cache\models--qdrant--bge-small-en-v1.5-onnx-q\snapshots\52398278842ec682c6f32300af41344b1c0b0bb2\model_optimized.onnx failed. File doesn't exist


Cause : 
The issue is that fastembed is trying to load a model from a corrupted/incomplete cache at C:\Users\iadev\AppData\Local\Temp\6\fastembed_cache\.

Fix: delete the incomplete cache and let fastembed re-download the model.

Run this in PowerShell or CMD:
Remove-Item -Recurse -Force "C:\Users\iadev\AppData\Local\Temp\6\fastembed_cache\models--qdrant--bge-small-en-v1.5-onnx-q"


Then retry:
> uv run uvicorn main:app



---

downloading blocks after uv run uvicorn main:app

add :
> $env:HF_TOKEN = "your_hf_token_here"
> uv run uvicorn main:app


cause : 
You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
2026-04-16 16:26:10,627 - WARNING - Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.