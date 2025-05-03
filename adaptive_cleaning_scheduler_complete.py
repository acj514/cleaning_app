import random
import datetime
from typing import List, Dict, Tuple, Union, Any
import os
import json
import streamlit as st
import pandas as pd


class AdaptiveCleaningScheduler:
    def __init__(self, username="default", history_file=None, daily_tasks_file=None):
        # Always provide string values for file paths
        if history_file is None:
            history_file = f"{username}_cleaning_history.json"
        if daily_tasks_file is None:
            daily_tasks_file = f"{username}_daily_tasks.json"

        self.history_file = history_file
        self.daily_tasks_file = daily_tasks_file

        # Path to files storing task history and daily assignments
        self.history_file = history_file
        self.daily_tasks_file = daily_tasks_file

        # Get the current date
        today = datetime.date.today()
        self.current_date = today
        self.day_of_week = today.strftime("%A")

        # Use week of the year instead of week of month
        self.week_of_year = today.isocalendar()[1]

        # Weekly focus now rotates based on week of year
        focus_rotation = ["Kitchen", "Bathroom", "Living Area", "Bedroom/Pet"]
        self.current_focus = focus_rotation[(self.week_of_year - 1) % len(focus_rotation)]

        # Calculate quarter (1-4)
        self.current_quarter = (today.month - 1) // 3 + 1

        # Initialize task lists by priority, time required, and frequency
        self.tasks, self.task_metadata = self._initialize_tasks()

        # Track when tasks were last done
        self.task_history = self._load_task_history()

        # Load or generate today's task assignments
        self.daily_task_assignments = self._load_or_generate_daily_tasks()

    def _load_task_history(self) -> Dict:
        """Load task history from file or create new if doesn't exist"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}  # Return empty dict if file doesn't exist or is invalid

    def _save_task_history(self):
        """Save task history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.task_history, f, indent=2)

    def _load_or_generate_daily_tasks(self) -> Dict:
        """Load today's task assignments or generate new ones if needed"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        try:
            with open(self.daily_tasks_file, 'r') as f:
                daily_tasks = json.load(f)

            # Check if we have tasks for today
            if today_str in daily_tasks:
                return daily_tasks
            else:
                # Generate new tasks for today
                daily_tasks[today_str] = self._generate_todays_tasks()
                with open(self.daily_tasks_file, 'w') as f:
                    json.dump(daily_tasks, f, indent=2)
                return daily_tasks

        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is invalid, create new
            daily_tasks = {today_str: self._generate_todays_tasks()}
            with open(self.daily_tasks_file, 'w') as f:
                json.dump(daily_tasks, f, indent=2)
            return daily_tasks

    def _generate_todays_tasks(self) -> Dict:
        """Generate task assignments for today"""
        # Generate daily tasks for all energy levels
        daily_tasks_red = self._generate_daily_tasks("red")
        daily_tasks_yellow = self._generate_daily_tasks("yellow")
        daily_tasks_green = self._generate_daily_tasks("green")

        # Generate weekly focus tasks for all energy levels
        weekly_tasks_red = self._generate_weekly_focus_tasks("red")
        weekly_tasks_yellow = self._generate_weekly_focus_tasks("yellow")
        weekly_tasks_green = self._generate_weekly_focus_tasks("green")

        # Generate biweekly tasks (sort by days since completion)
        if self.week_of_year % 2 == 0:
            biweekly_tasks = self.biweekly_tasks["weeks1_2"]
        else:
            biweekly_tasks = self.biweekly_tasks["weeks3_4"]

        # Filter biweekly tasks based on their frequency
        biweekly_tasks = [t for t in biweekly_tasks if self.is_task_due(t)]

        if not biweekly_tasks:
            biweekly_tasks = ["🎉 No biweekly tasks needed today!"]

        # Sort remaining by urgency score
        biweekly_tasks.sort(key=lambda t: self.get_task_urgency_score(t), reverse=True)

        # Generate monthly tasks
        monthly_tasks = self.get_monthly_task()

        # Get quarterly focus
        quarterly_task = self.get_quarterly_task()

        # Variety tasks pulled from all priorities for green energy days
        variety_tasks = []
        all_variety_sources = []
        for priority in ["priority2", "priority3"]:
            for time_category in ["2min", "5min", "15min"]:
                all_variety_sources.extend(self.tasks[priority][time_category])

        # Filter variety tasks based on frequency and urgency
        variety_tasks = [t for t in all_variety_sources if self.is_task_due(t)]
        variety_tasks.sort(key=lambda t: self.get_task_urgency_score(t), reverse=True)
        variety_tasks = variety_tasks[:10]

        # Create the task assignments dictionary
        task_assignments = {
            "date": self.current_date.strftime("%Y-%m-%d"),
            "day_of_week": self.day_of_week,
            "daily_tasks": {
                "red": daily_tasks_red,
                "yellow": daily_tasks_yellow,
                "green": daily_tasks_green
            },
            "weekly_tasks": {
                "red": weekly_tasks_red,
                "yellow": weekly_tasks_yellow,
                "green": weekly_tasks_green
            },
            "biweekly_tasks": biweekly_tasks,
            "monthly_tasks": monthly_tasks,
            "quarterly_task": quarterly_task,
            "variety_tasks": variety_tasks,
        }

        return task_assignments

    def _generate_daily_tasks(self, energy_level="red") -> List[str]:
        essential_tasks = {
            "Monday": "Clear and wipe kitchen counters",
            "Tuesday": "Pick up floor clutter in all rooms",
            "Wednesday": "Take out trash and recycling",
            "Thursday": "Clean coffee table",
            "Friday": "Wipe bathroom sink and toilet quick-clean",
            "Saturday": "Vacuum main living space",
            "Sunday": "Quick-sort mail and clear entryway"
        }

        tasks = []

        # Always recommend the essential task for today first
        essential_task = essential_tasks.get(self.day_of_week)
        if essential_task:
            tasks.append(essential_task)

            # Build a list of potential tasks sorted by urgency
            potential_tasks = []

            # Gather tasks from all priority1 time categories
            for time_category in ["2min", "5min", "15min"]:
                for task in self.tasks["priority1"][time_category]:
                    # Skip the day's essential task if it's in the list
                    if task == essential_task:
                        continue

                    # Only include due tasks
                    if self.is_task_due(task):
                        # Calculate urgency score and add to potential tasks
                        score = self.get_task_urgency_score(task)
                        potential_tasks.append((task, score))

            # Sort by urgency score (highest first)
            potential_tasks.sort(key=lambda x: x[1], reverse=True)

            # Choose how many bonus tasks to add based on energy level
            num_bonus_tasks = {
                "red": 2,  # 2 extras
                "yellow": 4,  # 4 extras
                "green": 8  # 8 extras
            }.get(energy_level, 2)

            # Add the highest scoring tasks
            tasks.extend([task for task, _ in potential_tasks[:num_bonus_tasks]])

        return tasks

    def _generate_weekly_focus_tasks(self, energy_level="yellow") -> List[str]:
        """Generate weekly focus tasks based on energy level and current focus area"""
        current_focus = self.current_focus
        tasks = []

        # Define weekly tasks for each focus area
        if current_focus == "Kitchen":
            weekly_tasks = [
                "Wipe down kitchen counters completely",
                "Quick-clean inside microwave with damp cloth",
                "Wipe refrigerator handles and most-touched shelves"
            ]
        elif current_focus == "Bathroom":
            weekly_tasks = [
                "Clean bathroom sink, faucet, and immediate counter area",
                "Scrub toilet bowl and wipe exterior surfaces",
                "Replace bathroom hand/face towels"
            ]
        elif current_focus == "Living Area":
            weekly_tasks = [
                "Quick-tidy living room sitting area",
                "Gather and put away items that belong in another room",
                "Clear and wipe dining/coffee table completely"
            ]
        else:  # Bedroom/Pet
            weekly_tasks = [
                "Organize nightstand for better function",
                "Sort through one drawer of clothing",
                "Clean litter box completely"
            ]

        # Filter out tasks that aren't due based on their frequency
        weekly_tasks = [t for t in weekly_tasks if self.is_task_due(t)]

        # If no tasks left, celebrate!
        if not weekly_tasks:
            return ["🎉 No weekly focus tasks needed today!"]

        # Sort tasks by urgency score
        weekly_tasks.sort(key=lambda t: self.get_task_urgency_score(t), reverse=True)

        # Recommend tasks based on energy level
        if energy_level == "red":
            # On red days, just recommend one task
            if weekly_tasks:
                tasks.append(weekly_tasks[0])
        elif energy_level == "yellow":
            # On yellow days, recommend 2 tasks
            tasks.extend(weekly_tasks[:2])
        else:  # green
            # On green days, recommend all tasks
            tasks.extend(weekly_tasks)

        return tasks

    def _initialize_tasks(self) -> Tuple[Dict, Dict]:
        """Initialize all cleaning tasks with priority, time, and frequency"""
        # Create frequency thresholds for determining when tasks are due
        frequency_thresholds = {
            "daily": 3,  # Due if not done in 2 days
            "weekly": 10,  # Due if not done in 7 days
            "biweekly": 18,  # Due if not done in 14 days
            "monthly": 35,  # Due if not done in 30 days
            "quarterly": 100  # Due if not done in 90 days
        }

        # Priority multipliers for urgency calculation
        priority_multipliers = {
            "priority1": 3.0,
            "priority2": 2.0,
            "priority3": 1.0,
            "priority4": 0.5
        }

        # Task metadata containing frequency and priority information
        task_metadata = {}

        # Regular tasks organized by priority and time
        tasks = {
            "priority1": {
                "2min": [
                    "Wipe bathroom sink",  # daily
                    "Check and clear clutter from hallway or entryway",  # daily
                    "Quick-sort mail",  # daily
                    "Wipe down bathroom faucet",  # daily
                    "Put shoes in closet or bin",  # daily
                    "Quick-wipe toilet seat and rim" # daily
                ],
                "5min": [
                    "Unload dishwasher",  # daily
                    "Scoop cat litter",  # daily
                    "Clear and wipe kitchen counters",  # daily
                    "Pick up floor clutter in main rooms",  # daily
                    "Take out trash if full",  # daily
                    "Clear kitchen and bathroom floors of objects"  # daily
                ],
                "15min": [
                    "Vacuum main living space",  # daily if possible
                    "Load dishwasher and run if full",  # daily
                    "Wipe down stovetop",  # daily
                    "Empty and wipe bathroom trash if full",  # daily
                    "Clean coffee table"  # daily
                ]
            },
            "priority2": {
                "2min": [
                    "Replace kitchen towel",  # weekly
                    "Tidy couch cushions and blanket",  # weekly
                    "Water houseplants",  # weekly
                    "Wipe down door handles",  # weekly
                    "Refill toilet paper or soap"  # weekly
                ],
                "5min": [
                    "Wipe down appliances",  # weekly
                    "Quick clean one mirror",  # weekly
                    "Tidy one shelf or counter",  # weekly
                    "Change pillowcases",  # weekly
                    "Clean out one fridge shelf"  # weekly
                ],
                "15min": [
                    "Mop kitchen and bathroom floors",  # weekly
                    "Change bed sheets",  # weekly
                    "Vacuum rugs",  # weekly
                    "Wipe switches and doorknobs",  # weekly
                    "Clean bathroom toilet and sink thoroughly"  # weekly
                ]
            },
            "priority3": {
                "2min": [
                    "Dust light fixtures",  # biweekly
                    "Dust electronics",  # biweekly
                    "Straighten bathroom items",  # biweekly
                    "Spot check corners for cobwebs",  # biweekly
                    "Check expiration dates on fridge items"  # biweekly
                ],
                "5min": [
                    "Wipe cabinet fronts",  # biweekly
                    "Clean cat food area",  # biweekly
                    "Wipe fridge handle and exterior",  # biweekly
                    "Organize one drawer",  # biweekly
                    "Wipe baseboards in one room"  # biweekly
                ],
                "15min": [
                    "Dust entire bedroom or office",  # monthly
                    "Clean out medicine cabinet",  # monthly
                    "Reorganize pantry zone",  # monthly
                    "Clean behind microwave",  # monthly
                    "Deep clean one small appliance"  # monthly
                ]
            },
            "priority4": {
                "15min": [
                    "Vacuum under couch",  # quarterly
                    "Dust and rotate books",  # quarterly
                    "Wipe window tracks",  # quarterly
                    "Clean washing machine filter",  # quarterly
                    "Check fire alarm batteries"  # quarterly
                ],
                "delegate": [
                    "Clean behind large appliances",  # quarterly
                    "Organize storage closet",  # quarterly
                    "Sort donation bin",  # quarterly
                    "Clean ceiling fan blades",  # quarterly
                    "Wash curtains or blinds"  # quarterly
                ]
            }
        }


        # Assign frequency to each task
        # Priority 1, 2min tasks are mostly daily
        for task in tasks["priority1"]["2min"]:
            frequency = "daily"
            if task in ["Replace kitchen hand towel with fresh one",
                        "Empty bathroom trash if contains hygiene products", "Clean toilet seat with disposable wipe"]:
                frequency = "biweekly"
            task_metadata[task] = {
                "frequency": frequency,
                "threshold_days": frequency_thresholds[frequency],
                "priority": "priority1",
                "priority_multiplier": priority_multipliers["priority1"],
                "time": "2min"
            }

        # Priority 1, 5min tasks are mostly weekly
        for task in tasks["priority1"]["5min"]:
            frequency = "weekly"
            task_metadata[task] = {
                "frequency": frequency,
                "threshold_days": frequency_thresholds[frequency],
                "priority": "priority1",
                "priority_multiplier": priority_multipliers["priority1"],
                "time": "5min"
            }

        # Priority 1, 15min tasks are mostly biweekly
        for task in tasks["priority1"]["15min"]:
            frequency = "biweekly"
            task_metadata[task] = {
                "frequency": frequency,
                "threshold_days": frequency_thresholds[frequency],
                "priority": "priority1",
                "priority_multiplier": priority_multipliers["priority1"],
                "time": "15min"
            }

        # Priority 2, 2min tasks are weekly
        for task in tasks["priority2"]["2min"]:
            frequency = "weekly"
            task_metadata[task] = {
                "frequency": frequency,
                "threshold_days": frequency_thresholds[frequency],
                "priority": "priority2",
                "priority_multiplier": priority_multipliers["priority2"],
                "time": "2min"
            }

        # Priority 2, 5min tasks are biweekly
        for task in tasks["priority2"]["5min"]:
            frequency = "biweekly"
            task_metadata[task] = {
                "frequency": frequency,
                "threshold_days": frequency_thresholds[frequency],
                "priority": "priority2",
                "priority_multiplier": priority_multipliers["priority2"],
                "time": "5min"
            }

        # Priority 2, 15min tasks are monthly
        for task in tasks["priority2"]["15min"]:
            frequency = "monthly"
            task_metadata[task] = {
                "frequency": frequency,
                "threshold_days": frequency_thresholds[frequency],
                "priority": "priority2",
                "priority_multiplier": priority_multipliers["priority2"],
                "time": "15min"
            }

        # Priority 3 tasks are mostly monthly
        for time_cat in ["2min", "5min", "15min"]:
            for task in tasks["priority3"][time_cat]:
                frequency = "monthly"
                task_metadata[task] = {
                    "frequency": frequency,
                    "threshold_days": frequency_thresholds[frequency],
                    "priority": "priority3",
                    "priority_multiplier": priority_multipliers["priority3"],
                    "time": time_cat
                }

        # Priority 4 tasks are quarterly
        for time_cat in ["15min", "delegate"]:
            for task in tasks["priority4"][time_cat]:
                frequency = "quarterly"
                task_metadata[task] = {
                    "frequency": frequency,
                    "threshold_days": frequency_thresholds[frequency],
                    "priority": "priority4",
                    "priority_multiplier": priority_multipliers["priority4"],
                    "time": time_cat
                }

        # Biweekly task sets
        self.biweekly_tasks = {
            "weeks1_2": [
                "Full shower/tub cleaning",
                "Complete toilet cleaning (bowl, tank, base, surrounding floor)",
                "Full kitchen counter and sink cleaning"
            ],
            "weeks3_4": [
                "Change bed linens (fitted sheet, pillowcases)",
                "Refrigerator clean-out of expired foods",
                "Kitchen sink deep clean including disposal and drain"
            ]
        }

        # Make sure biweekly tasks have metadata
        for week_set in self.biweekly_tasks.values():
            for task in week_set:
                if task not in task_metadata:
                    task_metadata[task] = {
                        "frequency": "biweekly",
                        "threshold_days": frequency_thresholds["biweekly"],
                        "priority": "priority1",
                        "priority_multiplier": priority_multipliers["priority1"],
                        "time": "15min"
                    }

        # Quarterly focus areas
        self.quarterly_focus = {
            1: "Bathroom deep clean (grout, fans, etc.)",
            2: "Kitchen deep clean (inside appliances, etc.)",
            3: "Living areas deep clean (under furniture, etc.)",
            4: "Bedroom deep clean (mattress, closets, etc.)"
        }

        # Add quarterly tasks metadata
        for _, task in self.quarterly_focus.items():
            task_metadata[task] = {
                "frequency": "quarterly",
                "threshold_days": frequency_thresholds["quarterly"],
                "priority": "priority4",
                "priority_multiplier": priority_multipliers["priority4"],
                "time": "delegate"
            }

        return tasks, task_metadata

    def get_days_since_task_completion(self, task_name):
        record = self.task_history.get(task_name)
        if not record or "last_done" not in record:
            return float('inf')  # Treat as never done
        try:
            last_done = datetime.datetime.strptime(record["last_done"], "%Y-%m-%d").date()
            return (datetime.date.today() - last_done).days
        except Exception:
            return float('inf')


    def is_task_due(self, task_name):
        """Check if a task is due based on its frequency"""
        # Skip celebration messages
        if task_name.startswith("🎉"):
            return False

        days_since = self.get_days_since_task_completion(task_name)

        # Get the threshold for this task
        if task_name in self.task_metadata:
            threshold = self.task_metadata[task_name]["threshold_days"]
        else:
            # Default to weekly if not found
            threshold = 7

        return days_since >= threshold

    def get_task_urgency_score(self, task_name):
        """Calculate an urgency score based on days since last completion and priority"""
        # Skip celebration messages
        if task_name.startswith("🎉"):
            return 0

        days_since = self.get_days_since_task_completion(task_name)

        if task_name in self.task_metadata:
            metadata = self.task_metadata[task_name]
            threshold = metadata["threshold_days"]
            priority_multiplier = metadata["priority_multiplier"]
        else:
            # Default values if metadata not found
            threshold = 10
            priority_multiplier = 1.0

        # Calculate overdue factor (how many times over the threshold)
        # Min value of 0.1 ensures tasks not yet due still have some score
        overdue_factor = max(0.1, days_since / threshold)

        # Final score calculation
        score = overdue_factor * priority_multiplier

        return score

    def was_task_done_recently(self, task_name, days_threshold):
        """Return True if the task was completed within days_threshold"""
        days_since = self.get_days_since_task_completion(task_name)
        return days_since < days_threshold

    def mark_task_completed(self, task_name, notes=""):
        """Mark a task as completed today with optional notes"""
        if task_name not in self.task_history:
            self.task_history[task_name] = {
                "completion_count": 0,
                "completion_dates": []
            }

        # Update the task history
        self.task_history[task_name]["last_done"] = self.current_date.strftime("%Y-%m-%d")
        self.task_history[task_name]["completion_count"] = self.task_history[task_name].get("completion_count", 0) + 1

        # Add to completion dates list
        if "completion_dates" not in self.task_history[task_name]:
            self.task_history[task_name]["completion_dates"] = []

        completion_entry = {
            "date": self.current_date.strftime("%Y-%m-%d"),
            "notes": notes
        }

        self.task_history[task_name]["completion_dates"].append(completion_entry)

        # Save the updated history
        self._save_task_history()

        print(f"✅ Task marked as completed: {task_name}")

    def get_task_stats(self, task_name):
        """Get statistics for a specific task"""
        if task_name not in self.task_history:
            return {
                "task": task_name,
                "ever_completed": False,
                "completion_count": 0,
                "last_done": "Never",
                "days_since_completion": float('inf')
            }

        days_since = self.get_days_since_task_completion(task_name)

        return {
            "task": task_name,
            "ever_completed": True,
            "completion_count": self.task_history[task_name]["completion_count"],
            "last_done": self.task_history[task_name]["last_done"],
            "days_since_completion": days_since
        }

    def get_daily_tasks(self, energy_level="red") -> List[str]:
        """Get today's daily tasks based on energy level from the saved task assignments"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        # Get tasks from the saved daily assignments
        if today_str in self.daily_task_assignments:
            return self.daily_task_assignments[today_str]["daily_tasks"][energy_level]
        else:
            # Fallback to generating new tasks
            return self._generate_daily_tasks(energy_level)

    def get_weekly_focus_tasks(self, energy_level="yellow") -> List[str]:
        """Get today's weekly focus tasks based on energy level from the saved task assignments"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        # Get tasks from the saved daily assignments
        if today_str in self.daily_task_assignments:
            return self.daily_task_assignments[today_str]["weekly_tasks"][energy_level]
        else:
            # Fallback to generating new tasks
            return self._generate_weekly_focus_tasks(energy_level)

    def get_biweekly_tasks(self) -> List[str]:
        """Get today's biweekly tasks from the saved task assignments"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        # Get tasks from the saved daily assignments
        if today_str in self.daily_task_assignments:
            return self.daily_task_assignments[today_str]["biweekly_tasks"]
        else:
            # Fallback to generating new tasks
            if self.week_of_year % 2 == 0:
                tasks = self.biweekly_tasks["weeks1_2"]
            else:
                tasks = self.biweekly_tasks["weeks3_4"]

            # Filter for due tasks
            tasks = [t for t in tasks if self.is_task_due(t)]

            # If no tasks left, return celebration message
            if not tasks:
                return ["🎉 No biweekly tasks needed today!"]

            # Sort by urgency score
            tasks.sort(key=lambda t: self.get_task_urgency_score(t), reverse=True)
            return tasks[:4]

    def get_monthly_task(self) -> List[str]:
        """Get today's monthly visual impact tasks from the saved task assignments"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        # Prevent circular reference during initialization
        if hasattr(self, 'daily_task_assignments') and today_str in self.daily_task_assignments:
            monthly_task = self.daily_task_assignments[today_str].get("monthly_task", [])
            if isinstance(monthly_task, str):
                return [monthly_task] if monthly_task else []
            return monthly_task

        # If not available yet, generate fresh list of monthly candidates
        monthly_tasks = []
        for priority in ["priority1", "priority2", "priority3"]:
            for time_category in ["2min", "5min", "15min"]:
                monthly_tasks.extend(self.tasks[priority][time_category])

        monthly_tasks = [t for t in monthly_tasks if not self.was_task_done_recently(t, 20)]

        if not monthly_tasks:
            return ["🎉 No monthly tasks needed today!"]

        monthly_tasks.sort(key=self.get_days_since_task_completion, reverse=True)
        return monthly_tasks[:5]

    def get_quarterly_task(self) -> str:
        """Get today's quarterly focus task from the saved task assignments"""
        quarterly_task = self.quarterly_focus[self.current_quarter]

        if self.is_task_due(quarterly_task):
            return quarterly_task
        else:
            return "🎉 No quarterly focus needed today!"

    def get_personalized_recommendations(self, energy_level="yellow") -> Dict:
        """Get personalized cleaning recommendations based on energy level"""
        today_str = self.current_date.strftime("%Y-%m-%d")
        result = {
            "energy_level": energy_level,
            "day": self.day_of_week,
            "date": self.current_date.strftime("%B %d, %Y"),
            "week_focus": self.current_focus,
            "week_number": self.week_of_year,
            "daily_tasks": self.get_daily_tasks(energy_level),
            "weekly_tasks": self.get_weekly_focus_tasks(energy_level),
        }

        # Only include biweekly tasks for yellow/green days
        if energy_level != "red":
            result["biweekly_tasks"] = self.get_biweekly_tasks()

        # Only include monthly tasks for green days
        if energy_level == "green":
            # Monthly tasks now returns a list of tasks
            saved_monthlies = self.daily_task_assignments.get(today_str, {}).get("monthly_tasks", [])
            if not saved_monthlies:
                saved_monthlies = self.get_monthly_task()
            result["monthly_tasks"] = saved_monthlies

            if not result["monthly_tasks"]:
                result["monthly_tasks"] = self.get_monthly_task()

            result["variety_tasks"] = self.daily_task_assignments.get(today_str, {}).get("variety_tasks", [])
            result["quarterly_focus"] = self.get_quarterly_task()

        return result

    def display_recommendations(self, energy_level="yellow"):
        """Print nicely formatted recommendations"""
        recs = self.get_personalized_recommendations(energy_level)

        # Clear screen (works on Windows, Mac, and Linux)
        os.system('cls' if os.name == 'nt' else 'clear')

        # Energy level indicator
        energy_displays = {
            "red": "🔴 LOW ENERGY DAY",
            "yellow": "🟡 MODERATE ENERGY DAY",
            "green": "🟢 GOOD ENERGY DAY"
        }

        print("\n========================================")
        print(f"  ADAPTIVE CLEANING RECOMMENDATIONS")
        print("========================================")
        print(f"\n{energy_displays[energy_level]}")
        print(f"{recs['day']}, {recs['date']}")
        print(f"Week {recs['week_number']} Focus: {recs['week_focus']}")
        print("\n----------------------------------------")

        # Display daily tasks
        print("\n🔍 DAILY PRIORITY TASKS:")
        task_options = []
        for i, task in enumerate(recs['daily_tasks'], 1):
            days_since = self.get_days_since_task_completion(task)
            last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"

            # Add frequency and urgency info
            if task in self.task_metadata:
                frequency = self.task_metadata[task]["frequency"]
                time = self.task_metadata[task]["time"]
                urgency_score = self.get_task_urgency_score(task)

                # Create urgency indicator
                if urgency_score > 3:
                    urgency = "🔥 HIGH"
                elif urgency_score > 1.5:
                    urgency = "⚠️ MEDIUM"
                else:
                    urgency = "✓ LOW"

                print(f"  {i}. {task} ({time}, {frequency})")
                print(f"     Last done: {last_done} | Urgency: {urgency}")
            else:
                print(f"  {i}. {task}")
                print(f"     Last done: {last_done}")

            task_options.append(task)

        # Display weekly tasks
        if recs['weekly_tasks']:
            print("\n🔄 WEEKLY FOCUS TASKS:")
            print(f"  Focus: {recs['week_focus']}")
            for i, task in enumerate(recs['weekly_tasks'], 1):
                days_since = self.get_days_since_task_completion(task)
                last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"

                # Add frequency and urgency info
                if task in self.task_metadata:
                    frequency = self.task_metadata[task]["frequency"]
                    time = self.task_metadata[task]["time"]
                    urgency_score = self.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    print(f"  {len(recs['daily_tasks']) + i}. {task} ({time}, {frequency})")
                    print(f"     Last done: {last_done} | Urgency: {urgency}")
                else:
                    print(f"  {len(recs['daily_tasks']) + i}. {task}")
                    print(f"     Last done: {last_done}")

                task_options.append(task)

        # Display biweekly tasks if applicable
        if energy_level != "red" and "biweekly_tasks" in recs:
            print("\n📅 BIWEEKLY TASKS:")
            print("  Choose ONE if energy allows:")
            start_idx = len(recs['daily_tasks']) + len(recs['weekly_tasks']) + 1
            for i, task in enumerate(recs['biweekly_tasks'], 0):
                if task.startswith("🎉"):
                    print(f"  {task}")
                    continue

                days_since = self.get_days_since_task_completion(task)
                last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"

                # Add frequency and urgency info
                if task in self.task_metadata:
                    frequency = self.task_metadata[task]["frequency"]
                    time = self.task_metadata[task]["time"]
                    urgency_score = self.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    print(f"  {start_idx + i}. {task} ({time}, {frequency})")
                    print(f"     Last done: {last_done} | Urgency: {urgency}")
                else:
                    print(f"  {start_idx + i}. {task}")
                    print(f"     Last done: {last_done}")

                task_options.append(task)

        # Display monthly tasks if applicable
        if energy_level == "green" and "monthly_tasks" in recs:
            print("\n🌟 MONTHLY VISUAL IMPACT TASKS:")
            monthly_tasks = recs['monthly_tasks']

            # Handle if it's a string (backwards compatibility)
            if isinstance(monthly_tasks, str):
                monthly_tasks = [monthly_tasks]

            for i, task in enumerate(monthly_tasks):
                if task.startswith("🎉"):
                    print(f"  {task}")
                    continue

                days_since = self.get_days_since_task_completion(task)
                last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"
                idx = len(task_options) + 1

                # Add frequency and urgency info
                if task in self.task_metadata:
                    frequency = self.task_metadata[task]["frequency"]
                    time = self.task_metadata[task]["time"]
                    urgency_score = self.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    print(f"  {idx}. {task} ({time}, {frequency})")
                    print(f"     Last done: {last_done} | Urgency: {urgency}")
                else:
                    print(f"  {idx}. {task}")
                    print(f"     Last done: {last_done}")

                task_options.append(task)

        # Display quarterly focus if applicable
        if energy_level == "green" and "quarterly_focus" in recs:
            print("\n🗓️ QUARTERLY FOCUS:")
            quarterly_task = recs['quarterly_focus']

            if quarterly_task.startswith("🎉"):
                print(f"  {quarterly_task}")
            else:
                days_since = self.get_days_since_task_completion(quarterly_task)
                last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"
                idx = len(task_options) + 1

                # Add frequency and urgency info
                if quarterly_task in self.task_metadata:
                    frequency = self.task_metadata[quarterly_task]["frequency"]
                    time = self.task_metadata[quarterly_task]["time"]
                    urgency_score = self.get_task_urgency_score(quarterly_task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    print(f"  {idx}. {quarterly_task} ({time}, {frequency})")
                    print(f"     Last done: {last_done} | Urgency: {urgency}")
                else:
                    print(f"  {idx}. {quarterly_task}")
                    print(f"     Last done: {last_done}")

                task_options.append(quarterly_task)

        # Display variety tasks if applicable
        if energy_level == "green" and "variety_tasks" in recs and recs["variety_tasks"]:
            print("\n✨ VARIETY TASKS:")
            print("  For when you want something different:")
            variety_idx = len(task_options) + 1

            for i, task in enumerate(recs["variety_tasks"]):
                days_since = self.get_days_since_task_completion(task)
                last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"

                # Add frequency and urgency info
                if task in self.task_metadata:
                    frequency = self.task_metadata[task]["frequency"]
                    time = self.task_metadata[task]["time"]
                    urgency_score = self.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    print(f"  {variety_idx + i}. {task} ({time}, {frequency})")
                    print(f"     Last done: {last_done} | Urgency: {urgency}")
                else:
                    print(f"  {variety_idx + i}. {task}")
                    print(f"     Last done: {last_done}")

                task_options.append(task)

        print("\n----------------------------------------")
        print("💡 REMINDER: Your health comes first!")
        print("   It's okay to do less or nothing at all.")
        print("========================================\n")

        return task_options  # Return the list of displayed tasks

    def view_history(self):
        """Display task completion history"""
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\n========================================")
        print("       CLEANING TASK HISTORY")
        print("========================================\n")

        if not self.task_history:
            print("No task history found. Start completing tasks to build history!")
            return

        # Sort tasks by most recently completed
        completed_tasks = []
        for task_name, data in self.task_history.items():
            if "last_done" in data:
                last_done_date = datetime.datetime.strptime(data["last_done"], "%Y-%m-%d").date()
                days_since = (self.current_date - last_done_date).days

                # Add frequency if available
                if task_name in self.task_metadata:
                    frequency = self.task_metadata[task_name]["frequency"]
                    is_due = self.is_task_due(task_name)
                    due_status = "Due" if is_due else "Not Due"
                else:
                    frequency = "unknown"
                    due_status = "-"

                completed_tasks.append(
                    (task_name, last_done_date, days_since, data["completion_count"], frequency, due_status))

        # Sort by most recent first
        completed_tasks.sort(key=lambda x: x[1], reverse=True)

        print(f"{'Task':<40} | {'Last Done':<12} | {'Days':<5} | {'Count':<5} | {'Frequency':<10} | {'Status':<8}")
        print("-" * 90)

        for task, date, days, count, frequency, status in completed_tasks:
            print(
                f"{task[:38]:<40} | {date.strftime('%Y-%m-%d')} | {days:<5} | {count:<5} | {frequency:<10} | {status:<8}")

        print("\n========================================")
        input("\nPress Enter to continue...")

    def show_statistics(self):
        """Display cleaning statistics"""
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\n========================================")
        print("       CLEANING STATISTICS")
        print("========================================\n")

        if not self.task_history:
            print("No task history found. Start completing tasks to build statistics!")
            return

        # Calculate total completions
        total_completions = sum(data.get("completion_count", 0) for data in self.task_history.values())

        # Find most completed task
        most_completed = None
        most_completions = 0
        for task, data in self.task_history.items():
            count = data.get("completion_count", 0)
            if count > most_completions:
                most_completions = count
                most_completed = task

        # Calculate streak (consecutive days with at least one task completed)
        dates_with_completions = set()
        for task, data in self.task_history.items():
            for completion in data.get("completion_dates", []):
                dates_with_completions.add(completion["date"])

        # Convert to date objects and sort
        completion_dates = sorted([datetime.datetime.strptime(d, "%Y-%m-%d").date()
                                   for d in dates_with_completions], reverse=True)

        # Calculate current streak
        current_streak = 0
        if completion_dates and completion_dates[0] == self.current_date:
            current_streak = 1
            for i in range(1, len(completion_dates)):
                if (completion_dates[i - 1] - completion_dates[i]).days == 1:
                    current_streak += 1
                else:
                    break

        # Print statistics
        print(f"Total tasks completed: {total_completions}")
        print(f"Most completed task: {most_completed} ({most_completions} times)")
        print(f"Current streak: {current_streak} days")
        print(f"Total unique tasks completed: {len(self.task_history)}")

        # Calculate frequency statistics if we have task_metadata
        if hasattr(self, 'task_metadata'):
            print("\nCompletion by Frequency:")
            print("------------------------")

            # Initialize counters
            freq_stats = {
                "daily": {"total": 0, "completed": 0, "overdue": 0},
                "weekly": {"total": 0, "completed": 0, "overdue": 0},
                "biweekly": {"total": 0, "completed": 0, "overdue": 0},
                "monthly": {"total": 0, "completed": 0, "overdue": 0},
                "quarterly": {"total": 0, "completed": 0, "overdue": 0}
            }

            # Count tasks by frequency
            for task, metadata in self.task_metadata.items():
                frequency = metadata["frequency"]
                if frequency in freq_stats:
                    freq_stats[frequency]["total"] += 1

                    if task in self.task_history:
                        freq_stats[frequency]["completed"] += 1

                    if self.is_task_due(task):
                        freq_stats[frequency]["overdue"] += 1

            # Display frequency stats
            print(f"{'Frequency':<10} | {'Total':<5} | {'Completed':<9} | {'Overdue':<7} | {'Completion %':<12}")
            print("-" * 55)

            for freq, stats in freq_stats.items():
                if stats["total"] > 0:  # Only include frequencies with tasks
                    completion_pct = (stats["completed"] / stats["total"]) * 100
                    print(
                        f"{freq.capitalize():<10} | {stats['total']:<5} | {stats['completed']:<9} | {stats['overdue']:<7} | {completion_pct:.1f}%")

        print("\n========================================")
        input("\nPress Enter to continue...")

    def reset_todays_tasks(self):
        """Reset today's task assignments (useful if you want different tasks)"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        try:
            with open(self.daily_tasks_file, 'r') as f:
                daily_tasks = json.load(f)

            # Delete today's tasks if they exist
            if today_str in daily_tasks:
                del daily_tasks[today_str]

            # Save the updated file
            with open(self.daily_tasks_file, 'w') as f:
                json.dump(daily_tasks, f, indent=2)

            # Regenerate today's tasks
            self.daily_task_assignments = self._load_or_generate_daily_tasks()

            print("\n✅ Today's task assignments have been reset!")

        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is invalid, just generate new tasks
            self.daily_task_assignments = self._load_or_generate_daily_tasks()
            print("\n✅ Today's task assignments have been generated!")


# Streamlit web application
def run_streamlit_app():
    st.set_page_config(page_title="Adaptive Cleaning Scheduler", layout="wide")

    st.title("🧹 Adaptive Cleaning Scheduler")

    # Initialize the scheduler
    scheduler = AdaptiveCleaningScheduler()

    # Sidebar Menu
    menu = st.sidebar.selectbox(
        "Menu",
        ["Today's Recommendations", "Mark Tasks Completed", "View Task History", "View Statistics", "Task Dashboard",
         "Reset Today's Tasks"]
    )

    if menu == "Today's Recommendations":
        st.subheader("How's your energy today?")
        energy_level = st.radio(
            "Select your current energy level:",
            ("red", "yellow", "green"),
            index=2,
            format_func=lambda x: {"red": "🔴 Red (low energy)", "yellow": "🟡 Moderate", "green": "🟢 Good"}[x]
        )

        recs = scheduler.get_personalized_recommendations(energy_level)

        st.write(f"### {recs['day']}, {recs['date']}")
        st.write(f"**Week {recs['week_number']} Focus:** {recs['week_focus']}")

        today_str = scheduler.current_date.strftime("%Y-%m-%d")

        # ✅ DAILY TASKS
        st.write("#### 🧹 Daily Tasks")
        # Add urgency indicators
        for task in recs['daily_tasks']:
            history = scheduler.task_history.get(task, {})
            last_done = history.get("last_done", "")
            done_today = last_done == today_str

            # Get urgency info
            if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                metadata = scheduler.task_metadata[task]
                frequency = metadata.get("frequency", "unknown")
                urgency_score = scheduler.get_task_urgency_score(task)

                # Create urgency indicator
                if urgency_score > 3:
                    urgency = "🔥 HIGH"
                elif urgency_score > 1.5:
                    urgency = "⚠️ MEDIUM"
                else:
                    urgency = "✓ LOW"

                label = f"{task} ({frequency} task, urgency: {urgency})"
            else:
                label = task

            checked = st.checkbox(label, value=done_today, key=f"daily_{task}")
            if checked and not done_today:
                scheduler.mark_task_completed(task)
                st.success(f"✅ Marked as completed: {task}")
                st.rerun()

        # VARIETY TASKS
        if energy_level == "green" and recs.get("variety_tasks"):
            st.markdown('<div style="padding-left: 1.5em;">', unsafe_allow_html=True)
            st.markdown("###### ✨ Bonus Variety Tasks")
            st.caption("Tasks not done recently, sorted by urgency!")

            for task in recs["variety_tasks"]:
                history = scheduler.task_history.get(task, {})
                last_done = history.get("last_done", "")
                done_today = last_done == today_str

                # Get urgency info
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    label = f"{task} ({frequency} task, urgency: {urgency})"
                else:
                    label = task

                col1, col2 = st.columns([1, 20])  # Adjust the ratio for more/less indent

                with col2:
                    checked = st.checkbox(label, value=done_today, key=f"variety_{task}")
                    if checked and not done_today:
                        scheduler.mark_task_completed(task)
                        st.success(f"✅ Marked as completed: {task}")
                        st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        # 🔄 WEEKLY TASKS
        st.write(f"#### 🔄 Weekly Focus Tasks – {recs['week_focus']}")
        for task in recs['weekly_tasks']:
            history = scheduler.task_history.get(task, {})
            last_done = history.get("last_done", "")
            done_today = last_done == today_str

            # Get urgency info
            if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                metadata = scheduler.task_metadata[task]
                frequency = metadata.get("frequency", "unknown")
                urgency_score = scheduler.get_task_urgency_score(task)

                # Create urgency indicator
                if urgency_score > 3:
                    urgency = "🔥 HIGH"
                elif urgency_score > 1.5:
                    urgency = "⚠️ MEDIUM"
                else:
                    urgency = "✓ LOW"

                label = f"{task} ({frequency} task, urgency: {urgency})"
            else:
                label = task

            checked = st.checkbox(label, value=done_today, key=f"weekly_{task}")
            if checked and not done_today:
                scheduler.mark_task_completed(task)
                st.success(f"✅ Marked as completed: {task}")
                st.rerun()

        # 📅 BIWEEKLY TASKS
        if energy_level != "red" and "biweekly_tasks" in recs:
            st.write("#### 📅 Biweekly Tasks")
            for task in recs['biweekly_tasks']:
                if task.startswith("🎉"):
                    st.info(task)
                    continue

                history = scheduler.task_history.get(task, {})
                last_done = history.get("last_done", "")
                done_today = last_done == today_str

                # Get urgency info
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    label = f"{task} ({frequency} task, urgency: {urgency})"
                else:
                    label = task

                checked = st.checkbox(label, value=done_today, key=f"biweekly_{task}")
                if checked and not done_today:
                    scheduler.mark_task_completed(task)
                    st.success(f"✅ Marked as completed: {task}")
                    st.rerun()

        # 🌟 MONTHLY TASKS
        if energy_level == "green" and "monthly_tasks" in recs:
            st.write("#### 🌟 Monthly Tasks")
            for task in recs["monthly_tasks"]:
                if task.startswith("🎉"):
                    st.info(task)
                    continue

                history = scheduler.task_history.get(task, {})
                last_done = history.get("last_done", "")
                done_today = last_done == today_str

                # Get urgency info
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    label = f"{task} ({frequency} task, urgency: {urgency})"
                else:
                    label = task

                checked = st.checkbox(label, value=done_today, key=f"monthly_{task}")
                if checked and not done_today:
                    scheduler.mark_task_completed(task)
                    st.success(f"✅ Marked as completed: {task}")
                    st.rerun()

        # 🗓️ QUARTERLY TASK
        if energy_level == "green" and "quarterly_focus" in recs:
            st.write("#### 🗓️ Quarterly Focus")
            task = recs["quarterly_focus"]
            if task.startswith("🎉"):
                st.info(task)
            else:
                history = scheduler.task_history.get(task, {})
                last_done = history.get("last_done", "")
                done_today = last_done == today_str

                # Get urgency info
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    label = f"{task} ({frequency} task, urgency: {urgency})"
                else:
                    label = task

                checked = st.checkbox(label, value=done_today, key=f"quarterly_{task}")
                if checked and not done_today:
                    scheduler.mark_task_completed(task)
                    st.success(f"✅ Marked as completed: {task}")
                    st.rerun()

    elif menu == "Mark Tasks Completed":
        st.subheader("✅ Mark a Task Completed")

        today_str = scheduler.current_date.strftime("%Y-%m-%d")
        assignments = scheduler.daily_task_assignments.get(today_str, {})

        task_options = []
        for level in ["red", "yellow", "green"]:
            task_options.extend(assignments.get("daily_tasks", {}).get(level, []))
            task_options.extend(assignments.get("weekly_tasks", {}).get(level, []))
        task_options.extend(assignments.get("biweekly_tasks", []))

        # Handle monthly_tasks as a list
        monthly_tasks = assignments.get("monthly_tasks", [])
        if isinstance(monthly_tasks, str):
            # Handle backwards compatibility
            task_options.append(monthly_tasks)
        else:
            task_options.extend(monthly_tasks)

        task_options.append(assignments.get("quarterly_task", ""))

        # Remove empty and duplicates and celebration messages
        task_options = list({task for task in task_options if task and not task.startswith("🎉")})

        if task_options:
            # Sort tasks by urgency if we have task_metadata
            if hasattr(scheduler, 'task_metadata'):
                task_options.sort(key=scheduler.get_task_urgency_score, reverse=True)

            task_display = []
            for task in task_options:
                # Get urgency info
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)

                    # Create urgency indicator
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    task_display.append(f"{task} ({frequency} task, urgency: {urgency})")
                else:
                    task_display.append(task)

            selected_idx = st.selectbox("Select a task to mark as completed:",
                                        range(len(task_display)),
                                        format_func=lambda i: task_display[i])
            selected_task = task_options[selected_idx]

            notes = st.text_input("Optional notes about this task:")

            if st.button("Mark Completed"):
                scheduler.mark_task_completed(selected_task, notes)
                st.success(f"Marked as completed: {selected_task}")
        else:
            st.info("No tasks available to mark yet. Please generate recommendations first.")

    elif menu == "View Task History":
        st.subheader("📜 Cleaning Task History")

        if scheduler.task_history:
            task_data = []
            for task, data in scheduler.task_history.items():
                last_done = data.get("last_done", "Never")
                count = data.get("completion_count", 0)

                # Add frequency and due status if available
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    frequency = scheduler.task_metadata[task].get("frequency", "unknown")
                    is_due = scheduler.is_task_due(task)
                    due_status = "Due" if is_due else "Not Due"
                else:
                    frequency = "unknown"
                    due_status = "Unknown"

                days_since = scheduler.get_days_since_task_completion(task)
                if days_since == float('inf'):
                    days_ago = "Never done"
                else:
                    days_ago = f"{days_since} days ago"

                task_data.append((task, last_done, days_ago, count, frequency, due_status))

            # Create dataframe
            df = pd.DataFrame({
                "Task": [t[0] for t in task_data],
                "Last Done": [t[1] for t in task_data],
                "Days Ago": [t[2] for t in task_data],
                "Times Completed": [t[3] for t in task_data],
                "Frequency": [t[4] for t in task_data],
                "Status": [t[5] for t in task_data]
            })

            # Add sorting and filtering
            st.write("Filter and sort the history:")
            col1, col2 = st.columns(2)
            with col1:
                freq_filter = st.multiselect("Filter by frequency:",
                                             options=["daily", "weekly", "biweekly", "monthly", "quarterly", "unknown"],
                                             default=[])
            with col2:
                status_filter = st.multiselect("Filter by status:",
                                               options=["Due", "Not Due", "Unknown"],
                                               default=[])

            # Apply filters
            filtered_df = df
            if freq_filter:
                filtered_df = filtered_df[filtered_df["Frequency"].isin(freq_filter)]
            if status_filter:
                filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]

            # Sort options
            sort_by = st.selectbox("Sort by:",
                                   ["Last Done", "Days Ago", "Times Completed", "Task"])
            sort_ascending = st.checkbox("Sort ascending", value=False)

            # Apply sorting
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=sort_ascending)

            st.dataframe(filtered_df)
        else:
            st.info("No task history found.")

    elif menu == "View Statistics":
        st.subheader("📈 Cleaning Statistics")

        if scheduler.task_history:
            total_completions = sum(d.get("completion_count", 0) for d in scheduler.task_history.values())
            most_completed = max(scheduler.task_history.items(), key=lambda x: x[1].get("completion_count", 0),
                                 default=(None, None))
            most_task = most_completed[0]
            most_count = most_completed[1]['completion_count'] if most_completed[1] else 0

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tasks Completed", total_completions)
            with col2:
                st.metric("Most Completed Task", most_task if most_task else "None")
            with col3:
                st.metric("Times Completed", most_count)

            # Calculate frequency statistics if we have task_metadata
            if hasattr(scheduler, 'task_metadata'):
                st.subheader("Completion by Frequency")

                # Initialize counters
                freq_stats = {
                    "daily": {"total": 0, "completed": 0, "overdue": 0},
                    "weekly": {"total": 0, "completed": 0, "overdue": 0},
                    "biweekly": {"total": 0, "completed": 0, "overdue": 0},
                    "monthly": {"total": 0, "completed": 0, "overdue": 0},
                    "quarterly": {"total": 0, "completed": 0, "overdue": 0},
                    "unknown": {"total": 0, "completed": 0, "overdue": 0}
                }

                # Count tasks by frequency
                for task in scheduler.task_metadata:
                    frequency = scheduler.task_metadata[task].get("frequency", "unknown")
                    freq_stats[frequency]["total"] += 1

                    if task in scheduler.task_history:
                        freq_stats[frequency]["completed"] += 1

                    if scheduler.is_task_due(task):
                        freq_stats[frequency]["overdue"] += 1

                # Convert to dataframe
                freq_data = []
                for freq, stats in freq_stats.items():
                    if stats["total"] > 0:  # Only include frequencies with tasks
                        completion_pct = (stats["completed"] / stats["total"]) * 100
                        overdue_pct = (stats["overdue"] / stats["total"]) * 100 if stats["total"] > 0 else 0

                        freq_data.append({
                            "Frequency": freq.capitalize(),
                            "Total Tasks": stats["total"],
                            "Completed At Least Once": stats["completed"],
                            "Completion %": f"{completion_pct:.1f}%",
                            "Currently Overdue": stats["overdue"],
                            "Overdue %": f"{overdue_pct:.1f}%"
                        })

                freq_df = pd.DataFrame(freq_data)
                st.dataframe(freq_df)

        else:
            st.info("No statistics available yet.")

    elif menu == "Task Dashboard":
        st.subheader("📊 Task Dashboard")

        if not hasattr(scheduler, 'task_metadata'):
            st.warning(
                "Task dashboard requires the enhanced scheduler with frequency metadata. Please update your code to the latest version.")
        elif scheduler.task_history:
            # Calculate task completion statistics
            frequency_stats = {}
            priority_stats = {}
            overdue_tasks = []

            for task in scheduler.task_metadata:
                metadata = scheduler.task_metadata[task]
                frequency = metadata.get("frequency", "unknown")
                priority = metadata.get("priority", "unknown")

                # Update frequency stats
                if frequency not in frequency_stats:
                    frequency_stats[frequency] = {"total": 0, "completed": 0, "overdue": 0}
                frequency_stats[frequency]["total"] += 1

                # Update priority stats
                if priority not in priority_stats:
                    priority_stats[priority] = {"total": 0, "completed": 0, "overdue": 0}
                priority_stats[priority]["total"] += 1

                # Check if task has been completed
                if task in scheduler.task_history:
                    frequency_stats[frequency]["completed"] += 1
                    priority_stats[priority]["completed"] += 1

                # Check if task is overdue
                if scheduler.is_task_due(task):
                    frequency_stats[frequency]["overdue"] += 1
                    priority_stats[priority]["overdue"] += 1

                    days_since = scheduler.get_days_since_task_completion(task)
                    if days_since == float('inf'):
                        days_ago = "Never done"
                    else:
                        days_ago = f"{days_since} days ago"

                    overdue_tasks.append({
                        "name": task,
                        "frequency": frequency,
                        "priority": priority,
                        "days_since": days_since,
                        "days_ago": days_ago,
                        "urgency_score": scheduler.get_task_urgency_score(task)
                    })

            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_tasks = sum(stats["total"] for stats in frequency_stats.values())
                completed_tasks = sum(stats["completed"] for stats in frequency_stats.values())
                completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
                st.metric("Overall Completion Rate", f"{completion_rate:.1f}%")

            with col2:
                total_overdue = sum(stats["overdue"] for stats in frequency_stats.values())
                st.metric("Overdue Tasks", f"{total_overdue}")

            with col3:
                # Calculate current streak
                dates_with_completions = set()
                for task, data in scheduler.task_history.items():
                    for completion in data.get("completion_dates", []):
                        dates_with_completions.add(completion["date"])

                # Convert to date objects and sort
                completion_dates = sorted([datetime.datetime.strptime(d, "%Y-%m-%d").date()
                                           for d in dates_with_completions], reverse=True)

                # Calculate current streak
                streak = 0
                if completion_dates and completion_dates[0] == scheduler.current_date:
                    streak = 1
                    for i in range(1, len(completion_dates)):
                        if (completion_dates[i - 1] - completion_dates[i]).days == 1:
                            streak += 1
                        else:
                            break

                st.metric("Current Streak", f"{streak} days")

            # Display frequency breakdown
            st.subheader("Completion by Frequency")

            # Convert to dataframe for easier display
            frequency_data = []
            for freq, stats in frequency_stats.items():
                completion_pct = (stats["completed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                overdue_pct = (stats["overdue"] / stats["total"]) * 100 if stats["total"] > 0 else 0

                frequency_data.append({
                    "Frequency": freq.capitalize(),
                    "Total Tasks": stats["total"],
                    "Completed At Least Once": stats["completed"],
                    "Completion %": f"{completion_pct:.1f}%",
                    "Currently Overdue": stats["overdue"],
                    "Overdue %": f"{overdue_pct:.1f}%"
                })

            freq_df = pd.DataFrame(frequency_data)
            st.dataframe(freq_df)

            # Display overdue tasks
            st.subheader("Overdue Tasks")
            if overdue_tasks:
                # Sort by urgency score (highest first)
                overdue_tasks.sort(key=lambda x: x["urgency_score"], reverse=True)

                overdue_data = []
                for task in overdue_tasks[:15]:  # Show top 15 most urgent
                    # Create urgency indicator
                    if task["urgency_score"] > 3:
                        urgency = "🔥 HIGH"
                    elif task["urgency_score"] > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"

                    overdue_data.append({
                        "Task": task["name"],
                        "Priority": task["priority"].replace("priority", "P"),
                        "Frequency": task["frequency"].capitalize(),
                        "Last Done": task["days_ago"],
                        "Urgency": urgency,
                        "Score": f"{task['urgency_score']:.1f}"
                    })

                overdue_df = pd.DataFrame(overdue_data)
                st.dataframe(overdue_df)

                # Add a button to quickly mark overdue tasks
                st.subheader("Quick Complete")
                task_options = [task["name"] for task in overdue_tasks]

                selected_task = st.selectbox("Select an overdue task to mark as complete:",
                                             task_options)

                notes = st.text_input("Optional notes:")

                if st.button("Mark Complete"):
                    scheduler.mark_task_completed(selected_task, notes)
                    st.success(f"Marked as completed: {selected_task}")
                    st.rerun()
            else:
                st.success("No overdue tasks! Great job staying on top of your cleaning.")
        else:
            st.info("No task history found. Start completing tasks to see statistics here.")

    elif menu == "Reset Today's Tasks":
        st.subheader("♻️ Reset Today's Tasks")
        st.write("This will regenerate all task recommendations for today using the new frequency-based system.")

        if st.button("Reset Tasks"):
            scheduler.reset_todays_tasks()
            st.success("Today's tasks have been reset!")
            st.write("Return to 'Today's Recommendations' to see your new personalized tasks.")


# Main program
# if __name__ == "__main__":
#     # If running as a stand-alone script
#     if 'streamlit' in sys.modules:
#         # Run the Streamlit app if streamlit is imported
#         run_streamlit_app()
#     else:
#         # Otherwise run the command-line version
#         scheduler = AdaptiveCleaningScheduler()
#
#         print("\nWelcome to your Adaptive Cleaning Scheduler!")
#         print("This program helps manage cleaning tasks based on your energy levels.")
#         print("Your tasks for today are consistent and won't change when you restart the app.")
#
#         while True:
#             print("\nWhat would you like to do?")
#             print("1. Get cleaning recommendations (based on energy)")
#             print("2. Mark tasks as completed")
#             print("3. View task history")
#             print("4. View cleaning statistics")
#             print("5. Reset today's task assignments")
#             print("6. Exit program")
#
#             choice = input("\nEnter your choice (1-6): ")
#
#             if choice == "1":
#                 print("\nWhat is your energy level today?")
#                 print("1. Red (Very limited energy)")
#                 print("2. Yellow (Moderate energy)")
#                 print("3. Green (Good energy)")
#
#                 energy_choice = input("\nEnter your energy level (1-3): ")
#
#                 if energy_choice == "1":
#                     displayed_tasks = scheduler.display_recommendations("red")
#                 elif energy_choice == "2":
#                     displayed_tasks = scheduler.display_recommendations("yellow")
#                 elif energy_choice == "3":
#                     displayed_tasks = scheduler.display_recommendations("green")
#                 else:
#                     print("\nInvalid choice. Defaulting to yellow energy level.")
#                     displayed_tasks = scheduler.display_recommendations("yellow")
#
#                 # Option to mark tasks completed directly
#                 print("\nWould you like to mark any tasks as completed?")
#                 print("Enter task number or 0 to return to main menu.")
#
#                 while True:
#                     task_choice = input("\nTask number to mark completed (0 to finish): ")
#
#                     if task_choice == "0":
#                         break
#
#                     try:
#                         task_idx = int(task_choice) - 1
#                         if 0 <= task_idx < len(displayed_tasks):
#                             notes = input("Optional notes about this task: ")
#                             scheduler.mark_task_completed(displayed_tasks[task_idx], notes)
#                         else:
#                             print("Invalid task number.")
#                     except ValueError:
#                         print("Please enter a valid number.")
#
#             elif choice == "2":
#                 # Get a list of all tasks from all energy levels for today
#                 today_str = scheduler.current_date.strftime("%Y-%m-%d")
#                 if today_str in scheduler.daily_task_assignments:
#                     assignments = scheduler.daily_task_assignments[today_str]
#
#                     all_tasks = []
#                     # Add daily tasks for all energy levels
#                     for energy in ["red", "yellow", "green"]:
#                         all_tasks.extend(assignments["daily_tasks"][energy])
#
#                     # Add weekly tasks for all energy levels
#                     for energy in ["red", "yellow", "green"]:
#                         all_tasks.extend(assignments["weekly_tasks"][energy])
#
#                     # Add biweekly tasks
#                     all_tasks.extend(assignments["biweekly_tasks"])
#
#                     # Add monthly tasks and quarterly task
#                     if "monthly_tasks" in assignments:
#                         if isinstance(assignments["monthly_tasks"], list):
#                             all_tasks.extend(assignments["monthly_tasks"])
#                         else:
#                             all_tasks.append(assignments["monthly_tasks"])
#
#                     all_tasks.append(assignments.get("quarterly_task", ""))
#
#                     # Remove duplicates, empty strings, and celebration messages
#                     seen = set()
#                     today_tasks = [x for x in all_tasks if
#                                    x and not x.startswith("🎉") and not (x in seen or seen.add(x))]
#
#                     # Sort by urgency score if we have task_metadata
#                     if hasattr(scheduler, 'task_metadata'):
#                         today_tasks.sort(key=scheduler.get_task_urgency_score, reverse=True)
#
#                     # Display tasks for selection
#                     os.system('cls' if os.name == 'nt' else 'clear')
#                     print("\n========================================")
#                     print("       MARK TODAY'S TASKS AS COMPLETED")
#                     print("========================================\n")
#
#                     for i, task in enumerate(today_tasks, 1):
#                         days_since = scheduler.get_days_since_task_completion(task)
#                         last_done = "Never" if days_since == float('inf') else f"{days_since} days ago"
#
#                         # Add urgency info if available
#                         if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
#                             frequency = scheduler.task_metadata[task]["frequency"]
#                             urgency_score = scheduler.get_task_urgency_score(task)
#
#                             # Create urgency indicator
#                             if urgency_score > 3:
#                                 urgency = "🔥 HIGH"
#                             elif urgency_score > 1.5:
#                                 urgency = "⚠️ MEDIUM"
#                             else:
#                                 urgency = "✓ LOW"
#
#                             print(f"{i}. {task}")
#                             print(f"   Last done: {last_done} | Frequency: {frequency} | Urgency: {urgency}")
#                         else:
#                             print(f"{i}. {task}")
#                             print(f"   Last done: {last_done}")
#
#                     print("\nEnter task number to mark as completed (0 to return):")
#                     while True:
#                         task_choice = input("\nTask number to mark completed (0 to finish): ")
#
#                         if task_choice == "0":
#                             break
#
#                         try:
#                             task_idx = int(task_choice) - 1
#                             if 0 <= task_idx < len(today_tasks):
#                                 notes = input("Optional notes about this task: ")
#                                 scheduler.mark_task_completed(today_tasks[task_idx], notes)
#                             else:
#                                 print("Invalid task number.")
#                         except ValueError:
#                             print("Please enter a valid number.")
#                 else:
#                     print("\nNo tasks assigned for today. Please generate recommendations first.")
#
#             elif choice == "3":
#                 scheduler.view_history()
#
#             elif choice == "4":
#                 scheduler.show_statistics()
#
#             elif choice == "5":
#                 confirm = input("\nAre you sure you want to reset today's task assignments? (y/n): ")
#                 if confirm.lower() == 'y':
#                     scheduler.reset_todays_tasks()
#                     print("Tasks have been reset. Go to option 1 to see your new tasks.")
#
#             elif choice == "6":
#                 print("\nThank you for using the Adaptive Cleaning Scheduler!")
#                 print("Remember: Your health comes first. Rest well!")
#                 break
#             else:
#                 print("\nInvalid choice. Please select 1-6.")
