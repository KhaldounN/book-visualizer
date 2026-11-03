# Starts the Book Analyzer website at http://localhost:8501
# Usage (from this folder):  .\run_website.ps1
#
# numpy's maths library (OpenBLAS) reserves memory for every CPU thread. With the
# Windows page file off, that can crash the site ("OpenBLAS error: Memory
# allocation still failed"). One thread is plenty: the AI models use PyTorch's own.
$env:OPENBLAS_NUM_THREADS = "1"
# The addresses to open (Streamlit's own message is off: it looks up the public address online)
$lan = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1 -ExpandProperty IPAddress
Write-Host "Book Analyzer: http://localhost:8501"
if ($lan) { Write-Host "On your phone (same Wi-Fi): http://${lan}:8501" }
& "$PSScriptRoot\.venv\Scripts\streamlit.exe" run "$PSScriptRoot\app\streamlit_app.py" --server.port 8501 @args
