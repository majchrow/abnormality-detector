from functional import seq
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np
import pylab as pl
from matplotlib import collections as mc
import matplotlib.dates as mdates
from enum import Enum
import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import pdfkit
import os
import datetime
import pandas as pd
import sys, os
from flask import render_template

sys.path.append(os.getcwd())

options = {"enable-local-file-access": None}


class ReportGenerator:
    def __init__(self, dao, name, start_date, end_date):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.call_info_data_provider = CallInfoDataProvider(
            name, dao, start_date, end_date
        )
        self.roster_data_provider = RosterDataProvider(name, dao, start_date, end_date)
        self.calls_data_provider = CallsDataProvider(name, dao, start_date, end_date)
        self.output_dir = "/flask/rest/resources/output/"
        self.output_subdir = "/flask/rest/resources/output/"
        self.resources_dir = "/flask/rest/resources/"
        self.pg = PlotGenerator()
        file_loader = FileSystemLoader(self.resources_dir)
        self.env = Environment(loader=file_loader)

    def generate_pdf_report(self):
        filename = self.__generate_html()
        filepath = f"{self.output_dir}{filename}"
        # pdfkit.from_file(f"{filepath}.html", f"{filepath}.pdf", options=options)
        # self.__delete_all_plots()
        # os.remove(f"{filepath}.html")
        pdf_content = render_template(f"{filename}.html")
        css = f"{self.resources_dir}mystyle.css"

        pdf_file = pdfkit.from_string(pdf_content, False, css=css)

        return pdf_file

    def __get_plot_filename(self, start_datetime, category):
        name = self.name.replace(" ", "")
        timestamp = start_datetime.astype(datetime.datetime)
        return f"{name}_{timestamp}_{category}.svg"

    def __get_html_filename(self):
        current_time = datetime.datetime.now().timestamp()
        name = self.name.replace(" ", "")
        filename = f"{name}_{current_time}"
        return filename

    def __prepare_all_data(self):
        mpd = self.calls_data_provider.get_number_of_meetings_per_day()
        self.general_stats_columns = mpd.columns
        self.general_stats_records = mpd.to_dict("records")
        self.daily_stats_columns = ["start_time", "end_time", "duration"]
        self.daily_stats_records = self.calls_data_provider.get_daily_stats()
        self.meetings = self.calls_data_provider.get_meetings()
        self.plots = self.__generate_plots()
        self.dates = self.calls_data_provider.get_dates()

    def __save_html_file(self, filepath, output):
        with open(filepath, "w") as f:
            f.write(output)

    def __delete_all_plots(self):
        for date in self.plots:
            for meeting in self.plots[date]:
                for plot in self.plots[date][meeting]:
                    os.remove(f"{self.output_dir}{plot}")

    def __generate_html(self):
        self.__prepare_all_data()
        template = self.env.get_template("basic.html")
        print(self.daily_stats_records)
        output = template.render(
            meeting_name=self.name,
            start_date=str(self.start_date),
            end_date=str(self.end_date),
            general_stats_columns=self.general_stats_columns,
            general_stats_records=self.general_stats_records,
            daily_stats_columns=self.daily_stats_columns,
            daily_stats_records=self.daily_stats_records,
            dates=self.dates,
            meetings=self.meetings,
            plots=self.plots,
        )
        filename = self.__get_html_filename()
        self.__save_html_file(f"{self.output_dir}{filename}.html", output)
        return f"{filename}"

    def __generate_plot_for_current_participants(self, start_datetime):
        current_participants = self.call_info_data_provider.get_current_participants(
            start_datetime
        )
        cp_filename = self.__get_plot_filename(start_datetime, "current_participants")
        self.pg.generate_and_save_scatter_plot(
            f"{self.output_dir}{cp_filename}",
            current_participants,
            Titles.CURRENT_PARTICIPANTS.value,
            "blue",
        )
        return f"{cp_filename}"

    def __generate_plot_for_active_speakers(self, start_datetime):
        active_speakers = self.roster_data_provider.get_active_speakers(start_datetime)
        as_filename = self.__get_plot_filename(start_datetime, "active_speakers")
        self.pg.generate_and_save_scatter_plot(
            f"{self.output_dir}{as_filename}",
            active_speakers,
            Titles.ACTIVE_SPEAKERS.value,
            "green",
        )
        return f"{as_filename}"

    def __generate_plots_for_meeting(self, start_datetime):
        cp_filepath = self.__generate_plot_for_current_participants(start_datetime)
        as_filepath = self.__generate_plot_for_active_speakers(start_datetime)

        return [cp_filepath, as_filepath]

    def __generate_plots(self):
        all_filepaths = dict()
        meetings = self.calls_data_provider.get_meetings()
        for date in meetings.keys():
            all_filepaths[date] = dict()
            for meeting in meetings[date]:
                filepaths = self.__generate_plots_for_meeting(meeting)
                all_filepaths[date][meeting] = filepaths

        return all_filepaths


