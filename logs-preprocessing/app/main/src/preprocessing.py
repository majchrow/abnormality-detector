import pyspark.sql.functions as func
from utils import CallInfoPreprocessorHelper, RosterPreprocessorHelper
from pyspark.sql.types import *


class Preprocessor:
    def __init__(self, spark, topic, filepath, kafka, table, helper):
        self.spark = spark
        self.keyspace = "engineering"
        self.table = table
        schema = spark.read.json(filepath).schema
        input_stream = self.get_input_stream_for_topic(topic, kafka)
        self.df = self.__do_basic_preprocessing(input_stream, schema)
        self.helper = helper

    @staticmethod
    def __do_basic_preprocessing(input_stream, schema):
        return input_stream.withColumn("event", func.from_json("value", schema)).select(
            "event.date", "event.call", "event.message"
        )

    def create_output_stream(self):
        return (
            self.prepare_final_df()
            .writeStream.outputMode("complete")
            .foreachBatch(self.__write_to_cassandra)
        )

    def prepare_final_df(self):
        pass

    def __do_post_preprocessing(self, preprocessed):
        self.df = (
            preprocessed.withColumn(
                "id", self.helper.concat_udf(func.array("call_id", "datetime"))
            )
            .withColumn("hour", func.hour("datetime"))
            .withColumn(
                "week_day_number", func.date_format("datetime", "u").cast(IntegerType())
            )
        )

    def __write_to_cassandra(self, write_df, epoch_id):
        write_df.write.format("org.apache.spark.sql.cassandra").options(
            table=self.table, keyspace=self.keyspace
        ).mode("append").save()

    def get_input_stream_for_topic(self, topic, kafka):
        return (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", kafka)
            .option("subscribe", topic)
            .load()
            .selectExpr("CAST(value AS STRING)")
        )


class CallInfoPreprocessor(Preprocessor):
    def __init__(self, spark, kafka, filepath):
        Preprocessor.__init__(
            self,
            spark=spark,
            topic="callInfoUpdate",
            filepath=filepath,
            kafka=kafka,
            table="call_info_update",
            helper=CallInfoPreprocessorHelper(spark),
        )

    def prepare_final_df(self):
        self.df = self.df.select("date", "call", "message.callInfo")
        info = self.df.callInfo

        selected = self.df.select(
            "call",
            info.callType.alias("callType"),
            info.distributedInstances.alias("distributedInstances"),
            info.endpointRecording.alias("endpointRecording"),
            info.lockState.alias("lockState"),
            info.participants.alias("participants"),
            info.recording.alias("recording"),
            info.streaming.alias("streaming"),
            info.joinAudioMuteOverride.alias("joinAudioMute"),
            "date",
        )

        grouped = selected.groupBy("call").agg(
            func.sort_array(func.collect_list("date")).alias("date_array"),
            func.collect_list("recording").alias("recording_array"),
            func.collect_list("streaming").alias("streaming_array"),
            func.collect_list("lockState").alias("lockState_array"),
            func.reverse(func.collect_list("callType")).getItem(0).alias("callType"),
            func.reverse(func.collect_list("participants"))
            .getItem(0)
            .cast(LongType())
            .alias("current_participants"),
            func.max("participants").cast(LongType()).alias("max_participants"),
            func.mean("participants").alias("mean_participants"),
        )

        preprocessed = (
            grouped.withColumn("datetime", self.helper.get_last_date_udf("date_array"))
            .withColumn("time_diff", self.helper.find_diff_udf("date_array"))
            .withColumn("call_id", "call")
            .withColumn("recording", self.helper.get_if_active_udf("recording_array"))
            .withColumn("streaming", self.helper.get_if_active_udf("streaming_array"))
            .withColumn("locked", self.helper.get_if_locked_udf("lockState_array"))
            .withColumn("cospace", self.helper.get_if_cospace_udf("callType"))
            .withColumn("adhoc", self.helper.get_if_adhoc_udf("callType"))
            .withColumn("lync_conferencing", self.helper.get_if_lync_udf("callType"))
            .withColumn("forwarding", self.helper.get_if_forwarding_udf("callType"))
            .select(
                "datetime",
                "time_diff",
                "call_id",
                "recording",
                "streaming",
                "locked",
                "cospace",
                "adhoc",
                "lync_conferencing",
                "forwarding",
                "current_participants",
                "mean_participants",
                "max_participants",
            )
        )

        self.__do_post_preprocessing(preprocessed)


class RosterPreprocessor(Preprocessor):
    def __init__(self, spark, kafka, filepath):
        Preprocessor.__init__(
            self,
            spark=spark,
            topic="rosterUpdate",
            filepath=filepath,
            kafka=kafka,
            table="roster_update",
            helper=RosterPreprocessorHelper(spark),
        )

    def prepare_final_df(self):
        self.df = self.df.select("date", "call", func.explode("message.updates"))
        update_col = self.df.col

        selected = self.df.select(
            "call",
            "date",
            update_col.activeSpeaker.alias("activeSpeaker"),
            update_col.canMove.alias("canMove"),
            update_col.direction.alias("direction"),
            update_col.endpointRecording.alias("endpointRecording"),
            update_col.layout.alias("layout"),
            update_col.movedParticipant.alias("movedParticipant"),
            update_col.movedParticipantCallBridge.alias("movedParticipantCallBridge"),
            update_col.participant.alias("participant"),
            update_col.presenter.alias("presenter"),
            update_col.state.alias("state"),
            update_col.updateType.alias("updateType"),
            update_col.uri.alias("uri"),
        )

        grouped = (
            selected.withColumn(
                "struct",
                func.struct(
                    "state",
                    "activeSpeaker",
                    "presenter",
                    "endpointRecording",
                    "participant",
                    "date",
                    "updateType",
                ),
            )
            .groupBy("call")
            .agg(func.collect_list("struct").alias("struct_array"))
        )

        preprocessed = grouped.withColumn(
            "call_stats", self.helper.get_call_stats_udf("struct_array")
        )
        stats = preprocessed.call_stats

        final = preprocessed.select(stats.initial.alias("initial"),
                          stats.connected.alias("connected"),
                          stats.onhold.alias("onhold"),
                          stats.ringing.alias("ringing"),
                          stats.presenter.alias("presenter"),
                          stats.active_speaker.alias("active_speaker"),
                          stats.endpoint_recording.alias("endpoint_recording"),
                          stats.datetime.alias("datetime"),
                          stats.call.alias("call_id"))

        self.__do_post_preprocessing(final)
