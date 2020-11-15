from datetime import datetime

data_roster_template={
"datetime": type(str()),
"active_speaker": type(int()),
"week_day_number": type(int()),
"days": [type(dict())]
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


def valid_time(date_text):
    tries=0
    if len(date_text)==8:
        try:
            datetime.strptime(date_text, '%H:%M:%S')
            tries=1
        except ValueError:
            tries=0
    elif len(date_text)==5:
        try:
            datetime.strptime(date_text, '%H:%M')
            tries=1
        except ValueError:
            tries=0
    else:
        return False
    return True if tries==1 else False


def type_of(type_class):
    return str(type_class).split(" ")[1][1:-2]


def validate_elem_of_days_list(elem, data_template):
    wrong_constraints=[]
    if type(elem) != data_template["days"][0]:
        wrong_constraints.append({"parameter": "days", "type": "value",
                                  "message": "Wrong type value: " + str(elem) + " in \"days\" ---> " + type_of(type_class=
                                      type(elem)) + " is not " + type_of(type_class=data_template["days"][0])})
    else:
        if len(elem)>0:
            wrong_flag = False
            for x in elem.keys():
                if x not in ["min_hour", "max_hour", "day"]:
                    wrong_flag = True
                    wrong_constraints.append({"parameter": "days", "type": "value", "message": "Wrong value: " + str(
                        x) + " in \"days\" ---> right value is:  {\"day\": x, \"min_hour\": y, \"max_hour\": z} with min_hour, max_hour optional"})
            if not wrong_flag:
                for y in elem.keys():
                    if y != "day":
                        if not valid_time(date_text=elem[y]):
                            wrong_constraints.append({"parameter": "days", "type": "value",
                                                      "message": "Wrong type value: " + str(
                                                          y) + " in \"days\" ---> " + str(
                                                          elem[y]) + " is neither \"%H:%M:%S\" nor \"%H:%M\" "})
                    else:
                        if type(elem["day"]) != data_template["week_day_number"]:
                            wrong_constraints.append({"parameter": "days", "type": "value",
                                                      "message": "Wrong type value: " + str(
                                                          elem["day"]) + " in \"days\" ---> " + type_of(type_class=
                                                          type(elem["day"])) + " is not " + type_of(type_class=
                                                          data_template["week_day_number"])})
        else:
            wrong_constraints.append({"parameter": "days", "type": "value",
                                      "message": "Wrong value: " + str(elem) + " in \"days\" ---> is empty"})
    return wrong_constraints


def days_form(cond_list, data_template):
    wrong_constraints=[]
    day_list=[]
    if len(cond_list)==0:
        wrong_constraints.append({"parameter": "days", "type": "value",
                                  "message": "Wrong type value: \"days\" is empty"})

    if len(cond_list)==1:
        l=validate_elem_of_days_list(elem=cond_list[0], data_template=data_template)
        if l:
           wrong_constraints=wrong_constraints+l

    else:
        for e in cond_list:
            if "day" in e.keys():
                day_list.append(e["day"])
                l = validate_elem_of_days_list(elem=e, data_template=data_template)
                if l:
                    wrong_constraints = wrong_constraints + l
            else:
                wrong_constraints.append({"parameter": "days", "type": "value", "message": "Wrong value: " + str(
                    e) + " in \"days\" ---> right value is:  {\"day\": x, \"min_hour\": y, \"max_hour\": z} with min_hour, max_hour optional, day is required"})

    if len(day_list)!= len(set(day_list)):
        wrong_constraints.append({"parameter": "days", "type": "value", "message": "Wrong value: days are duplicated"})

    return wrong_constraints


def validate(data_template, admin_constraints, template_name):
    wrong_constraints=[]
    keys_template = list(data_template.keys())

    ac= admin_constraints["criteria"]
    for e in ac:
        p=e["parameter"]
        if template_name=="call_info" and p=="time_diff":
            c = e["conditions"]
            if type(c)!=type(data_template[p]):
                wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong type value: "+str(c)+" ---> "+type_of(type_class=type(c))+" is not "+type_of(type_class=type(data_template[p]))})
            else:
                mi=-1
                ma=-1
                right_param=[]
                min_max = list(c.keys())
                if len(min_max)==0:
                    wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: "+str(c)+" ---> "+str(c)+" is empty"})
                elif len(min_max)>2:
                    wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: "+str(c)+" ---> "+" too many params, right value is:  {\"min\": x, \"max\": y}"} )
                elif len(min_max)==1:
                    if min_max[0]=="min":
                        mi=c["min"]
                        right_param.append("min")
                    elif min_max[0]=="max":
                        ma=c["max"]
                        right_param.append("max")
                    else:
                        wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: " + str(c) + " ---> " + " wrong names of params, right value is:  {\"min\": x, \"max\": y}"})
                else:
                    if (("max" in min_max) and ("min" in min_max)):
                        mi=c["min"]
                        ma=c["max"]
                        right_param.append("min")
                        right_param.append("max")
                    else:
                        wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong value: " + str(c) + " ---> " + " wrong names of params, right value is:  {\"min\": x, \"max\": y}"})
                if len(right_param)==2:
                    OK=0
                    for mima in right_param:
                        if type(c[mima]) != data_template["time_diff"][mima]:
                            wrong_constraints.append({"parameter": p, "type": "value",
                                                      "message": "Wrong type value: " +mima+" in "+ str(c) + " ---> " + type_of(type_class=
                                                          type(c[mima])) + " is not " + type_of(type_class=data_template["time_diff"][mima])})
                        else:
                            OK=OK+1
                    if OK==2:
                        if mi>=ma:
                            wrong_constraints.append({"parameter": p, "type": "value",
                                                      "message": "Wrong values: \"min\" = "+str(mi)+", \"max\" = "+str(ma) + " ---> min <= max"})
                        for mima in right_param:
                            if c[mima]<0:
                                wrong_constraints.append({"parameter": p, "type": "value",
                                                          "message": "Wrong value: \""+mima+"\" = "+str(c[mima]) + " ---> "+mima+" >= 0"})
                if len(right_param)==1:
                    if c[right_param[0]] < 0:
                        wrong_constraints.append({"parameter": p, "type": "value",
                                                  "message": "Wrong value: \"" + right_param[0] + "\" = " + str(
                                                      c[right_param[0]]) + " ---> " + right_param[0] + " >= 0"})

        elif p=="days":
            c=e["conditions"]
            if type(c)!=type(data_template[p]):
                wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong type value: "+str(c)+" ---> "+type_of(type_class=type(c))+" is not "+ type_of(type_class=type(data_template[p]))})
            else:
                l=days_form(cond_list=c, data_template=data_template)
                if l:
                    wrong_constraints=wrong_constraints+l


        elif p in keys_template:
            c=e["conditions"]
            if type(c)!=data_template[p]:
                wrong_constraints.append({"parameter": p, "type": "value", "message": "Wrong type value: "+str(c)+" ---> "+type_of(type_class=type(c))+" is not "+ type_of(type_class=data_template[p])})



        else:
            wrong_constraints.append({"parameter": p, "type": "parameter", "message": "Wrong parameter name: " + str(p) + " ---> \"" + str(p) +"\" not exist in "+template_name})

    if wrong_constraints:
        raise ValueError(wrong_constraints)
    return True


admin_constraints= {
    "type": "threshold",
    "criteria": [
        {
            "parameter": "time_diff",
            "conditions": {
                "min": 0,
                "max": 42,
            }
        },
        {
            "parameter": "max_participants",
            "conditions": 2
        },

        {
            "parameter": "days",
            "conditions": [
                {
                    "day": 2,
                    "min_hour": "06:00",
                    "max_hour": "06:11",
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

print(validate(data_template=data_call_info_template, admin_constraints=admin_constraints, template_name="call_info"))
# print(validate(data_template=data_roster_template, admin_constraints=admin_constraints, template_name="roster"))
