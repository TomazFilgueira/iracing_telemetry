# 🏎️ Real-Time iRacing Strategy & Telemetry Deck

A professional-grade, real-time telemetry and strategy tool for **iRacing** developed with Python and Streamlit. This system provides sim racers and engineers with live performance metrics and fuel management data to optimize race-day decision-making.

---

## 🌟 Key Features

* **Performance Monitoring**: Track live lap times with an integrated moving average of the last 3 laps to identify pace trends and consistency.
* **Fuel Strategy Management**: Automatic calculation of fuel consumption per lap, remaining fuel, and projected fuel balance at the finish line.
* **Dynamic Session Projection**: Live estimation of laps remaining based on session time and current average pace.
* **Automated Session Management**: Intelligent file handling that creates unique session logs and automatically archives completed stints to keep your workspace clean.
* **Portable Configuration**: Centralized path management allows the project to run on any machine or directory without manual path adjustments.

---

## 🛠️ Technical Foundations

The application is built on **Python** and uses the **Streamlit** framework for a responsive, web-based interface. It leverages the **iRacing SDK** for high-frequency data polling and **Pandas** for real-time data processing. 

The pace estimation model assumes the race stint follows a **Wide-Sense Stationary (WSS)** process under consistent conditions, allowing for stable fuel and lap projections throughout the event.

[Image of a data flow diagram from a racing simulator to a telemetry server and a web dashboard]

---

## 🚀 Getting Started

### 1. Prerequisites
* **iRacing** installed and running.
* **Python 3.10+**.
* Required libraries:
    * `irsdk`: For simulator connectivity.
    * `streamlit`: For the web interface.
    * `pandas`: For data manipulation.

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone [https://github.com/your-username/your-repository.git](https://github.com/your-username/your-repository.git)
cd your-repository
pip install -r requirements.txt
```

## 🚀 Usage

The system is designed for high-efficiency operation during race sessions. You do not need to manually configure paths or open multiple terminals.

1. **Initialization**: Run `RACE_START.bat` from the project root after Iracing **opened**. This will automatically:
    * Start the telemetry collection engine in a dedicated background terminal.
    * Launch the Streamlit dashboard server.
    * Open the strategy interface in your default web browser.
2. **Monitoring**: Use the dashboard to track live lap trends, fuel consumption, and finish-line projections. Consider looking for local IP and access through mobile phone
3. **Termination**: Run `RACE_STOP.bat` once your stint is complete. This script will:
    * Safely terminate all active telemetry and dashboard processes.
    * Automatically archive the current session log to the historical storage folder.

---

## 📁 Project Structure

The project follows a modular architecture to ensure data integrity and ease of testing across different hardware setups.

* **`read_iracing.py`**: The core data polling engine. It interfaces with the simulator SDK, calculates moving averages, and handles real-time data persistence.
* **`dashboard.py`**: The visual strategy deck. It automatically detects the most recent session file and renders interactive charts and KPIs.
* **`config.py`**: The centralized configuration hub. It manages relative paths and global variables to ensure portability.
* **`Data_Logs/`**: Directory dedicated to the active session data. This folder is monitored by the dashboard for real-time updates.
* **`concluded_sessions/`**: A historical archive where completed stints are moved after the session ends for long-term storage and analysis.
