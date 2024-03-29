import tkinter as tk
import json
import os
import requests
from datetime import datetime
from typing import List
from tkinter import ttk, messagebox, simpledialog
from objects import ActivityTracker
import pandas as pd

from util import pretty_duration, get_number, str_to_datetime, datetime_to_str, ask_time

config = {}
if not os.path.exists('config.json'):
    raise Exception('config.json not found')

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

class TimeTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Time Tracker")
        self.geometry("1280x720")

        self.data = ActivityTracker()

        self.add_activity_frame = ttk.Frame(self)
        self.add_activity_frame.pack(side=tk.TOP, fill=tk.X)

        self.activities_frame = ttk.Frame(self)
        self.activities_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.report_frame = ttk.Frame(self)
        self.report_frame.pack(side=tk.TOP, fill=tk.X)

        self.create_widgets()

    def create_widgets(self):
        # Add activity widgets
        self.add_activity_button = ttk.Button(self.add_activity_frame, text="Add Activity", command=self.add_activity)
        self.add_activity_button.pack(side=tk.LEFT, padx=(0, 10))

        self.remove_activity_button = ttk.Button(self.add_activity_frame, text="Remove Activity", command=self.remove_activity)
        self.remove_activity_button.pack(side=tk.LEFT)

        # Current activity stats
        self.current_activity_time_label = ttk.Label(self.add_activity_frame, text="0:00:00")
        self.current_activity_time_label.pack(side=tk.RIGHT)

        self.current_activity_colon = ttk.Label(self.add_activity_frame, text=": ")
        self.current_activity_colon.pack(side=tk.RIGHT)

        self.current_activity_label = ttk.Label(self.add_activity_frame, text="None selected")
        self.current_activity_label.pack(side=tk.RIGHT)

        # Create a style object and configure the row height
        style = ttk.Style()
        style.configure("Treeview", rowheight=40)

        # Activities list
        self.activities_list = ttk.Treeview(self.activities_frame, style="Treeview")
        self.activities_list["columns"] = ("Activity", "Time", "7_Day")
        self.activities_list.column("#0", width=0, stretch=tk.NO)
        self.activities_list.column("Activity", anchor=tk.W, width=150)
        self.activities_list.column("Time", anchor=tk.W, width=100)
        self.activities_list.column("7_Day", anchor=tk.W, width=100)
        self.activities_list.heading("Activity", text="Activity", anchor=tk.W)
        self.activities_list.heading("7_Day", text="7 Day", anchor=tk.W)
        self.activities_list.heading("Time", text="Time", anchor=tk.W)
        self.activities_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.activities_list_scrollbar = ttk.Scrollbar(self.activities_frame, orient="vertical", command=self.activities_list.yview)
        self.activities_list.configure(yscrollcommand=self.activities_list_scrollbar.set)
        self.activities_list_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.activities_list.bind("<<TreeviewSelect>>", self.show_instance_list)

        # Instance list
        self.instance_list = ttk.Treeview(self.activities_frame, style="Treeview")
        self.instance_list["columns"] = ("Date", "start_time", "stop_time", "Duration")
        self.instance_list.column("#0", width=0, stretch=tk.NO)
        self.instance_list.column("Date", anchor=tk.W, width=100)
        self.instance_list.column("start_time", anchor=tk.W, width=75)
        self.instance_list.column("stop_time", anchor=tk.W, width=75)
        self.instance_list.column("Duration", anchor=tk.W, width=100)
        self.instance_list.heading("Date", text="Date", anchor=tk.W)
        self.instance_list.heading("start_time", text="Start Time", anchor=tk.W)
        self.instance_list.heading("stop_time", text="Stop Time", anchor=tk.W)
        self.instance_list.heading("Duration", text="Duration", anchor=tk.W)
        self.instance_list.pack_forget()

        self.instance_list_scrollbar = ttk.Scrollbar(self.activities_frame, orient="vertical", command=self.instance_list.yview)
        self.instance_list.configure(yscrollcommand=self.instance_list_scrollbar.set)
        self.instance_list_scrollbar.pack_forget()

        # Timer control buttons
        self.start_timer_button = ttk.Button(self.activities_frame, text="Start Timer", command=self.start_timer)
        self.stop_timer_button = ttk.Button(self.activities_frame, text="Stop Timer", command=self.stop_timer)
        self.activities_button = ttk.Button(self.activities_frame, text="Activities", command=self.show_activities_list)
        self.add_instance_button = ttk.Button(self.activities_frame, text="Add Instance", command=self.add_manual_instance)
        self.delete_instance_button = ttk.Button(self.activities_frame, text="Delete", command=self.delete_instance)
        self.hours_last_week_label = ttk.Label(self.activities_frame, text="0:00")

        # Save button
        self.save_data_button = ttk.Button(self.report_frame, text="Save Data", command=self.save_data)
        self.save_data_button.pack(side=tk.LEFT, padx=(10, 5), pady=10)

        self.load_data()

        # Initialize the live timer update
        self.update_live_timer()

    def show_activities_list(self):
        self.data.unload_activity()
        self.instance_list.pack_forget()
        self.start_timer_button.pack_forget()
        self.stop_timer_button.pack_forget()
        self.activities_button.pack_forget()
        self.add_instance_button.pack_forget()
        self.delete_instance_button.pack_forget()
        self.hours_last_week_label.pack_forget()
        self.activities_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.reset_current_activity_label()

    def show_instance_list(self, event):
        selected_item = self.activities_list.selection()
        if len(selected_item) == 0:
            return
        activity_name = selected_item[0]
        if not self.data.set_activity(activity_name):
            return
        self.activities_list.pack_forget()
        self.instance_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.instance_list.delete(*self.instance_list.get_children())
        for i in self.data.get_current_activity().get_sorted_instances():
            self.instance_list.insert("", tk.END, i.to_string(), values=(i.pretty_date(), i.pretty_start_time(), i.pretty_stop_time(), pretty_duration(i.duration)))
        self.start_timer_button.pack(side=tk.TOP, pady=(10, 5))
        self.activities_button.pack(side=tk.TOP, pady=(5, 10))
        self.delete_instance_button.pack(side=tk.TOP, pady=(5, 10))
        self.add_instance_button.pack(side=tk.TOP, pady=(5, 10))
        self.hours_last_week_label.pack(side=tk.TOP, pady=(5, 10))
        self.hours_last_week_label.config(text='7 Day: ' + pretty_duration(self.data.get_current_activity().get_hours_last_week()))

        self.current_activity_label.config(text=activity_name)
        self.current_activity_time_label.config(text="0:00:00")
        self.current_activity_colon.config(text=": ")

    def delete_instance(self):
        selected_item = self.instance_list.selection()
        if len(selected_item) == 0:
            print("Delete Instance: no selected item")
            return
        result = messagebox.askyesno("Delete Instance", "Are you sure?")
        if not result:
            return
        if not self.data.get_current_activity().delete_instance(selected_item[0]):
            return
        self.show_activities_list()
        self.show_instance_list(None)
        self.save_data()

    def save_data(self):
        self.data.to_dataframe().to_csv("activities.csv", index=False)
        print("Data Saved!")

    def get_data_from_server(self):
        if 'server' not in config or 'server_port' not in config:
            print('Server or server port not in config file, reading locally')
            return None
        ip = config['server']
        port = config['server_port']
        res = requests.post(f'http://{ip}:{port}/retrieve', json={
            "password": config['password']    
        })
        if res.status_code != 200:
            print(f'Server responded with {res.status_code}, {res.content.decode()}')
            return None
        data = res.content.decode()
        print('Loaded data from server, writing activities file')
        if len(data) > 0:
            with open('activities.csv', 'w', encoding='utf-8') as f:
                f.write(data)
        return data

    def sync_data(self):
        if 'server' not in config or 'server_port' not in config:
            print('Server or server port not in config file, reading locally')
            return None
        if 'password' not in config:
            print('Password not in config')
            return None
        ip = config['server']
        port = config['server_port']
        f = open('activities.csv', 'r', encoding='utf-8')
        data = f.read()
        f.close()
        res = requests.post(f'http://{ip}:{port}/sync', json={
            "password": config['password'],
            "data": data
        })
        if res.status_code != 200:
            print(f'Server responded with {res.status_code}, {res.content.decode()}')
            return None
        print('Data Synced to server')

    def load_data(self):
        self.get_data_from_server()

        file_name = "activities.csv"
        if not os.path.exists(file_name):
            return
        df = pd.read_csv("activities.csv")
        self.data = ActivityTracker.from_dataframe(df)
        for k in self.data.activities.keys():
            self.activities_list.insert("", tk.END, k, values=(
                k, 
                pretty_duration(self.data.activities[k].get_total_time()), 
                pretty_duration(self.data.activities[k].get_hours_last_week())
            ))

    def add_activity(self):
        activity_name = simpledialog.askstring("Activity Title", "What is the name of the activity?")
        if activity_name == None or len(activity_name) == 0:
            return
        if activity_name and self.data.name_available(activity_name):
            self.data.add_activity(activity_name)
            self.activities_list.insert("", tk.END, activity_name, values=(activity_name, "0:00:00"))

    def remove_activity(self):
        result = messagebox.askyesno("Remove Activity?", "Are you sure?")
        if not result:
            return
        selected_item = self.activities_list.selection()
        if selected_item:
            activity_name = selected_item[0]
            self.data.remove_activity(activity_name)
            self.activities_list.delete(activity_name)
        self.save_data()
        self.sync_data()

    def start_timer(self):
        if self.data.timer_running():
            print(f"Stopping timer")
            self.stop_timer()
        
        selected_item = self.activities_list.selection()
        if not selected_item:
            print("No currently selected item")
            return
        self.start_timer_button.pack_forget()
        self.stop_timer_button.pack(side=tk.TOP, pady=(5, 10))
        
        print("Starting timer")
        activity_name = selected_item[0]
        self.data.start_timer(activity_name)

    def add_manual_instance(self):
        start_time = ask_time('Start Time')
        if start_time is None:
            return
        end_time = ask_time('End Time')
        if end_time is None:
            return

        instance = self.data.get_current_activity().add_instance()
        instance.start_time = start_time
        instance.end_time = end_time
        instance.duration = end_time - start_time
        self.save_data()
        self.sync_data()
        self.show_activities_list()
        self.show_instance_list(None)

    def reset_current_activity_label(self):
        self.current_activity_label.config(text="")
        self.current_activity_time_label.config(text="")
        self.current_activity_colon.config(text="")

    def stop_timer(self):
        current_activity = self.data.get_current_activity()
        if self.data.stop_timer() is None:
            return
        self.stop_timer_button.pack_forget()
        self.start_timer_button.pack(side=tk.TOP, pady=(5, 10))
        self.activities_list.set(current_activity.name, "Time", current_activity.get_total_time())
        self.current_activity_time_label.config(text="0:00:00")
        self.current_activity_colon.config(text=": ")
        self.save_data()
        self.sync_data()
        self.show_activities_list()
        self.show_instance_list(None)

    def update_live_timer(self):
        current_time = self.data.get_current_time()
        if current_time is not None:
            self.current_activity_time_label.config(text=current_time)

        self.after(1000, self.update_live_timer)

if __name__ == "__main__":
    app = TimeTrackerApp()
    app.mainloop()
