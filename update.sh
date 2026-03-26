#!/bin/bash

set -e  # Exit on any error

# Activate virtual environment
source ~/ProjectEPU/venv/bin/activate

# Go to project folder
cd ~/ProjectEPU

# Stash any local changes (optional)
git stash

# Pull latest code from GitHub
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Run Alembic migrations (must run BEFORE restart)
echo "Running alembic migrations..."
if python -m alembic upgrade head; then
    echo "✅ Migrations completed successfully"
else
    echo "⚠️  Warning: Alembic migration failed - service will restart with current schema"
    echo "You may need to run 'python -m alembic upgrade head' manually after investigating the error"
fi

# Restart service (use correct service name: projectepu, not epu)
echo "Restarting projectepu service..."
sudo systemctl restart projectepu

# Check service status
sudo systemctl status projectepu

echo "✅ Update complete!"
