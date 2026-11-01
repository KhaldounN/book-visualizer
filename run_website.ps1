# Starts the Book Analyzer website at http://localhost:8501
# Usage (from this folder):  .\run_website.ps1
#
# numpy's maths library (OpenBLAS) reserves memory for every CPU thread. With the
# Windows page file off, that can crash the site ("OpenBLAS error: Memory
# allocation still failed"). One thread is plenty: the AI models use PyTorch's own.
$env:OPENBLAS_NUM_THREADS = "1"
& "$PSScriptRoot\.venv\Scripts\streamlit.exe" run "$PSScriptRoot\app\streamlit_app.py" --server.port 8501 @args
