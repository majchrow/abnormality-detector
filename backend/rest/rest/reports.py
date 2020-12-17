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
import base64
import unidecode
from .exceptions import NotFoundError
import random
from matplotlib.ticker import MaxNLocator
from matplotlib import gridspec
from flask import current_app

sys.path.append(os.getcwd())

options = {"enable-local-file-access": None}


class ReportGenerator:
    def __init__(self, dao, name, template):
        self.name = name
        self.call_info_data_provider = CallInfoDataProvider(name, dao)
        self.roster_data_provider = RosterDataProvider(name, dao)
        self.calls_data_provider = CallsDataProvider(name, dao)
        self.resources_dir = "/flask/rest/resources/"
        self.template = template
        self.pg = PlotGenerator()
        self.css = f"{self.resources_dir}mystyle.css"

    def generate_plot_for_meeting(self, start_datetime):
        bin_to_zero_one = lambda x: 1 if x else 0
        data = dict()
        data["current_participants"] = self.call_info_data_provider.get_data_for_column(
            start_datetime, "current_participants", parameter="participant"
        )

        data["streaming"] = self.call_info_data_provider.get_data_for_column(
            start_datetime,
            "streaming",
            parameter="streaming",
            apply_func=bin_to_zero_one,
        )
        data["recording"] = self.call_info_data_provider.get_data_for_column(
            start_datetime,
            "recording",
            parameter="recording",
            apply_func=bin_to_zero_one,
        )
        data["active_speakers"] = self.roster_data_provider.get_data_for_column(
            start_datetime,
            "active_speaker",
            "active_speakers",
            parameter="active_speaker",
        )
        data["presenters"] = self.roster_data_provider.get_data_for_column(
            start_datetime, "presenter", "presenters", parameter="presenter"
        )
        data["anomalies"] = self.get_anomalies(start_datetime)

        start = min(data["streaming"].index[0], data["presenters"].index[0])
        end = max(data["streaming"].index[-1], data["presenters"].index[-1])

        plot = self.pg.create_plot(
            data,
            f"{self.resources_dir}{self.get_plot_filename(start_datetime)}",
            start,
            end,
        )
        return plot

    def get_plot_filename(self, start_datetime):
        name = unidecode.unidecode(self.name.replace(" ", ""))
        meeting_time = (
            int(start_datetime.timestamp())
            if type(start_datetime) == pd.Timestamp
            else start_datetime.astype(datetime.datetime)
        )
        return f"{name}_{meeting_time}.png"

    def generate_pdf_report(self):
        self.prepare_all_data()
        pdf_content = self.get_pdf_content()
        pdf_file = pdfkit.from_string(pdf_content, False, css=self.css)

        return pdf_file

    def get_anomalies(self, start_datetime):
        info_anomalies = self.call_info_data_provider.get_anomalies(start_datetime)
        roster_anomalies = self.roster_data_provider.get_anomalies(start_datetime)
        anomalies = pd.concat([info_anomalies, roster_anomalies]).sort_index()
        anomalies = anomalies[~anomalies["ml_anomaly"].isna()]
        if not anomalies.empty:
            anomalies["ml_anomaly"] = "anomaly"
        return anomalies

    def get_pdf_content(self):
        pass

    def prepare_all_data(self):
        pass


