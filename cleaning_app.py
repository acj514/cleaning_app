import streamlit as st
import pandas as pd
import datetime
from adaptive_cleaning_scheduler_complete import AdaptiveCleaningScheduler

# Initialize the scheduler
scheduler = AdaptiveCleaningScheduler()

st.set_page_config(page_title="Adaptive Cleaning Scheduler", layout="wide", initial_sidebar_state="expanded")

st.title("🧹 Adaptive Cleaning Scheduler")

username = st.text_input("Enter your name to access your personalized cleaning schedule:", "")

# Only show the rest of the app if a username is provided
if username:
    # Initialize the scheduler with the username
    scheduler = AdaptiveCleaningScheduler(username=username)

    # Sidebar Menu
    menu = st.sidebar.radio(
        "📋 Menu",
        ["Today's Recommendations", "Mark Tasks Completed", "View Task History", "View Statistics", "Task Dashboard", "Reset Today's Tasks"],
        format_func=lambda x: x  # Optional: makes sure formatting stays clean
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

        # Filter out completed daily tasks
        uncompleted_daily_tasks = []
        for task in recs['daily_tasks']:
            if isinstance(task, str) and task.startswith("🎉"):
                st.info(task)
                continue

            history = scheduler.task_history.get(task, {})
            last_done = history.get("last_done", "")
            done_today = last_done == today_str

            # Only add to list if not done today
            if not done_today:
                uncompleted_daily_tasks.append(task)

        # Check if all tasks were completed
        if not uncompleted_daily_tasks:
            st.markdown(
                """
                <div style="background-color: rgba(27, 54, 93, 0.5); 
                            padding: 10px 15px; 
                            border-radius: 5px; 
                            margin-bottom: 10px">
                    <span style="color: #ffffff">🎉 All daily tasks completed! Great job!</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Display only uncompleted tasks
            for task in uncompleted_daily_tasks:
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

                checked = st.checkbox(label, value=False, key=f"daily_{task}")
                if checked:
                    scheduler.mark_task_completed(task)
                    st.success(f"✅ Marked as completed: {task}")
                    st.rerun()

        # VARIETY TASKS
        if energy_level == "green" and recs.get("variety_tasks"):
            st.markdown('<div style="padding-left: 1.5em;">', unsafe_allow_html=True)
            st.markdown("###### ✨ Bonus Variety Tasks")
            st.caption("Tasks not done recently, sorted by urgency!")

            # Filter out completed variety tasks
            uncompleted_variety_tasks = []
            for task in recs["variety_tasks"]:
                history = scheduler.task_history.get(task, {})
                last_done = history.get("last_done", "")
                done_today = last_done == today_str

                # Only add to list if not done today
                if not done_today:
                    uncompleted_variety_tasks.append(task)

            if not uncompleted_variety_tasks:
                st.markdown(
                    """
                    <div style="background-color: rgba(27, 54, 93, 0.5); 
                                padding: 10px 15px; 
                                border-radius: 5px; 
                                margin-bottom: 10px">
                        <span style="color: #ffffff">🎉 All variety tasks completed! Amazing!</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                for task in uncompleted_variety_tasks:
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
                        checked = st.checkbox(label, value=False, key=f"variety_{task}")
                        if checked:
                            scheduler.mark_task_completed(task)
                            st.success(f"✅ Marked as completed: {task}")
                            st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        # 🔄 WEEKLY TASKS
        st.write(f"#### 🔄 Weekly Focus Tasks – {recs['week_focus']}")
        if not recs['weekly_tasks']:
            # If no weekly tasks, show a styled container
            st.markdown(
                """
                <div style="background-color: rgba(27, 54, 93, 0.5); 
                            padding: 10px 15px; 
                            border-radius: 5px; 
                            margin-bottom: 10px">
                    <span style="color: #ffffff">🎉 No weekly focus tasks needed today!</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Filter out completed weekly tasks
            uncompleted_weekly_tasks = []
            for task in recs['weekly_tasks']:
                if isinstance(task, str) and task.startswith("🎉"):
                    st.info(task)
                    continue

                uncompleted_weekly_tasks.append(task)

            # Check if all tasks were completed
            if not uncompleted_weekly_tasks:
                st.markdown(
                    """
                    <div style="background-color: rgba(27, 54, 93, 0.5); 
                                padding: 10px 15px; 
                                border-radius: 5px; 
                                margin-bottom: 10px">
                        <span style="color: #ffffff">🎉 All weekly tasks completed! Great job!</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                # Display only uncompleted tasks
                for task in uncompleted_weekly_tasks:
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

                    checked = st.checkbox(label, value=False, key=f"weekly_{task}")
                    if checked:
                        scheduler.mark_task_completed(task)
                        st.success(f"✅ Marked as completed: {task}")
                        st.rerun()

        # 📅 BIWEEKLY TASKS
        if energy_level != "red" and "biweekly_tasks" in recs:
            st.write("#### 📅 Biweekly Tasks")

            # Filter tasks to only get actual tasks (not celebration messages)
            actual_biweekly_tasks = [task for task in recs['biweekly_tasks'] if
                                     not (isinstance(task, str) and task.startswith("🎉"))]

            if not actual_biweekly_tasks:
                st.markdown(
                    """
                    <div style="background-color: rgba(27, 54, 93, 0.5); 
                                padding: 10px 15px; 
                                border-radius: 5px; 
                                margin-bottom: 10px">
                        <span style="color: #ffffff">🎉 No biweekly tasks needed today!</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                # Filter out completed biweekly tasks
                uncompleted_biweekly_tasks = []
                for task in recs['biweekly_tasks']:
                    if isinstance(task, str) and task.startswith("🎉"):
                        st.info(task)
                        continue

                    history = scheduler.task_history.get(task, {})
                    last_done = history.get("last_done", "")
                    done_today = last_done == today_str

                    # Only add to list if not done today
                    if not done_today:
                        uncompleted_biweekly_tasks.append(task)

                # Check if all tasks were completed
                if not uncompleted_biweekly_tasks and actual_biweekly_tasks:
                    st.markdown(
                        """
                        <div style="background-color: rgba(27, 54, 93, 0.5); 
                                    padding: 10px 15px; 
                                    border-radius: 5px; 
                                    margin-bottom: 10px">
                            <span style="color: #ffffff">🎉 All biweekly tasks completed! Great job!</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    # Display only uncompleted tasks
                    for task in uncompleted_biweekly_tasks:
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

                        checked = st.checkbox(label, value=False, key=f"biweekly_{task}")
                        if checked:
                            scheduler.mark_task_completed(task)
                            st.success(f"✅ Marked as completed: {task}")
                            st.rerun()

        # 🌟 MONTHLY TASKS
        if energy_level == "green" and "monthly_tasks" in recs:
            st.write("#### 🌟 Monthly Tasks")

            # Filter tasks to only get actual tasks (not celebration messages)
            actual_monthly_tasks = [task for task in recs['monthly_tasks'] if
                                    not (isinstance(task, str) and task.startswith("🎉"))]

            if not actual_monthly_tasks:
                st.markdown(
                    """
                    <div style="background-color: rgba(27, 54, 93, 0.5); 
                                padding: 10px 15px; 
                                border-radius: 5px; 
                                margin-bottom: 10px">
                        <span style="color: #ffffff">🎉 No monthly tasks needed today!</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                # Filter out completed monthly tasks
                uncompleted_monthly_tasks = []
                for task in recs['monthly_tasks']:
                    if isinstance(task, str) and task.startswith("🎉"):
                        st.info(task)
                        continue

                    history = scheduler.task_history.get(task, {})
                    last_done = history.get("last_done", "")
                    done_today = last_done == today_str

                    # Only add to list if not done today
                    if not done_today:
                        uncompleted_monthly_tasks.append(task)

                # Check if all tasks were completed
                if not uncompleted_monthly_tasks and actual_monthly_tasks:
                    st.markdown(
                        """
                        <div style="background-color: rgba(27, 54, 93, 0.5); 
                                    padding: 10px 15px; 
                                    border-radius: 5px; 
                                    margin-bottom: 10px">
                            <span style="color: #ffffff">🎉 All monthly tasks completed! Great job!</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    # Display only uncompleted tasks
                    for task in uncompleted_monthly_tasks:
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

                        checked = st.checkbox(label, value=False, key=f"monthly_{task}")
                        if checked:
                            scheduler.mark_task_completed(task)
                            st.success(f"✅ Marked as completed: {task}")
                            st.rerun()

        # 🗓️ QUARTERLY TASKS
    if energy_level == "green" and "quarterly_focus" in recs:
        st.write("#### 🗓️ Quarterly Focus")
        task = recs["quarterly_focus"]
        if isinstance(task, str) and task.startswith("🎉"):
            st.info(task)
        else:
            history = scheduler.task_history.get(task, {})
            last_done = history.get("last_done", "")
            done_today = last_done == today_str
    
            if done_today:
                st.markdown(
                    """
                    <div style="background-color: rgba(27, 54, 93, 0.5); 
                                padding: 10px 15px; 
                                border-radius: 5px; 
                                margin-bottom: 10px">
                        <span style="color: #ffffff">🎉 Quarterly focus task completed! Excellent!</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)
    
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"
    
                    label = f"{task} ({frequency} task, urgency: {urgency})"
                else:
                    label = task
    
                checked = st.checkbox(label, value=False, key=f"quarterly_{task}")
                if checked:
                    scheduler.mark_task_completed(task)
                    st.success(f"✅ Marked as completed: {task}")
                    st.rerun()
    
        # 🧽 Additional Overdue Quarterly-Frequency Tasks
        if recs.get("extra_quarterly_tasks"):
            st.markdown("##### 🧽 Additional Quarterly Tasks")
            for task in recs["extra_quarterly_tasks"]:  # <-- Make sure this loop is wrapping the logic
                history = scheduler.task_history.get(task, {})
                last_done = history.get("last_done", "")
                done_today = last_done == today_str
        
                if done_today:
                    continue  # Skip if already done today
        
                if hasattr(scheduler, 'task_metadata') and task in scheduler.task_metadata:
                    metadata = scheduler.task_metadata[task]
                    frequency = metadata.get("frequency", "unknown")
                    urgency_score = scheduler.get_task_urgency_score(task)
        
                    if urgency_score > 3:
                        urgency = "🔥 HIGH"
                    elif urgency_score > 1.5:
                        urgency = "⚠️ MEDIUM"
                    else:
                        urgency = "✓ LOW"
        
                    label = f"{task} ({frequency} task, urgency: {urgency})"
                else:
                    label = task
        
                checked = st.checkbox(label, value=False, key=f"quarterly_extra_{task}")
                if checked:
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
                for task in overdue_tasks[:]:  # Show top 15 most urgent
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

else:
    st.info("Please enter your name above to get started with your personalized cleaning schedule.")
