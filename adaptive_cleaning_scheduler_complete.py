from airtable_backend import AirtableBackend
import random
import datetime
from typing import List, Dict, Tuple, Union, Any
import streamlit as st
import pandas as pd
import os

class AdaptiveCleaningScheduler:
    def __init__(self, username="default"):
        self.username = username
        self.backend = AirtableBackend()

        today = datetime.date.today()
        self.current_date = today
        self.day_of_week = today.strftime("%A")
        self.week_of_year = today.isocalendar()[1]
        self.current_focus = ["Kitchen", "Bathroom", "Living Area", "Bedroom/Pet"][(self.week_of_year - 1) % 4]
        self.current_quarter = (today.month - 1) // 3 + 1

        self.tasks, self.task_metadata = self._initialize_tasks()
        self.task_history = self.backend.get_task_history(self.username)
        self.daily_task_assignments = self._load_or_generate_daily_tasks()
        self._ensure_today_generated()  # Ensure today's tasks are generated

    def _ensure_today_generated(self):
        today_str = self.current_date.strftime("%Y-%m-%d")
        if today_str not in self.daily_task_assignments:
            self.daily_task_assignments[today_str] = self._generate_todays_tasks()
            # Save to Airtable
            self.backend.save_daily_tasks(self.username, today_str, self.daily_task_assignments[today_str])

    def mark_task_completed(self, task_name, notes=""):
        self.backend.update_task_history(self.username, task_name, notes)
        self.task_history = self.backend.get_task_history(self.username)
        print(f"✅ Task marked as completed: {task_name}")
    
    def reset_todays_tasks(self):
        """Reset today's task assignments (useful if you want different tasks)"""
        today_str = self.current_date.strftime("%Y-%m-%d")

        # Generate new tasks for today
        new_tasks = self._generate_todays_tasks()
        
        # Update local cache
        self.daily_task_assignments[today_str] = new_tasks
        
        # Save to Airtable
        self.backend.save_daily_tasks(self.username, today_str, new_tasks)
        
        print("\n✅ Today's task assignments have been reset!")

    def get_daily_tasks(self, energy_level="red") -> List[str]:
        today_str = self.current_date.strftime("%Y-%m-%d")
        return self.daily_task_assignments[today_str].get("daily_tasks", {}).get(energy_level, [])

    def get_weekly_focus_tasks(self, energy_level="yellow") -> List[str]:
        today_str = self.current_date.strftime("%Y-%m-%d")
        return self.daily_task_assignments[today_str].get("weekly_tasks", {}).get(energy_level, [])

    def get_biweekly_tasks(self) -> List[str]:
        today_str = self.current_date.strftime("%Y-%m-%d")
        return self.daily_task_assignments[today_str].get("biweekly_tasks", [])

    def get_monthly_task(self) -> List[str]:
        """Get today's monthly visual impact tasks"""
        today_str = self.current_date.strftime("%Y-%m-%d")
        
        # Prevent circular reference during initialization
        if hasattr(self, 'daily_task_assignments') and today_str in self.daily_task_assignments:
            monthly_tasks = self.daily_task_assignments[today_str].get("monthly_tasks", [])
            if isinstance(monthly_tasks, str):
                return [monthly_tasks] if monthly_tasks else []
            return monthly_tasks
        
        # If not available, generate fresh list of monthly candidates
        monthly_candidates = []
        
        # Get all tasks with frequency "monthly"
        for task_name, metadata in self.task_metadata.items():
            if metadata.get("frequency") == "monthly":
                monthly_candidates.append(task_name)
        
        # Filter for tasks that are due
        monthly_tasks = [t for t in monthly_candidates if self.is_task_due(t)]
        
        if not monthly_tasks:
            return ["🎉 No monthly tasks needed today!"]
        
        # Sort by urgency score (most urgent first)
        monthly_tasks.sort(key=self.get_task_urgency_score, reverse=True)
        return monthly_tasks[:5]

    def get_quarterly_task(self) -> str:
        quarterly_task = self.quarterly_focus[self.current_quarter]
        if self.is_task_due(quarterly_task):
            return quarterly_task
        return "🎉 No quarterly focus needed today!"      
    
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
        
        # Look for additional biweekly tasks from all priorities
        additional_biweekly_tasks = []
        for task_name, metadata in self.task_metadata.items():
            # Skip tasks already in biweekly_tasks
            if task_name in biweekly_tasks:
                continue
                
            # If task has biweekly frequency and is due
            if metadata.get("frequency") == "biweekly" and self.is_task_due(task_name):
                additional_biweekly_tasks.append(task_name)
        
        # Add additional biweekly tasks to the main list
        biweekly_tasks.extend(additional_biweekly_tasks)
    
        if not biweekly_tasks:
            biweekly_tasks = ["🎉 No biweekly tasks needed today!"]
    
        # Sort remaining by urgency score
        biweekly_tasks.sort(key=lambda t: self.get_task_urgency_score(t), reverse=True)
    
        # Generate monthly tasks
        monthly_tasks = self.get_monthly_task()
    
        # Get quarterly focus
        quarterly_task = self.get_quarterly_task()
    
        variety_tasks = []
        all_variety_sources = []
        for priority in ["priority2", "priority3"]:
            for time_category in ["2min", "5min", "15min"]:
                all_variety_sources.extend(self.tasks[priority][time_category])
        
        # Filter variety tasks based on frequency and urgency
        # Also exclude tasks that are already in biweekly_tasks
        variety_tasks = [t for t in all_variety_sources 
                         if self.is_task_due(t) and t not in biweekly_tasks]
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
        """Generate daily tasks based on energy level and task urgency"""
        day_assignment = {
            "Monday": "Clear and wipe kitchen counters",
            "Tuesday": "Pick up floor clutter in all rooms",
            "Wednesday": "Take out trash and recycling",
            "Thursday": "Clean coffee table",
            "Friday": "Wipe bathroom sink and toilet quick-clean",
            "Saturday": "Vacuum main living space",
            "Sunday": "REST DAY - No cleaning required"
        }

        tasks = []

        # Always recommend the assigned daily task first if it's not Sunday
        if self.day_of_week != "Sunday":
            daily_task = day_assignment.get(self.day_of_week, random.choice(self.tasks["priority1"]["2min"]))
            tasks.append(daily_task)

            # Build a list of potential tasks sorted by urgency
            potential_tasks = []

            # Gather tasks from all priority1 time categories
            for time_category in ["2min", "5min", "15min"]:
                for task in self.tasks["priority1"][time_category]:
                    # Skip the day's assigned task if it's in the list
                    if task == daily_task:
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

        
        # Regular tasks organized by priority and time
        ## Regular tasks organized by priority and time
        tasks = {
            "priority1": {
                "2min": [
                    "Wipe bathroom sink",  # daily
                    "Check and clear clutter from hallway or entryway",  # daily
                    "Quick-sort mail",  # daily
                    "Wipe down bathroom faucet",  # daily
                    "Put shoes in closet or bin"  # daily
                ],
                "5min": [
                    "Unload dishwasher",  # daily
                    "Scoop cat litter",  # daily
                    "Clear and wipe kitchen counters",  # daily
                    "Pick up floor clutter in main room",  # daily
                    "Take out trash if full"  # daily
                ],
                "15min": [
                    "Vacuum main living space",  # daily if possible
                    "Load dishwasher and run if full",  # daily
                    "Wipe down stovetop",  # daily
                    "Empty and wipe bathroom trash",  # daily
                    "Clean coffee table" # daily
                ]
            },
            "priority2": {
                "2min": [
                    "Replace kitchen towel",  # weekly
                    "Tidy couch cushions and blankets",  # weekly
                    "Water houseplants",  # weekly
                    "Wipe down door handles",  # weekly
                    "Refill toilet paper or soap"  # weekly
                ],
                "5min": [
                    "Wipe down appliances",  # weekly
                    "Quick clean one mirror",  # weekly
                    "Tidy one shelf or counter",  # weekly
                    "Clean out one fridge shelf"  # weekly
                ],
                "15min": [
                    "Mop kitchen and bathroom floors",  # weekly
                    "Wipe switches and doorknobs",  # weekly
                    "Clean bathroom toilet and sink thoroughly",  # weekly
                    "Replace bath towels" # weekly
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
                    "Deep clean one appliance",  # monthly
                    "Clean cycle on coffee maker", # monthly
                    "Clean cycle on dishwasher", # monthly
                    "Dust ceiling fans and light fixtures", # monthly
                    "Clean baseboards and molding", # monthly
                    "Vacuum upholstered furniture", # monthly
                    "Clean kitchen sink drain with baking soda and vinegar", # monthly
                    "Launder shower curtain and liner (don't use dryer!)" # monthly
                ]
            },
            "priority4": {
                "15min": [
                    "Vacuum under couch",  # quarterly
                    "Dust and rotate books",  # quarterly
                    "Wipe window tracks",  # quarterly
                    "Clean washing machine filter",  # quarterly
                    "Check fire alarm batteries",  # quarterly
                    "Rotate mattress", # quarterly
                    "Wash trashcans and recycling bins", # quarterly
                    "Declutter storage spaces", # quarterly
                    "Check water filter and water softner", # quarterly
                    "Wash curtains or blinds"  # quarterly
                ],
                "delegate": [
                    "Clean behind large appliances",  # quarterly
                    "Organize storage closet",  # quarterly
                    "Sort donation bin"  # quarterly
                ]
            }
        }
        
        task_metadata = {}
        for priority, durations in tasks.items():
            for duration, task_list in durations.items():
                for task in task_list:
                    task_metadata[task] = {
                        "priority": priority,
                        "duration": duration,
                        "frequency": (
                            "daily" if priority == "priority1" else
                            "weekly" if priority == "priority2" else
                            "biweekly" if priority == "priority3" and duration != "15min" else
                            "monthly" if priority == "priority3" and duration == "15min" else
                            "quarterly"
                        )
                    }


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
        """Calculate days since task was last completed"""
        if task_name not in self.task_history:
            return float('inf')  # Task never done

        last_done_str = self.task_history[task_name]["last_done"]
        if not last_done_str:
            return float('inf')  # Task never done
            
        try:
            last_done = datetime.datetime.strptime(last_done_str, "%Y-%m-%d").date()
            days_since = (self.current_date - last_done).days
            return days_since
        except ValueError:
            return float('inf')  # Invalid date format

    def is_task_due(self, task_name):
        meta = self.task_metadata.get(task_name)
        if not meta:
            return False  # or True, depending on what you prefer
        
        frequency = meta.get("frequency", "unknown")
        threshold = {
            "daily": 3,
            "weekly": 10,
            "biweekly": 18,
            "monthly": 35,
            "quarterly": 100
        }.get(frequency, 7)
    
        last_done_data = self.task_history.get(task_name)
        if not last_done_data:
            return True
    
        last_done_str = last_done_data.get("last_done")
        if not last_done_str:
            return True
    
        try:
            last_done = datetime.datetime.strptime(last_done_str, "%Y-%m-%d").date()
        except ValueError:
            return True
    
        days_since_done = (datetime.date.today() - last_done).days
        return days_since_done >= threshold

    def get_task_urgency_score(self, task_name):
        """Calculate an urgency score based on days since last completion and priority"""
        # Skip celebration messages
        metadata = self.task_metadata.get(task_name)
        if not metadata:
            print(f"[Warning] No metadata for task '{task_name}'")
            return 0  # or a default urgency score
    
        frequency = metadata.get("frequency", "unknown")
        threshold = {
            "daily": 3,
            "weekly": 10,
            "biweekly": 18,
            "monthly": 35,
            "quarterly": 100
        }.get(frequency, 7)
    
        last_done_data = self.task_history.get(task_name)
        if last_done_data is None:
            return threshold  # assume max urgency if never done
        
        last_done_str = last_done_data.get("last_done")
        if not last_done_str:
            return threshold  # assume max urgency if never done
    
        try:
            last_done = datetime.datetime.strptime(last_done_str, "%Y-%m-%d").date()
        except ValueError:
            return threshold  # assume max urgency if invalid date
    
        days_since_done = (datetime.date.today() - last_done).days
        return days_since_done / threshold


    def was_task_done_recently(self, task_name, days_threshold):
        """Return True if the task was completed within days_threshold"""
        days_since = self.get_days_since_task_completion(task_name)
        return days_since < days_threshold

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
            result["monthly_tasks"] = self.daily_task_assignments.get(today_str, {}).get("monthly_tasks", [])
            print(f"Monthly tasks from daily assignments: {result['monthly_tasks']}")
            if not result["monthly_tasks"]:
                monthly_tasks = self.get_monthly_task()
                print(f"Monthly tasks from get_monthly_task: {monthly_tasks}")
                result["monthly_tasks"] = monthly_tasks

            result["variety_tasks"] = self.daily_task_assignments.get(today_str, {}).get("variety_tasks", [])
            result["quarterly_focus"] = self.get_quarterly_task()

            # Add up to 5 additional overdue quarterly-frequency tasks
            overdue_quarterly = [
                task for task, meta in self.task_metadata.items()
                if meta.get("frequency") == "quarterly" and self.is_task_due(task) and task != result["quarterly_focus"]
            ]
            
            # Sort by days since last done (most overdue first)
            overdue_quarterly.sort(key=self.get_days_since_task_completion, reverse=True)
            result["extra_quarterly_tasks"] = overdue_quarterly[:5]

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
            # Get completion dates if they exist
            if "completion_dates" in data:
                for completion in data.get("completion_dates", []):
                    if isinstance(completion, dict) and "date" in completion:
                        dates_with_completions.add(completion["date"])

        # Convert to date objects and sort
        completion_dates = []
        for date_str in dates_with_completions:
            try:
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                completion_dates.append(date_obj)
            except ValueError:
                continue
                
        completion_dates.sort(reverse=True)

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

    def _load_task_history(self):
        """Load task history from Airtable"""
        return self.backend.get_task_history(self.username)

    def _load_or_generate_daily_tasks(self):
        """Load daily tasks from Airtable or generate if not found"""
        today_str = self.current_date.strftime("%Y-%m-%d")
        
        # Try to load from Airtable
        daily_tasks = self.backend.get_daily_tasks(self.username, today_str)
        
        if daily_tasks:
            return {today_str: daily_tasks}
        else:
            # Generate new tasks if not found
            new_tasks = self._generate_todays_tasks()
            
            # Save to Airtable
            self.backend.save_daily_tasks(self.username, today_str, new_tasks)
            
            return {today_str: new_tasks}
