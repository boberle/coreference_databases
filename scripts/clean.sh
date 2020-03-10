rm fasttext_*_filtered
find -type d -name __pycache__ -exec rm -Rf '{}' \;
find -type f -name "*.pyc" -exec rm -Rf '{}' \;