class RoomReportGenerator(ReportGenerator):
    def __init__(self, dao, name):
        ReportGenerator.__init__(self, dao, name, "basic_room.html")

    def get_pdf_content(self):
        pdf_content = render_template(
            self.template,
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

        return pdf_content

    def prepare_all_data(self):
        mpd = self.calls_data_provider.get_number_of_meetings_per_day()
        self.general_stats_columns = mpd.columns
        self.general_stats_records = mpd.to_dict("records")
        self.daily_stats_columns = ["start_time", "end_time", "duration"]
        self.daily_stats_records = self.calls_data_provider.get_daily_stats()
        self.meetings = self.calls_data_provider.get_meetings()
        self.plots = self.__generate_plots()
        self.dates = self.calls_data_provider.get_dates()
        self.start_date = self.dates[0]
        self.end_date = self.dates[-1]

    def __generate_plots(self):
        all_plots = dict()
        meetings = self.calls_data_provider.get_meetings()
        for date in meetings.keys():
            all_plots[date] = dict()
            for meeting in meetings[date]:
                all_plots[date][meeting] = self.generate_plot_for_meeting(meeting)

        return all_plots


class MeetingReportGenerator(ReportGenerator):
    def __init__(self, dao, name, start_datetime):
        ReportGenerator.__init__(self, dao, name, "basic_meeting.html")
        self.start_datetime = start_datetime

    def get_pdf_content(self):
        pdf_content = render_template(
            self.template,
            meeting_name=self.name,
            date=self.date,
            start_time=str(self.start_time)[:-7],
            last_update_time=str(self.last_update_time)[:-7],
            duration=self.duration,
            plots=self.plots,
            finished=self.finished,
        )

        return pdf_content

    def prepare_all_data(self):
        details = self.calls_data_provider.get_meeting_details(self.start_datetime)
        self.date = details["date"]
        self.start_time = details["start_time"]
        self.last_update_time = details["last_update_time"]
        self.duration = details["duration"]
        self.finished = details["finished"]
        self.plots = self.generate_plot_for_meeting(self.start_datetime)


class Titles(Enum):
    CURRENT_PARTICIPANTS = "Number of participants during the meeting"
    ACTIVE_SPEAKERS = "Number of active speakers during the meeting"
    STREAMING = "Time intervals when streaming was turned on"
    RECORDING = "Time intervals when recording was turned on"


class PlotGenerator:
    @dataclass
    class Point:
        x: int
        y: int

    @dataclass
    class Segment:
        xa: int
        xb: int
        y: int

    def generate_and_save_scatter_plot(self, filename, data, title, color):
        ax = data.plot(
            figsize=(8, 4),
            grid=True,
            title=title,
            marker=".",
            linestyle="--",
            markersize=10,
            color=color,
        )
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.savefig(filename)
        plot = self.image_file_path_to_base64_string(filename)
        self.remove_plot(filename)
        return plot

    def get_start_and_end(self, anomalies):
        start_date = anomalies["datetime"][0]
        end_date = anomalies["datetime"][-1]
        return {"start": start_date, "end": end_date}

    def create_intervals(self, data, column, color):
        inxval = mdates.date2num(
            np.array([t.to_pydatetime() for t in list(data.index)])
        )
        inyval = data[column]

        points = []
        for x, y in zip(inxval, inyval):
            points.append(self.Point(x, y))

        init = seq(points).init()
        tail = seq(points).tail()

        lines: List[List[Tuple[int, int]]] = (
            init.zip(tail)
            .map(lambda ab: self.make_good_segment(ab[0], ab[1]))
            .filter_not(lambda x: x is None)
            .map(self.segment_array)
            .to_list()
        )

        point = points[-1]
        segment = self.segment_array(self.make_good_segment(point, point))
        lines.append(segment)

        colors = []

        for anomaly in data["anomaly_reason"]:
            if anomaly:
                colors.append("red")
            else:
                colors.append(color)

        lc = mc.LineCollection(lines, linewidths=2, colors=colors)

        return lc

    def make_good_segment(self, a: Point, b: Point) -> Optional[Segment]:
        return self.Segment(xa=a.x, xb=b.x, y=a.y)

    def segment_array(self, s: Segment) -> List[Tuple[int, int]]:
        return [(s.xa, s.y), (s.xb, s.y)]

    @staticmethod
    def remove_plot(filepath):
        os.remove(filepath)

    @staticmethod
    def image_file_path_to_base64_string(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def plot_line(self, timestamp):
        plt.axvline(pd.Timestamp(timestamp), c="black", linewidth=1.5, linestyle="--")

    def create_plot(self, data, filename, start, end):
        fig = plt.figure(figsize=(17, 12))
        gs = gridspec.GridSpec(6, 1, height_ratios=[4, 3, 1, 1, 1, 1])

        interval = 5  # TODO: duration (in min) / 20 ???

        lines = []
        line0, ax0 = self.create_first_line(
            data["current_participants"],
            "current_participants",
            "royalblue",
            gs,
            interval,
            start,
            end,
        )
        lines.append(line0)

        is_last = True if data["anomalies"].empty else False

        data_dict = [
            {
                "data": data["active_speakers"],
                "column": "active_speakers",
                "color": "mediumseagreen",
                "is_binary": False,
                "is_last": False,
            },
            {
                "data": data["presenters"],
                "column": "presenters",
                "color": "gold",
                "is_binary": False,
                "is_last": False,
            },
            {
                "data": data["streaming"],
                "column": "streaming",
                "color": "darkorange",
                "is_binary": True,
                "is_last": False,
            },
            {
                "data": data["recording"],
                "column": "recording",
                "color": "purple",
                "is_binary": True,
                "is_last": is_last,
            },
        ]

        axes = []

        for i, el in enumerate(data_dict):
            line, ax = self.add_line(
                el["data"],
                el["column"],
                el["color"],
                gs,
                i + 1,
                interval,
                ax0,
                start,
                end,
                el["is_binary"],
                el["is_last"],
            )
            lines.append(line)
            axes.append(ax)

        if not data["anomalies"].empty:
            self.add_anomalies(data["anomalies"], gs, 5, interval, ax0, start, end)

        ax0.legend(
            tuple(lines),
            (
                "number of participants",
                "number of active speakers",
                "number of presenters",
                "streaming",
                "recording",
            ),
            loc="upper left",
        )

        plt.subplots_adjust(hspace=0.0)

        plt.savefig(filename)

        plot = self.image_file_path_to_base64_string(filename)

        self.remove_plot(filename)

        return plot

    def create_first_line(
        self, data, column, color, gs, interval, start_time, end_time
    ):
        diff = (data.index[-1] - data.index[0]).total_seconds()
        if diff > 6 * 60:
            myFmt = mdates.DateFormatter("%H:%M")
        else:
            myFmt = mdates.DateFormatter("%H:%M:%S")
        ax0 = plt.subplot(gs[0])
        lc0 = self.create_intervals(data, column, color)
        line0 = ax0.add_collection(lc0)
        # ax0.xaxis.set_major_locator(mdates.MinuteLocator(interval=interval))
        ax0.xaxis.set_major_formatter(myFmt)
        ax0.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax0.xaxis_date()
        ax0.autoscale_view()
        ax0.grid(True)
        plt.setp(ax0.get_xticklabels(), visible=False)

        start, end = ax0.get_ylim()

        max_value = data[column].max()

        ax0.set_ylim(-0.5, max(1, max_value) + 0.5)
        ax0.yaxis.set_ticks(np.arange(0, max(1, max_value) + 1, 1))

        self.plot_line(start_time)
        self.plot_line(end_time)

        return line0, ax0

    def add_line(
        self,
        data,
        column,
        color,
        gs,
        index,
        interval,
        ax,
        start_time,
        end_time,
        is_binary=False,
        is_last=False,
    ):
        diff = (data.index[-1] - data.index[0]).total_seconds()
        if diff > 6 * 60:
            myFmt = mdates.DateFormatter("%H:%M")
        else:
            myFmt = mdates.DateFormatter("%H:%M:%S")
        ax1 = plt.subplot(gs[index], sharex=ax)
        lc1 = self.create_intervals(data, column, color)
        line1 = ax1.add_collection(lc1)
        ax1.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax1.xaxis.set_major_formatter(myFmt)
        ax1.xaxis_date()
        ax1.autoscale_view()
        ax1.grid(True)

        start, end = ax1.get_ylim()

        max_value = data[column].max()

        ax1.set_ylim(-0.2, max(1, max_value) + 0.2)
        ax1.yaxis.set_ticks(np.arange(0, max(1, max_value) + 1, 1))

        if is_binary:
            labels = [item.get_text() for item in ax1.get_yticklabels()]
            labels[0] = "OFF"
            labels[1] = "ON"
            ax1.set_yticklabels(labels)

        if not is_last:
            plt.setp(ax1.get_xticklabels(), visible=False)

        self.plot_line(start_time)
        self.plot_line(end_time)

        return line1, ax1

    def add_anomalies(self, anomalies, gs, index, interval, ax, start_time, end_time):
        ax1 = plt.subplot(gs[index], sharex=ax)
        myFmt = mdates.DateFormatter("%H:%M")
        # ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        ax1.xaxis.set_major_formatter(myFmt)
        ax1.grid(True)
        line1 = ax1.plot(
            anomalies.index, anomalies["ml_anomaly"], marker="x", c="r", linestyle=""
        )
        self.plot_line(start_time)
        self.plot_line(end_time)
        return line1, ax1


class MeetingDataProvider:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def filter_by_start_datetime(self, start_datetime):
        return self.data[self.data["start_datetime"] == start_datetime]


class CallInfoDataProvider(MeetingDataProvider):
    def __init__(self, name, dao):
        data = dao.get_call_info_data(name)
        MeetingDataProvider.__init__(self, name, data)

    def get_data_for_column(
        self, start_datetime, column, parameter=None, apply_func=None
    ):
        filtered = pd.DataFrame(
            self.filter_by_start_datetime(start_datetime)[
                ["datetime", column, "anomaly_reason"]
            ]
        )
        filtered["anomaly_reason"] = filtered["anomaly_reason"].apply(
            lambda x: x and parameter in x
        )
        filtered.index = filtered["datetime"]
        del filtered["datetime"]
        return filtered

    def get_anomalies(self, start_datetime):
        filtered = self.filter_by_start_datetime(start_datetime)[
            ["datetime", "ml_anomaly"]
        ]
        filtered.index = filtered["datetime"]
        del filtered["datetime"]
        return pd.DataFrame(filtered)


class CallsDataProvider(MeetingDataProvider):
    def __init__(self, name, dao):
        data = dao.get_calls_data(name)
        MeetingDataProvider.__init__(self, name, data)
        self.__init_dates()
        self.__init_meetings()

    def get_meeting_details(self, start_datetime):
        df = self.filter_by_start_datetime(start_datetime)
        if df.empty:
            raise NotFoundError
        meeting = df.iloc[0]
        return {
            "date": meeting["date"],
            "start_time": meeting["start_time"],
            "last_update_time": meeting["last_update_time"],
            "finished": meeting["finished"],
            "duration": self.__convert_seconds_to_time_format(meeting["duration"]),
        }

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
    def __init__(self, name, dao):
        data = dao.get_roster_data(name)
        MeetingDataProvider.__init__(self, name, data)

    def get_data_for_column(self, start_datetime, column, rename, parameter):
        filtered = pd.DataFrame(
            self.filter_by_start_datetime(start_datetime)[
                ["datetime", column, "anomaly_reason"]
            ]
        )
        filtered.index = filtered["datetime"]
        filtered.rename(columns={column: rename}, inplace=True)
        filtered["anomaly_reason"] = filtered["anomaly_reason"].apply(
            lambda x: x and parameter in x
        )
        del filtered["datetime"]
        return filtered

    def get_anomalies(self, start_datetime):
        filtered = self.filter_by_start_datetime(start_datetime)[
            ["datetime", "ml_anomaly"]
        ]
        filtered.index = filtered["datetime"]
        del filtered["datetime"]
        return pd.DataFrame(filtered)