<div align="center">
  <img width="500" alt="Header" src="https://raw.githubusercontent.com/chrisjameschamp/BinVentory/43aa6fc07bb1d9b85e73453515033b397f0bdf21/static/images/Full_Row.svg">
</div>
<div align="center">
  
  ![GitHub documentation](https://img.shields.io/badge/documentation-yes-brightgreen.svg?style=flat-square)
  ![GitHub issues](https://img.shields.io/github/issues/chrisjameschamp/BinVentory)
  ![GitHub pull requests](https://img.shields.io/github/issues-pr/chrisjameschamp/BinVentory)
  ![GitHub](https://img.shields.io/github/license/chrisjameschamp/BinVentory)
  ![GitHub repo size](https://img.shields.io/github/repo-size/chrisjameschamp/BinVentory?style=flat-square)
  ![Github repo languages](https://img.shields.io/github/languages/count/chrisjameschamp/BinVentory?style=flat-square)
  ![Github repo top lang](https://img.shields.io/github/languages/top/chrisjameschamp/BinVentory?style=flat-square)
  ![Python](https://img.shields.io/badge/python-3.11%2B-blue)
  ![GitHub license](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)
  ![GitHub last commit](https://img.shields.io/github/last-commit/chrisjameschamp/BinVentory?style=flat-square)


</div>

**BinVentory** is a lightweight, easy-to-use inventory management system designed for organizing and tracking items in storage bins. It features a simple web interface where users can add, edit, move, and delete locations, bins, and items. This project is powered by Flask, uses SQLite for data persistence, and is deployed with Gunicorn in production.

## Features

-   **User Authentication**: Includes admin user login with PIN-based authentication after inactivity.
-   **Inventory Organization**: Manage locations and their associated bins, and easily categorize and track items.
-   **Search Functionality**: Quickly find locations, bins, and items using a global search that supports both names and bin numbers.
-   **QR Code Scanning**: Use the built-in QR scanner to access bins and items quickly.
-   **Account Management**: Change username, password, and PIN from the account settings page.
-   **Session Management**: After 30 minutes of inactivity, users must re-authenticate with a PIN to resume their session.
-   **Mobile Support**: Responsive UI designed to work on both desktop and mobile devices.

## Installation

To set up and run BinVentory, follow the instructions below.

### 1. Prerequisites

Ensure you have the following software installed on your machine:

-   **Python 3.x** (preferably 3.7+)
-   **SQLite 3**
-   **pip** (Python package installer)
-   **virtualenv** (Python virtual environment manager)

### 2. Clone the repository

`git clone git@github.com:chrisjameschamp/BinVentory.git
cd BinVentory` 

### 3. Run the installation script

Run the provided `install.sh` script to install dependencies and set up the virtual environment, database, and Gunicorn service.

`chmod +x install.sh
./install.sh` 

### 4. Start the application

Once installed, BinVentory will run automatically as a systemd service using Gunicorn. You can access the application by going to:

`http://<your-machine-ip>:5000` 

Default login credentials:

-   **Username**: `admin`
-   **Password**: `password`
-   **PIN**: `1234`

## Usage

### 1. Home Page

The home page shows a list of all locations. From here, you can:

-   **Add new locations** by clicking the "+" button.
-   **Click on a location** to view the bins associated with that location.

### 2. Bin Management

Each location page displays the bins associated with that location. For each bin, you can:

-   **Add, edit, or delete bins**.
-   **Move bins** between locations.
-   **Click on a bin** to view the items inside it.

### 3. Item Management

Within each bin, you can manage items:

-   **Add, edit, or delete items**.
-   **Move items** between bins.

### 4. QR Code Scanning

You can scan a QR code to directly access a bin using the **Scan QR Code** button in the navigation bar. This feature is mobile-friendly.

### 5. Account Settings

Click on **Account Settings** in the top-right corner of the page to:

-   Change your **username**.
-   Update your **password**.
-   Update your **PIN** for quick re-authentication.

### 6. Session Timeout

After 30 minutes of inactivity, you will be asked to re-enter your PIN to resume your session.

## Deployment

For production, the `install.sh` script sets up a **Gunicorn** server managed by **systemd**. If you wish to redeploy or restart the service:

`sudo systemctl restart binventory` 

## Contributing

If you'd like to contribute, please open a pull request or an issue on GitHub. We welcome contributions to improve the project!

## License

This project is licensed under the MIT License.