class Titles(Enum):
    CURRENT_PARTICIPANTS = "Number of participants during the meeting"
    ACTIVE_SPEAKERS = "Number of active speakers during the meeting"
    STREAMING = "Time intervals when streaming was turned on"
    RECORDING = "Time intervals when recording was turned on"


class PlotGenerator:
    def generate_and_save_scatter_plot(self, filename, data, title, color):
        data.plot(
            figsize=(10, 5),
            grid=True,
            title=title,
            marker=".",
            linestyle="--",
            markersize=10,
            color=color,
        )
        plt.savefig(filename)


class MeetingDataProvider:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def filter_by_start_datetime(self, start_datetime, df_type):
        print(self.data.head())
        return self.data[self.data["start_datetime"] == start_datetime]


class CallInfoDataProvider(MeetingDataProvider):
    def __init__(self, name, dao, start_date, end_date):
        data = dao.get_call_info_data(name, start_date, end_date)
        MeetingDataProvider.__init__(self, name, data)

    def get_current_participants(self, start_datetime):
        cp = pd.DataFrame(
            self.filter_by_start_datetime(start_datetime, "info")[
                ["time", "current_participants"]
            ]
        )
        cp.index = cp["time"]
        return cp

    def get_streaming_intervals(self, start_datetime):
        filtered = self.filter_by_start_datetime(start_datetime, "info")
        filtered["streaming"] = filtered["streaming"].apply(lambda x: 1 if x else 0)
        return pd.DataFrame(filtered[["datetime", "streaming"]])

    def get_recording_intervals(self, start_datetime):
        filtered = self.filter_by_start_datetime(start_datetime, "info")
        filtered["recording"] = filtered["recording"].apply(lambda x: 1 if x else 0)
        return pd.DataFrame(filtered[["datetime", "recording"]])


class CallsDataProvider(MeetingDataProvider):
    def __init__(self, name, dao, start_date, end_date):
        data = dao.get_calls_data(name, start_date, end_date)
        MeetingDataProvider.__init__(self, name, data)
        self.__init_dates()
        self.__init_meetings()

    def __init_dates(self):
        dates = list(pd.unique(self.data["date"]))
        dates.sort()
        self.dates = dates

    def __get_meetings(self, date):
        meetings = list(
            pd.unique(self.data[self.data["date"] == date]["start_datetime"])
        )
        return meetings

    def __init_meetings(self):
        all_meetings = dict()
        for date in self.dates:
            all_meetings[date] = self.__get_meetings(date)
        self.meetings = all_meetings

    def get_meetings(self):
        return self.meetings

    def get_dates(self):
        return self.dates

    def get_number_of_meetings_per_day(self):
        stats = pd.DataFrame(self.data.groupby(by=["date"]).start_datetime.nunique())
        stats.rename(columns={"start_datetime": "number_of_meetings"}, inplace=True)
        stats.reset_index(inplace=True)
        return stats

    def get_meeting_stats(self, date):
        df = self.data[self.data["date"] == date]
        df.sort_values(by=["start_time"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        def add_columns(row):
            row["end_time"] = (
                str(row["last_update_time"])[:8] if row["finished"] else "-"
            )
            row["start_time"] = str(row["start_time"])[:8]
            row["duration"] = (
                str(
                    self.__convert_seconds_to_time_format(
                        (row["last_update"] - row["start_datetime"]).total_seconds()
                    )
                )
                if row["finished"]
                else "-"
            )
            return row

        df = df.apply(add_columns, axis=1)
        return pd.DataFrame(df[["start_time", "end_time", "duration"]])

    def get_daily_stats(self):
        daily_stats = dict()
        for date in self.dates:
            daily_stats[date] = self.get_meeting_stats(date).to_dict("records")
        return daily_stats

    @staticmethod
    def __convert_seconds_to_time_format(seconds):
        seconds = int(round(seconds))
        hour = int(seconds / 3600)
        minutes = int(seconds / 60) - hour * 60
        seconds = seconds - minutes * 60 - hour * 3600
        hour = str(hour) if hour > 9 else f"0{hour}"
        minutes = str(minutes) if minutes > 9 else f"0{minutes}"
        seconds = str(seconds) if seconds > 9 else f"0{seconds}"
        return f"{hour}:{minutes}:{seconds}"


class RosterDataProvider(MeetingDataProvider):
    def __init__(self, name, dao, start_date, end_date):
        data = dao.get_roster_data(name, start_date, end_date)
        MeetingDataProvider.__init__(self, name, data)

    def get_active_speakers(self, start_datetime):
        asp = pd.DataFrame(
            self.filter_by_start_datetime(start_datetime, "roster")[
                ["time", "active_speaker"]
            ]
        )
        asp.index = asp["time"]
        asp.rename(columns={"active_speaker": "active_speakers"}, inplace=True)
        return asp