# Starts the Book Visualizer website (Book Analyzer), version 2, at http://localhost:8502
# (version 1 lives in the "book analyzer" folder next to this one and uses port 8501,
# so both can run at the same time)
# Usage (from this folder):  .\run_website.ps1
#
# numpy's maths library (OpenBLAS) reserves memory for every CPU thread. With the
# Windows page file off, that can crash the site ("OpenBLAS error: Memory
# allocation still failed"). One thread is plenty: the AI models use PyTorch's own.
$env:OPENBLAS_NUM_THREADS = "1"
$port = 8502
# The addresses to open (Streamlit's own message is off: it looks up the public address online)
$lan = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1 -ExpandProperty IPAddress
Write-Host "Book Visualizer (v2): http://localhost:$port"
if ($lan) { Write-Host "On your phone (same Wi-Fi): http://${lan}:$port" }
# "python -m streamlit" rather than streamlit.exe: this .venv was copied from version 1, and
# its .exe launchers still point at version 1's Python; python.exe always uses this folder's
& "$PSScriptRoot\.venv\Scripts\python.exe" -m streamlit run "$PSScriptRoot\app\streamlit_app.py" --server.port $port @args
