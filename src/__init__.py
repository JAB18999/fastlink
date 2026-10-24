name: Market Analysis

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run market analysis
        run: |
          python scripts/run_analysis.py --symbol BTC-USDT-SWAP

      - name: Commit generated report
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add reports/
          git add data/
          if git diff --cached --quiet; then
            echo "No changes to commit."
          else
            git commit -m "chore: update market analysis report"
            git push
          fi
