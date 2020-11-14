from datetime import datetime


data_roster_template={
"datetime": type(str()),
"active_speaker": type(int()),
"week_day_number": type(int()),
"days" : type(list())
}

data_call_info_template={
"time_diff": {"min": type(int()), "max": type(int())},
"max_participants": type(int()),
"recording": type(bool()),
"streaming": type(bool()),
"datetime": type(str()),
"week_day_number": type(int()),
"days": [type(dict())]
}
data_roster={
"datetime": "2020-06-08 06:11:24.794+0000",
"call_id": "id121212",
"initial": 0,
"ringing": 1,
"connected": 10,
"onhold": 2,
"active_speaker": 10,
"presenter": 2,
"endpoint_recording": 3,
"hour": 10,
"week_day_number": 3,
"name": "name1"
}

data_call_info={
"adhoc": False,
"call_id": "id12312e",
"cospace": False,
"current_participants": 10,
"datetime": "2020-06-08 06:11:24.794+0000",
"forwarding": True,
"hour": 10,
"locked": False,
"lync_conferencing": True,
"max_participants": 20,
"mean_participants": 10.5,
"recording": False,
"streaming": True,
"time_diff": 20000,
"week_day_number": 4,
"name": "name"}


def check_roster(data_roster, admin_constraints):
    anomalies=[]
  #  if validate(data_roster admin_constraints)==[]:
    if True:
        for a in admin_constraints["criteria"]:
            if a["parameter"]=="active_speaker":
                if data_roster["active_speaker"]>a["conditions"]:
                    anomalies.append(("active_speaker", data_roster["active_speaker"]))
            if a["parameter"]=="days":
                if len(a["conditions"])==1:
                    min_hour = "00:00:00"
                    max_hour = "23:59:59"
                    curr_hour = datetime.strptime(data_roster["datetime"], '%Y-%m-%d %H:%M:%S.%f%z')
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
                        if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                            anomalies.append(("days", curr_hour))

                    else:
                        week_day_number = a["conditions"][0]["day"]
                        if data_roster["week_day_number"]==week_day_number:
                            if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (
                                    datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                                anomalies.append(("days", curr_hour))

                if len(a["conditions"]) > 1:
                    for b in a["conditions"]:
                        week_day_number = b["day"]
                        if data_roster["week_day_number"] == week_day_number:
                            min_hour = "00:00:00"
                            max_hour = "23:59:59"
                            curr_hour = datetime.strptime(data_roster["datetime"], '%Y-%m-%d %H:%M:%S.%f%z')
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

        return (1, anomalies) if len(anomalies)>0 else (0, [("", "")])

    else:
        return (-1, [])





def check_call_info(data_call_info, admin_constraints):
    anomalies=[]
  #  if validate(data_call_info, admin_constraints)==[]:
    if True:
        for a in admin_constraints["criteria"]:
            if a["parameter"]=="time_diff":
                mi=float("-inf")
                ma=float("inf")
                if "min" in a["conditions"]:
                    mi=a["conditions"]["min"]
                if "max" in a["conditions"]:
                    ma=a["conditions"]["max"]
                if data_call_info["time_diff"]>ma or data_call_info["time_diff"]<mi:
                    anomalies.append(("time_diff", data_call_info["time_diff"]))
            if a["parameter"]=="max_participants":
                if data_call_info["max_participants"]>a["conditions"]:
                    anomalies.append(("max_participants", data_call_info["max_participants"]))
            if a["parameter"]=="recording":
                if data_call_info["recording"] != a["conditions"]:
                    anomalies.append(("recording", data_call_info["recording"]))
            if a["parameter"]=="streaming":
                if data_call_info["streaming"] != a["conditions"]:
                    anomalies.append(("streaming", data_call_info["streaming"]))
            if a["parameter"]=="days":
                if len(a["conditions"])==1:
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
                        if (datetime.strptime(min_hour, '%H:%M:%S') > datetime.strptime(curr_hour, '%H:%M:%S')) or (datetime.strptime(max_hour, '%H:%M:%S') < datetime.strptime(curr_hour, '%H:%M:%S')):
                            anomalies.append(("days", curr_hour))

                    else:
                        week_day_number = a["conditions"][0]["day"]
                        if data_call_info["week_day_number"]==week_day_number:
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

        return (1, anomalies) if len(anomalies)>0 else (0, [("", "")])

    else:
        return (-1, [])




admin_constraints= {
    "type": "threshold",
    "criteria": [
        {
            "parameter": "time_diff",
            "conditions": {
                "min": 0,
                "max": 42
            }
        },
        {
            "parameter": "max_participants",
            "conditions": 25
        },
        {
            "parameter": "days",
            "conditions": [
                {
                    "day": 4,
                    "min_hour": "06:00",
                    "max_hour": "06:11"
                },
                {
                    "day": 1,
                    "min_hour": "05:00",
                    "max_hour": "20:30"
                }
            ]
        }
    ]
}

print(check_call_info(data_call_info, admin_constraints))