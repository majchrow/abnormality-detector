from datetime import datetime


# TODO:
#  - this duplication sucks!
#  - we need validation for whether "parameter" & "conditions" are present at all
param_types = {
    "time_diff": {"min": int, "max": int},
    "max_participants": int,
    "recording": bool,
    "streaming": bool,
    "active_speaker": int,
    "datetime": str,
    "week_day_number": int,
    "days": [dict]
}


def valid_time(date_text):
    try:
        if len(date_text) == 8:
            fmt = '%H:%M:%S'
        elif len(date_text) == 5:
            fmt = '%H:%M'
        else:
            return False
        datetime.strptime(date_text, fmt)
        return True
    except ValueError:
        return False


def type_of(type_class):
    return str(type_class).split(" ")[1][1:-2]


def validate_elem_of_days_list(elem):
    wrong_constraints = []
    if type(elem) != param_types["days"][0]:
        msg = "Wrong type value: {} in \"days\" ---> {}  is not {}".format(
            str(elem), type_of(type_class=type(elem)), type_of(type_class=param_types["days"][0])
        )
        wrong_constraints.append({"parameter": "days", "type": "value", "message": msg})
    else:
        if len(elem) > 0:
            wrong_flag = False
            for x in elem.keys():
                if x not in ["min_hour", "max_hour", "day"]:
                    wrong_flag = True
                    msg = ('Wrong value: {} in "days" ---> right value is: '
                           '{"day": x, "min_hour": y, "max_hour": z} with '
                           'min_hour, max_hour optional').format(str(x))
                    wrong_constraints.append({"parameter": "days", "type": "value", "message": msg})
            if not wrong_flag:
                for y in elem.keys():
                    if y != "day":
                        if not valid_time(date_text=elem[y]):
                            msg = ('Wrong type value: {} in "days" ---> '
                                   '{} is neither "%H:%M:%S" nor "%H:%M"').format(y, elem[y])
                            wrong_constraints.append({"parameter": "days", "type": "value", "message": msg})
                    else:
                        if type(elem["day"]) != param_types["week_day_number"]:
                            msg = 'Wrong type value: {} in "days" ---> {} is not {}'.format(
                                elem["day"], type_of(type_class=type(elem["day"])),
                                type_of(type_class=param_types["week_day_number"])
                            )
                            wrong_constraints.append({"parameter": "days", "type": "value", "message": msg})

                        if isinstance(elem["day"], int):
                            if elem["day"] < 1 or elem["day"] > 7:
                                wrong_constraints.append({"parameter": "days", "type": "value",
                                                          "message": "Wrong type value: " + str(
                                                              elem["day"]) + " ---> " + str(
                                                              elem["day"]) + " is not from 1 to 7"})
        else:
            wrong_constraints.append({"parameter": "days", "type": "value",
                                      "message": "Wrong value: {}  in \"days\" ---> is empty".format(str(elem))})
    return wrong_constraints


def days_form(cond_list):
    wrong_constraints = []
    day_list = []
    if len(cond_list) == 0:
        wrong_constraints.append({"parameter": "days", "type": "value",
                                  "message": "Wrong type value: \"days\" is empty"})

    if len(cond_list) == 1:
        wrong_constraints.extend(validate_elem_of_days_list(elem=cond_list[0]))

    else:
        for e in cond_list:
            if "day" in e.keys():
                day_list.append(e["day"])
                wrong_constraints.extend(validate_elem_of_days_list(elem=e))
            else:
                wrong_constraints.append({
                    "parameter": "days",
                    "type": "value",
                    "message": f"Wrong value: {e} in \"days\" ---> right value is: "
                               " {\"day\": x, \"min_hour\": y, \"max_hour\": z} with "
                               "min_hour, max_hour optional, day is required"
                })

    if len(day_list) != len(set(day_list)):
        wrong_constraints.append({"parameter": "days", "type": "value", "message": "Wrong value: days are duplicated"})

    return wrong_constraints


