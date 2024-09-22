#!/bin/bash

# Exit script if any command fails
set -e

# Define some variables
APP_DIR="$PWD"
VENV_DIR="$APP_DIR/venv"
SYSTEMD_SERVICE="/etc/systemd/system/binventory.service"

echo "Starting Binventory installation..."

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python3 could not be found. Please install Python3 and try again."
    exit
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found. Installing pip3..."
    python3 -m ensurepip --upgrade
fi

# Check if SQLite is installed
if ! command -v sqlite3 &> /dev/null
then
    echo "SQLite3 is not installed. Please install SQLite3 and try again."
    exit
fi

# Install virtualenv if not installed
if ! command -v virtualenv &> /dev/null
then
    echo "virtualenv could not be found, installing it..."
    pip install virtualenv
fi

# Create a virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    virtualenv -p python3 $VENV_DIR
fi

# Activate virtual environment
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

# Install required Python packages
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if Gunicorn is installed
if ! command -v gunicorn &> /dev/null
then
    echo "Gunicorn could not be found, installing it..."
    pip install gunicorn
fi

# Set up systemd service for production (optional)
if [ ! -f "$SYSTEMD_SERVICE" ]; then
    echo "Creating systemd service file..."
    sudo bash -c "cat > $SYSTEMD_SERVICE" << EOF
[Unit]
Description=Gunicorn instance to serve Binventory
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
EOF

    echo "Enabling and starting systemd service..."
    sudo systemctl daemon-reload
    sudo systemctl enable binventory
    sudo systemctl start binventory
else
    echo "Systemd service already exists, skipping creation..."
fi

# Get the IP address of the system
IP_ADDRESS=$(hostname -I | awk '{print $1}')

# Output the URL to access Binventory and default login info
echo ""
echo "BinVentory installation completed!"
echo "To start using BinVentory, go to: http://$IP_ADDRESS:5000"
echo "Default login credentials:"
echo "  Username: admin"
echo "  Password: password"
