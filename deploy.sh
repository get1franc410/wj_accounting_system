#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- CONFIGURATION ---
# These are the variables for your PythonAnywhere setup.
PA_USERNAME="joshuaadeyanju410"
PA_PROJECT_PATH="/home/joshuaadeyanju410/wj_accounting_system"
PA_VENV_PATH="/home/joshuaadeyanju410/wj_accounting_venv"
PA_WSGI_FILE="/var/www/joshuaadeyanju410_pythonanywhere_com_wsgi.py"
GIT_BRANCH="main"


# --- SCRIPT LOGIC ---

# 1. Check for a commit message
if [ -z "$1" ]; then
  echo "❌ ERROR: No commit message provided."
  echo "Usage: ./deploy.sh \"Your commit message\""
  exit 1
fi

echo "✅ Step 1: Starting deployment process..."

# 2. Add, commit, and push changes to GitHub
echo "🔄 Step 2: Committing and pushing changes to GitHub..."
git add .
git commit -m "$1"
git push origin $GIT_BRANCH
echo "✅ Git push to '$GIT_BRANCH' branch successful."

# 3. Connect to PythonAnywhere and run update commands
echo "🔄 Step 3: Connecting to PythonAnywhere to deploy updates..."

# This corrected block passes all commands as a single string to ssh.
# This is more reliable than the previous method.
ssh ${PA_USERNAME}@ssh.pythonanywhere.com "
  set -e # Stop the script if any command fails on the server

  echo '  - Navigating to project directory...'
  cd ${PA_PROJECT_PATH}

  echo '  - Pulling latest changes from GitHub...'
  git pull origin ${GIT_BRANCH}

  echo '  - Installing/updating Python packages...'
  ${PA_VENV_PATH}/bin/pip install -r requirements.txt

  echo '  - Applying database migrations...'
  ${PA_VENV_PATH}/bin/python manage.py migrate

  echo '  - Collecting static files...'
  ${PA_VENV_PATH}/bin/python manage.py collectstatic --noinput

  echo '  - Reloading web application...'
  touch ${PA_WSGI_FILE}
"

echo "✅ Deployment to PythonAnywhere complete."
echo "🚀🚀🚀 ALL DONE! Your website should now be live with the latest updates. 🚀🚀🚀"
