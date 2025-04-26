# Adaptive Cleaning Scheduler

An intelligent cleaning task scheduler that adapts to your energy levels and prioritizes tasks based on urgency and importance.

## Overview

The Adaptive Cleaning Scheduler is designed to help you manage household cleaning tasks in a way that respects your energy levels and mental health. Unlike traditional rigid cleaning schedules, this app uses an intelligent algorithm to recommend which tasks need attention based on their priority, when they were last completed, and how much energy you have available.

## Key Features

- **Energy-Adaptive Interface**: Select your current energy level (🔴 Low, 🟡 Moderate, 🟢 Good) to receive appropriate recommendations
- **Smart Task Prioritization**: Tasks are ranked by health importance, urgency, and time since last completion
- **Weekly Focus Rotation**: Automatically cycles through focus areas (Kitchen, Bathroom, Living Area, Bedroom/Pet) each week
- **Visual Progress Tracking**: Statistics dashboard shows completion rates and streaks
- **Multi-frequency Task Management**: Organizes daily, weekly, biweekly, monthly, and quarterly cleaning tasks

## How It Works

### Task Organization

Tasks are categorized by:
- **Priority**: From essential health/hygiene tasks to deep cleaning
- **Time Required**: 2-minute, 5-minute, 15-minute, and delegation tasks
- **Frequency**: Daily, weekly, biweekly, monthly, and quarterly tasks

### Urgency Calculation

The app calculates an urgency score for each task based on:
- Priority multiplier (higher priority tasks have greater weight)
- Overdue factor (days since last completion relative to expected frequency)

### Energy Level Adaptation

- **Red (Low Energy)**: Only shows essential tasks and limits the number of recommendations
- **Yellow (Moderate Energy)**: Shows a balanced set of high and medium priority tasks
- **Green (Good Energy)**: Provides a full range of tasks including variety options

## Getting Started

### Prerequisites

- Python 3.6 or higher
- Streamlit
- Pandas

### Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/adaptive-cleaning-scheduler.git
cd adaptive-cleaning-scheduler
```

2. Install the required packages:
```
pip install -r requirements.txt
```

3. Run the Streamlit app:
```
streamlit run app.py
```

## Using the App

1. Select your energy level for the day
2. Review the recommended tasks
3. Check off tasks as you complete them
4. Visit the statistics dashboard to track your progress
5. Reset tasks as needed for a fresh start

## File Structure

- `adaptive_cleaning_scheduler.py`: Core scheduler class with task logic
- `app.py`: Streamlit web interface

## Task Data

The app stores task completion history in JSON files:
- `cleaning_history.json`: Records when tasks were last completed
- `daily_tasks.json`: Stores daily task assignments

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Created for anyone who struggles with traditional cleaning schedules
- Inspired by compassionate approaches to home management

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## Contact

Your Name - [your.email@example.com](mailto:your.email@example.com)

Project Link: [https://github.com/yourusername/adaptive-cleaning-scheduler](https://github.com/yourusername/adaptive-cleaning-scheduler)
