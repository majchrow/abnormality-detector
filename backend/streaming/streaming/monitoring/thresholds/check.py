from datetime import datetime


def check_roster(data_roster, criteria):
    anomalies = []
    for criterion in criteria:
        if criterion["parameter"] == "active_speaker":
            if data_roster["active_speaker"] > criterion["conditions"]:
                anomalies.append(("active_speaker", data_roster["active_speaker"]))
        if criterion["parameter"] == "days":
            if len(criterion["conditions"]) == 1:
                min_hour = "00:00:00"
                max_hour = "23:59:59"
                curr_hour = datetime.strptime(data_roster["datetime"], '%Y-%m-%d %H:%M:%S.%f%z')
                curr_hour = str(curr_hour.hour) + ":" + str(curr_hour.minute) + ":" + str(curr_hour.second)
                if "min_hour" in criterion["conditions"][0].keys():
                    min_hour = criterion["conditions"][0]["min_hour"]
                    if len(min_hour) == 5:
                        min_hour = min_hour + ":00"
                if "max_hour" in criterion["conditions"][0].keys():
                    max_hour = criterion["conditions"][0]["max_hour"]
                    if len(max_hour) == 5:
                        max_hour = max_hour + ":00"

                if "day" not in criterion["conditions"][0].keys():
                    if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                            datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                        anomalies.append(("days", curr_hour))

                else:
                    week_day_number = criterion["conditions"][0]["day"]
                    if data_roster["week_day_number"] == week_day_number:
                        if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                                datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                            anomalies.append(("days", curr_hour))

            if len(criterion["conditions"]) > 1:
                for b in criterion["conditions"]:
                    week_day_number = b["day"]
                    if data_roster["week_day_number"] == week_day_number:
                        min_hour = "00:00:00"
                        max_hour = "23:59:59"
                        curr_hour = datetime.strptime(data_roster["datetime"], '%Y-%m-%d %H:%M:%S.%f%z')
                        curr_hour = str(curr_hour.hour) + ":" + str(curr_hour.minute) + ":" + str(curr_hour.second)
                        if "min_hour" in criterion["conditions"][0].keys():
                            min_hour = criterion["conditions"][0]["min_hour"]
                            if len(min_hour) == 5:
                                min_hour = min_hour + ":00"
                        if "max_hour" in criterion["conditions"][0].keys():
                            max_hour = criterion["conditions"][0]["max_hour"]
                            if len(max_hour) == 5:
                                max_hour = max_hour + ":00"
                        if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                                datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                            anomalies.append(("days", curr_hour))

    return anomalies


def check_call_info(data_call_info, criteria):
    anomalies = []
    for a in criteria:
        if a["parameter"] == "time_diff":
            mi = float("-inf")
            ma = float("inf")
            if "min" in a["conditions"]:
                mi = a["conditions"]["min"]
            if "max" in a["conditions"]:
                ma = a["conditions"]["max"]
            if data_call_info["time_diff"] > ma or data_call_info["time_diff"] < mi:
                anomalies.append(("time_diff", data_call_info["time_diff"]))
        if a["parameter"] == "max_participants":
            if data_call_info["max_participants"] > a["conditions"]:
                anomalies.append(("max_participants", data_call_info["max_participants"]))
        if a["parameter"] == "recording":
            if data_call_info["recording"] != a["conditions"]:
                anomalies.append(("recording", data_call_info["recording"]))
        if a["parameter"] == "streaming":
            if data_call_info["streaming"] != a["conditions"]:
                anomalies.append(("streaming", data_call_info["streaming"]))
        if a["parameter"] == "days":
            if len(a["conditions"]) == 1:
                min_hour = "00:00:00"
                max_hour = "23:59:59"
                curr_hour = datetime.strptime(data_call_info["datetime"], '%Y-%m-%d %H:%M:%S.%f%z')
                curr_hour = str(curr_hour.hour) + ":" + str(curr_hour.minute) + ":" + str(curr_hour.second)
                if "min_hour" in a["conditions"][0].keys():
                    min_hour = a["conditions"][0]["min_hour"]
                    if len(min_hour) == 5:
                        min_hour = min_hour + ":00"
                if "max_hour" in a["conditions"][0].keys():
                    max_hour = a["conditions"][0]["max_hour"]
                    if len(max_hour) == 5:
                        max_hour = max_hour + ":00"

                if "day" not in a["conditions"][0].keys():
                    if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                            datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                        anomalies.append(("days", curr_hour))

                else:
                    week_day_number = a["conditions"][0]["day"]
                    if data_call_info["week_day_number"] == week_day_number:
                        if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                                datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                            anomalies.append(("days", curr_hour))

            if len(a["conditions"]) > 1:
                for b in a["conditions"]:
                    week_day_number = b["day"]
                    if data_call_info["week_day_number"] == week_day_number:
                        min_hour = "00:00:00"
                        max_hour = "23:59:59"
                        curr_hour = datetime.strptime(data_call_info["datetime"], '%Y-%m-%d %H:%M:%S.%f%z')
                        curr_hour = str(curr_hour.hour) + ":" + str(curr_hour.minute) + ":" + str(curr_hour.second)
                        if "min_hour" in a["conditions"][0].keys():
                            min_hour = a["conditions"][0]["min_hour"]
                            if len(min_hour) == 5:
                                min_hour = min_hour + ":00"
                        if "max_hour" in a["conditions"][0].keys():
                            max_hour = a["conditions"][0]["max_hour"]
                            if len(max_hour) == 5:
                                max_hour = max_hour + ":00"
                        if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                                datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                            anomalies.append(("days", curr_hour))

    return anomalies
