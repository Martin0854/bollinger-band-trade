#!/bin/bash
# Example: Run backtest using the CLI

# Run with YAML config
poetry run python -m src.cli.main backtest --config examples/config_example.yaml

# Run with verbose logging
poetry run python -m src.cli.main backtest --config examples/config_example.yaml --verbose

# Note: The CLI currently requires mock data to be loaded.
# For full CLI support, you'll need to implement data fetching (User Story 3).