def validate(criteria):
    wrong_constraints = []
    params = list(param_types.keys())

    for e in criteria:
        p = e["parameter"]
        if p == "time_diff":
            c = e["conditions"]
            if not isinstance(c, type(param_types[p])):
                wrong_constraints.append({"parameter": p, "type": "value",
                                          "message": f"Wrong type value: {c} ---> " + type_of(
                                              type_class=type(c)) + " is not " + type_of(
                                              type_class=type(param_types[p]))})
            else:
                mi = -1
                ma = -1
                right_param = []
                min_max = list(c.keys())
                if len(min_max) == 0:
                    wrong_constraints.append({"parameter": p, "type": "value",
                                              "message": "Wrong value: " + str(c) + " ---> " + str(c) + " is empty"})
                elif len(min_max) > 2:
                    wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: " + str(
                        c) + " ---> " + " too many params, right value is:  {\"min\": x, \"max\": y}"})
                elif len(min_max) == 1:
                    if min_max[0] == "min":
                        mi = c["min"]
                        right_param.append("min")
                    elif min_max[0] == "max":
                        ma = c["max"]
                        right_param.append("max")
                    else:
                        wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: " + str(
                            c) + " ---> " + " wrong names of params, right value is:  {\"min\": x, \"max\": y}"})
                else:
                    if "max" in min_max and "min" in min_max:
                        mi = c["min"]
                        ma = c["max"]
                        right_param.append("min")
                        right_param.append("max")
                    else:
                        wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: " + str(
                            c) + " ---> " + " wrong names of params, right value is:  {\"min\": x, \"max\": y}"})
                if len(right_param) == 2:
                    OK = 0
                    for mima in right_param:
                        if type(c[mima]) != param_types["time_diff"][mima]:
                            wrong_constraints.append({"parameter": p, "type": "value",
                                                      "message": "Wrong type value: " + mima + " in " + str(
                                                          c) + " ---> " + type_of(type_class=
                                                                                  type(c[mima])) + " is not " + type_of(
                                                          type_class=param_types["time_diff"][mima])})
                        else:
                            OK = OK + 1
                    if OK == 2:
                        if mi >= ma:
                            wrong_constraints.append({"parameter": p, "type": "value",
                                                      "message": "Wrong values: \"min\" = " + str(
                                                          mi) + ", \"max\" = " + str(ma) + " ---> min <= max"})
                        for mima in right_param:
                            if c[mima] < 0:
                                wrong_constraints.append({"parameter": p, "type": "value",
                                                          "message": "Wrong value: \"" + mima + "\" = " + str(
                                                              c[mima]) + " ---> " + mima + " >= 0"})
                if len(right_param) == 1:
                    if c[right_param[0]] < 0:
                        wrong_constraints.append({"parameter": p, "type": "value",
                                                  "message": "Wrong value: \"" + right_param[0] + "\" = " + str(
                                                      c[right_param[0]]) + " ---> " + right_param[0] + " >= 0"})
        elif p == "days":
            c = e["conditions"]
            if type(c) != type(param_types[p]):
                wrong_constraints.append({"parameter": p, "type": "value",
                                          "message": "Wrong type value: " + str(c) + " ---> " + type_of(
                                              type_class=type(c)) + " is not " + type_of(
                                              type_class=type(param_types[p]))})
            else:
                wrong_constraints.extend(days_form(cond_list=c))
        elif p in params:
            c = e["conditions"]
            if type(c) != param_types[p]:
                wrong_constraints.append({"parameter": p, "type": "value",
                                          "message": "Wrong type value: " + str(c) + " ---> " + type_of(
                                              type_class=type(c)) + " is not " + type_of(type_class=param_types[p])})
            if isinstance(c, int):
                if c < 0:
                    wrong_constraints.append({"parameter": p, "type": "value",
                                              "message": "Wrong type value: " + str(c) + " ---> " + str(c) + " <0"})
        else:
            wrong_constraints.append({"parameter": p, "type": "parameter",
                                      "message": "Wrong parameter name: " + str(p) + " ---> \"" + str(
                                          p) + "\" not handled"})

    if wrong_constraints:
        raise ValueError(wrong_constraints)
    return True
