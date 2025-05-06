# airtable_backend.py
from pyairtable import Table
import streamlit as st
import datetime

class AirtableBackend:
    def __init__(self):
        config = st.secrets["airtable"]
        self.token = config["token"]
        self.base_id = config["base_id"]
        self.table_history_name = config["table_history"]
        self.table_metadata_name = config["table_metadata"]

        self.table_history = Table(self.token, self.base_id, self.table_history_name)
        self.table_metadata = Table(self.token, self.base_id, self.table_metadata_name)

    def get_task_history(self, username):
        records = self.table_history.all(formula=f"{{username}} = '{username}'")
        history = {}
        for r in records:
            task = r['fields'].get('task')
            if not task:
                continue
            history[task] = {
                "last_done": r['fields'].get("last_done", ""),
                "completion_count": r['fields'].get("completion_count", 0),
                "completion_dates": r['fields'].get("completion_dates", [])
            }
        return history

    def update_task_history(self, username, task):
        today = datetime.date.today().isoformat()
        match = self.table_history.first(formula=f"AND({{username}} = '{username}', {{task}} = '{task}')")
        if match:
            fields = match["fields"]
            count = fields.get("completion_count", 0) + 1
            dates = fields.get("completion_dates", [])
            if isinstance(dates, str):
                import json
                try:
                    dates = json.loads(dates)
                except:
                    dates = []
            dates.append(today)
            self.table_history.update(match["id"], {
                "last_done": today,
                "completion_count": count,
                "completion_dates": dates,
            })
        else:
            self.table_history.create({
                "username": username,
                "task": task,
                "last_done": today,
                "completion_count": 1,
                "completion_dates": [today],
            })

    def get_task_metadata(self):
        records = self.table_metadata.all()
        metadata = {}
        for r in records:
            task = r['fields'].get('task')
            if not task:
                continue
            metadata[task] = {
                "frequency": r['fields'].get("frequency", "unknown"),
                "priority": r['fields'].get("priority", "priority3"),
            }
        return metadata
