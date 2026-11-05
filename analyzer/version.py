"""The version of the saved analyses, on its own so the website can read it without loading the
AI libraries (importing analyzer.pipeline loads torch, about 1 GB of memory)."""

# Bump this whenever BookAnalysis changes shape or the analysis changes, so
# results saved by an older version are re-analyzed instead of loaded
ANALYSIS_VERSION = 5  # 5: EmoLit's 38 fine emotions in 8 families
