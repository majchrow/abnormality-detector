from pyspark.sql.types import *
import operator
from datetime import datetime
from pyspark.sql.functions import *
import math

class PreprocessorHelper:
    def __init__(self, spark):
        self.datetime_pattern = "%Y-%m-%dT%H:%M:%S.%f"
        self.concat_udf = udf(
            lambda cols: "".join([x if x is not None else "*" for x in cols]),
            StringType(),
        )
        self.get_name_udf = udf(self.get_name, StringType())
        self.get_last_date_udf = udf(self.get_last_date, TimestampType())
        udf_func_dict = {
            "get_name_udf": self.get_name_udf,
            "get_last_date_udf": self.get_last_date_udf,
            "concat_udf": self.concat_udf
        }
        for udf_func in udf_func_dict:
            spark.udf.register(udf_func, udf_func_dict[udf_func])

    @staticmethod
    def get_last_nonempty_value(values):
        nonempty_values = [i for i in values if i and not (type(i) == float and math.isnan(i))]
        return nonempty_values[-1] if nonempty_values else None

    @staticmethod
    def get_name(names):
        return PreprocessorHelper.get_last_nonempty_value(names)

    @staticmethod
    def get_last_date(dates):
        datetime_pattern = "%Y-%m-%dT%H:%M:%S.%f"
        date = datetime.strptime(dates[-1], datetime_pattern)
        return date


class CallInfoPreprocessorHelper(PreprocessorHelper):
    def __init__(self, spark):
        PreprocessorHelper.__init__(self, spark)
        self.get_time_diff_udf = udf(self.__get_time_diff, LongType())
        self.get_if_active_udf = udf(self.__get_if_active, BooleanType())
        self.get_if_locked_udf = udf(self.__get_if_locked, BooleanType())
        self.get_if_adhoc_udf = udf(self.__get_if_adhoc, BooleanType())
        self.get_if_lync_udf = udf(self.__get_if_lync, BooleanType())
        self.get_if_cospace_udf = udf(self.__get_if_cospace, BooleanType())
        self.get_if_forwarding_udf = udf(self.__get_if_forwarding, BooleanType())
        self.get_max_udf = udf(self.__get_max, IntegerType())
        self.get_mean_udf = udf(self.__get_mean, DoubleType())
        udf_func_dict = {
            "get_time_diff_udf": self.get_time_diff_udf,
            "get_if_active_udf": self.get_if_active_udf,
            "get_if_locked_udf": self.get_if_locked_udf,
            "get_if_adhoc_udf": self.get_if_adhoc_udf,
            "get_if_lync_udf": self.get_if_lync_udf,
            "get_if_forwarding_udf": self.get_if_forwarding_udf,
            "get_if_cospace_udf": self.get_if_cospace_udf,
            "get_max_udf": self.get_max_udf,
            "get_mean_udf": self.get_mean_udf
        }
        for udf_func in udf_func_dict:
            spark.udf.register(udf_func, udf_func_dict[udf_func])

    @staticmethod
    def __get_time_diff(dates):
        datetime_pattern = "%Y-%m-%dT%H:%M:%S.%f"
        start_date = datetime.strptime(dates[0], datetime_pattern)
        end_date = datetime.strptime(dates[-1], datetime_pattern)
        return int((end_date - start_date).total_seconds())

    @staticmethod
    def __get_if_active(values):
        state = PreprocessorHelper.get_last_nonempty_value(values)
        return state == "active"

    @staticmethod
    def __get_if_locked(values):
        state = PreprocessorHelper.get_last_nonempty_value(values)
        return state == "locked"

    @staticmethod
    def __get_if_type(current_type, expected_type):
        return current_type == expected_type

    @staticmethod
    def __get_if_adhoc(real_type):
        return CallInfoPreprocessorHelper.__get_if_type(real_type, "adHoc")

    @staticmethod
    def __get_if_lync(real_type):
        return CallInfoPreprocessorHelper.__get_if_type(real_type, "lyncConferencing")

    @staticmethod
    def __get_if_forwarding(real_type):
        return CallInfoPreprocessorHelper.__get_if_type(real_type, "forwarding")

    @staticmethod
    def __get_if_cospace(real_type):
        return CallInfoPreprocessorHelper.__get_if_type(real_type, "coSpace")

    @staticmethod
    def __get_max(values):
        filtered = CallInfoPreprocessorHelper.__get_nonempty_values(values)
        max_value = 0
        for value in filtered:
            if value > max_value:
                max_value = value
        return int(max_value)

    @staticmethod
    def __get_mean(values):
        filtered = CallInfoPreprocessorHelper.__get_nonempty_values(values)
        total = 0
        for value in filtered:
            total = total + value
        size = len(values)
        return float(total/size) if size else 0.0
    
    @staticmethod
    def __get_nonempty_values(values):
        return [value for value in values if value and not (type(value) == float and math.isnan(value))]


