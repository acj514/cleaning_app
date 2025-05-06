import os
import datetime
from typing import Dict, List, Optional, Any
import requests
import json
import time

class AirtableBackend:
    def __init__(self):
        # Get Airtable credentials from environment variables
        self.api_key = os.environ.get('AIRTABLE_API_KEY')
        self.base_id = os.environ.get('AIRTABLE_BASE_ID')
        
        # Define table names
        self.task_history_table = 'task_history'
        self.daily_tasks_table = 'daily_tasks'
        
        # Airtable API base URL
        self.api_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        # Set up headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Verify credentials
        if not self.api_key or not self.base_id:
            print("⚠️ Warning: Airtable credentials not found in environment variables.")
            print("Please set AIRTABLE_API_KEY and AIRTABLE_BASE_ID environment variables.")
        else:
            # Check if tables exist and create them if they don't
            self._ensure_tables_exist()
    
    def get_task_history(self, username: str) -> Dict[str, Any]:
        """
        Retrieve task history for a specific user from Airtable
        
        Returns a dictionary where:
        - Keys are task names
        - Values are dictionaries with completion data
        """
        # Initialize empty history
        task_history = {}
        
        try:
            # Check if the table exists first
            try:
                response = requests.get(
                    f"{self.api_url}/{self.task_history_table}",
                    headers=self.headers,
                    params={'maxRecords': 1}  # Just check if table exists
                )
                
                # If 404, table doesn't exist
                if response.status_code == 404:
                    print(f"Task history table not found. Creating table...")
                    self._create_task_history_table()
                    # Return empty results for now
                    return {}
                    
            except Exception as e:
                print(f"Error checking if task history table exists: {e}")
            
            # Query Airtable for records matching this username
            params = {
                'filterByFormula': f"{{username}}='{username}'"
            }
            
            response = requests.get(
                f"{self.api_url}/{self.task_history_table}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    # Table doesn't exist, create it
                    print(f"Task history table not found. Creating table...")
                    self._create_task_history_table()
                    return {}
                else:
                    print(f"Error fetching task history: {response.status_code}")
                    print(response.text)
                    return {}
            
            # Process the response
            records = response.json().get('records', [])
            
            for record in records:
                fields = record.get('fields', {})
                task_name = fields.get('task_name')
                
                if not task_name:
                    continue
                
                task_history[task_name] = {
                    'completion_count': fields.get('completion_count', 0),
                    'last_done': fields.get('last_done', ''),
                    'record_id': record.get('id')  # Store record ID for updates
                }
                
                # If completion_dates field exists, parse it
                if 'completion_dates' in fields and fields['completion_dates']:
                    try:
                        completion_dates = json.loads(fields['completion_dates'])
                        task_history[task_name]['completion_dates'] = completion_dates
                    except:
                        task_history[task_name]['completion_dates'] = []
                else:
                    task_history[task_name]['completion_dates'] = []
            
            return task_history
            
        except Exception as e:
            print(f"Error retrieving task history: {e}")
            return {}
    
    def update_task_history(self, username: str, task_name: str, notes: str = "") -> bool:
        """
        Update task history when a task is completed
        """
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # First, check if we already have this task in history
        task_history = self.get_task_history(username)
        
        if task_name in task_history:
            # Update existing record
            record_id = task_history[task_name].get('record_id')
            completion_count = task_history[task_name].get('completion_count', 0) + 1
            
            # Get existing completion dates or initialize empty list
            completion_dates = task_history[task_name].get('completion_dates', [])
            
            # Add new completion
            completion_dates.append({
                "date": today,
                "notes": notes
            })
            
            # Prepare update data
            data = {
                "fields": {
                    "completion_count": completion_count,
                    "last_done": today,
                    "completion_dates": json.dumps(completion_dates)
                }
            }
            
            try:
                # Update record in Airtable
                response = requests.patch(
                    f"{self.api_url}/{self.task_history_table}/{record_id}",
                    headers=self.headers,
                    data=json.dumps(data)
                )
                
                if response.status_code not in [200, 201]:
                    print(f"Error updating task history: {response.status_code}")
                    print(response.text)
                    return False
                
                return True
                
            except Exception as e:
                print(f"Error updating task history: {e}")
                return False
        else:
            # Create new record - debug the data we're sending
            completion_dates = [{
                "date": today,
                "notes": notes
            }]
            
            data = {
                "fields": {
                    "username": username,
                    "task_name": task_name,
                    "completion_count": 1,
                    "last_done": today,
                    "completion_dates": json.dumps(completion_dates)
                }
            }
            
            print(f"Creating new task history with data: {json.dumps(data, indent=2)}")
            
            try:
                # Create new record in Airtable
                response = requests.post(
                    f"{self.api_url}/{self.task_history_table}",
                    headers=self.headers,
                    data=json.dumps(data)
                )
                
                if response.status_code not in [200, 201]:
                    print(f"Error creating task history: {response.status_code}")
                    print(f"Response: {response.text}")
                    
                    # Try an alternative format for the Date field
                    data["fields"]["last_done"] = {
                        "date": today  # Format as object with date property
                    }
                    
                    print(f"Trying alternative date format: {json.dumps(data, indent=2)}")
                    
                    alt_response = requests.post(
                        f"{self.api_url}/{self.task_history_table}",
                        headers=self.headers,
                        data=json.dumps(data)
                    )
                    
                    if alt_response.status_code not in [200, 201]:
                        print(f"Alternative format also failed: {alt_response.status_code}")
                        print(f"Response: {alt_response.text}")
                        return False
                    
                return True
                
            except Exception as e:
                print(f"Error creating task history: {e}")
                return False
    
    def save_daily_tasks(self, username: str, date_str: str, task_assignments: Dict) -> bool:
        """
        Save daily task assignments to Airtable
        """
        # Check if the table exists first
        try:
            response = requests.get(
                f"{self.api_url}/{self.daily_tasks_table}",
                headers=self.headers,
                params={'maxRecords': 1}  # Just check if table exists
            )
            
            # If 404, table doesn't exist
            if response.status_code == 404:
                print(f"Daily tasks table not found. Creating table...")
                self._create_daily_tasks_table()
                # Wait a moment for table creation to complete
                time.sleep(1)
        except Exception as e:
            print(f"Error checking if daily tasks table exists: {e}")
        
        # First check if we already have a record for this date and user
        params = {
            'filterByFormula': f"AND({{username}}='{username}', {{date}}='{date_str}')"
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/{self.daily_tasks_table}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    # Table doesn't exist, create it
                    print(f"Daily tasks table not found. Creating table...")
                    self._create_daily_tasks_table()
                    # Wait a moment for table creation to complete
                    time.sleep(1)
                    
                    # After creating table, proceed with creating new record
                    return self._create_new_daily_tasks_record(username, date_str, task_assignments)
                else:
                    print(f"Error checking for existing daily tasks: {response.status_code}")
                    print(response.text)
                    return False
                
            records = response.json().get('records', [])
            
            # Convert task assignments to JSON string for storage
            task_assignments_json = json.dumps(task_assignments)
            
            if records:
                # Update existing record
                record_id = records[0].get('id')
                
                data = {
                    "fields": {
                        "task_assignments": task_assignments_json
                    }
                }
                
                update_response = requests.patch(
                    f"{self.api_url}/{self.daily_tasks_table}/{record_id}",
                    headers=self.headers,
                    data=json.dumps(data)
                )
                
                if update_response.status_code not in [200, 201]:
                    print(f"Error updating daily tasks: {update_response.status_code}")
                    print(update_response.text)
                    return False
                    
                return True
            else:
                # Create new record
                return self._create_new_daily_tasks_record(username, date_str, task_assignments)
                
        except Exception as e:
            print(f"Error saving daily tasks: {e}")
            return False
            
    def _create_new_daily_tasks_record(self, username: str, date_str: str, task_assignments: Dict) -> bool:
        """Helper method to create a new daily tasks record"""
        # Convert task assignments to JSON string for storage
        task_assignments_json = json.dumps(task_assignments)
        
        data = {
            "fields": {
                "username": username,
                "date": date_str,
                "task_assignments": task_assignments_json
            }
        }
        
        try:
            create_response = requests.post(
                f"{self.api_url}/{self.daily_tasks_table}",
                headers=self.headers,
                data=json.dumps(data)
            )
            
            if create_response.status_code not in [200, 201]:
                print(f"Error creating daily tasks: {create_response.status_code}")
                print(create_response.text)
                return False
                
            return True
        except Exception as e:
            print(f"Error creating daily tasks record: {e}")
            return False
    
    def get_daily_tasks(self, username: str, date_str: str) -> Dict:
        """
        Retrieve daily task assignments from Airtable
        """
        # Check if the table exists first
        try:
            response = requests.get(
                f"{self.api_url}/{self.daily_tasks_table}",
                headers=self.headers,
                params={'maxRecords': 1}  # Just check if table exists
            )
            
            # If 404, table doesn't exist
            if response.status_code == 404:
                print(f"Daily tasks table not found. Creating table...")
                self._create_daily_tasks_table()
                # Return empty results for now
                return {}
                
        except Exception as e:
            print(f"Error checking if daily tasks table exists: {e}")
        
        # Now try to get the data
        params = {
            'filterByFormula': f"AND({{username}}='{username}', {{date}}='{date_str}')"
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/{self.daily_tasks_table}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    # Table doesn't exist, create it
                    print(f"Daily tasks table not found. Creating table...")
                    self._create_daily_tasks_table()
                    return {}
                else:
                    print(f"Error fetching daily tasks: {response.status_code}")
                    print(response.text)
                    return {}
                
            records = response.json().get('records', [])
            
            if not records:
                return {}
                
            # Get the task assignments from the first matching record
            task_assignments_json = records[0].get('fields', {}).get('task_assignments', '{}')
            
            try:
                return json.loads(task_assignments_json)
            except:
                return {}
                
        except Exception as e:
            print(f"Error retrieving daily tasks: {e}")
            return {}
    
    def get_all_daily_tasks(self, username: str) -> Dict[str, Dict]:
        """
        Retrieve all daily task assignments for a user
        """
        params = {
            'filterByFormula': f"{{username}}='{username}'"
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/{self.daily_tasks_table}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                print(f"Error fetching all daily tasks: {response.status_code}")
                print(response.text)
                return {}
                
            records = response.json().get('records', [])
            
            daily_tasks = {}
            for record in records:
                fields = record.get('fields', {})
                date_str = fields.get('date')
                
                if not date_str:
                    continue
                    
                task_assignments_json = fields.get('task_assignments', '{}')
                
                try:
                    daily_tasks[date_str] = json.loads(task_assignments_json)
                except:
                    daily_tasks[date_str] = {}
            
            return daily_tasks
                
        except Exception as e:
            print(f"Error retrieving all daily tasks: {e}")
            return {}