class RosterPreprocessorHelper(PreprocessorHelper):
    class CallStats:
        call_stats_schema = StructType(
            [
                StructField("initial", IntegerType(), False),
                StructField("connected", IntegerType(), False),
                StructField("onhold", IntegerType(), False),
                StructField("ringing", IntegerType(), False),
                StructField("presenter", IntegerType(), False),
                StructField("active_speaker", IntegerType(), False),
                StructField("endpoint_recording", IntegerType(), False),
                StructField("datetime", TimestampType()),
            ]
        )

        def __init__(
            self,
            initial,
            connected,
            onhold,
            ringing,
            presenter,
            active_speaker,
            endpoint_recording,
            date,
        ):
            self.initial = initial
            self.connected = connected
            self.onhold = onhold
            self.ringing = ringing
            self.presenter = presenter
            self.active_speaker = active_speaker
            self.endpoint_recording = endpoint_recording
            self.datetime = date

    def __init__(self, spark):
        PreprocessorHelper.__init__(self, spark)
        self.get_call_stats_udf = udf(
            self.__get_call_stats, self.CallStats.call_stats_schema
        )
        spark.udf.register("get_call_stats_udf", self.get_call_stats_udf)

    @staticmethod
    def __get_call_stats(struct_array):
        datetime_pattern = "%Y-%m-%dT%H:%M:%S.%f"
        struct_array.sort(key=operator.itemgetter("date"))
        date = datetime.strptime(
            [struct["date"] for struct in struct_array][-1], datetime_pattern
        )

        removed = [
            struct["participant"]
            for struct in struct_array
            if struct["updateType"] == "remove"
        ]
        current = [
            struct for struct in struct_array if struct["participant"] not in removed
        ]
        participant_dict = dict()

        for struct in current:
            participant = struct["participant"]
            if participant in participant_dict:
                participant_dict[participant].append(struct)
            else:
                participant_dict[participant] = [struct]

        grouped = list(participant_dict.values())

        fields = ["state", "presenter", "activeSpeaker", "endpointRecording"]
        final = {field: list() for field in fields}
        for events in grouped:
            for field in fields:
                final[field].append(RosterPreprocessorHelper.__get_current_value(events, field))

        final["initial"] = 0
        final["connected"] = 0
        final["onhold"] = 0
        final["ringing"] = 0

        for state in final["state"]:
            final[state] = final[state] + 1

        final["presenter_sum"] = RosterPreprocessorHelper.__count_true_values(final["presenter"])
        final["activeSpeaker_sum"] = RosterPreprocessorHelper.__count_true_values(final["activeSpeaker"])
        final["endpointRecording_sum"] = RosterPreprocessorHelper.__count_true_values(
            final["endpointRecording"]
        )

        return RosterPreprocessorHelper.CallStats(
            final["initial"],
            final["connected"],
            final["onhold"],
            final["ringing"],
            final["presenter_sum"],
            final["activeSpeaker_sum"],
            final["endpointRecording_sum"],
            date,
        )

    @staticmethod
    def __get_current_value(events, field):
        values = [event[field] for event in events]
        return RosterPreprocessorHelper.get_last_nonempty_value(values)

    @staticmethod
    def __count_true_values(values):
        return len([value for value in values if value and value is not None])


class CallsPreprocessorHelper(PreprocessorHelper):
    def __init__(self, spark):
        PreprocessorHelper.__init__(self, spark)
        self.get_if_finished_udf = udf(self.__get_if_finished, BooleanType())
        udf_func_dict = {
            "get_if_finished_udf": self.get_if_finished_udf
        }
        for udf_func in udf_func_dict:
            spark.udf.register(udf_func, udf_func_dict[udf_func])

    @staticmethod
    def __get_if_finished(values):
        return "remove" in values
