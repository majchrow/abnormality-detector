import pyspark.sql.functions as func
from utils import RosterPreprocessorHelper, CallInfoPreprocessorHelper
from pyspark.sql.types import *
import os


class Preprocessor:
    def __init__(self, spark, topic, filepath, kafka, table, helper):
        self.spark = spark
        self.keyspace = os.environ["KEYSPACE"]
        self.table = table
        self.kafka = kafka
        self.write_topic = "preprocessed_" + topic
        schema = spark.read.json(filepath).schema
        input_stream = self.__get_input_stream_for_topic(topic, kafka)
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
            .foreachBatch(self.write_data)
        )

    def prepare_final_df(self):
        pass

    def do_post_preprocessing(self, preprocessed):
        return preprocessed.withColumn("hour", func.hour("datetime")).withColumn(
            "week_day_number", func.date_format("datetime", "u").cast(IntegerType())
        )

    def write_data(self, write_df, epoch_id):
        write_df.persist()
        self.__write_to_cassandra(write_df)
        self.__write_to_kafka(write_df)
        write_df.unpersist()

    def __write_to_cassandra(self, write_df):
        write_df.write.format("org.apache.spark.sql.cassandra").options(
            table=self.table, keyspace=self.keyspace
        ).mode("append").save()

    def __write_to_kafka(self, write_df):
        self.prepare_for_kafka(write_df).write.format("kafka").option(
            "kafka.bootstrap.servers", self.kafka
        ).option("topic", self.write_topic).save()

    def __get_input_stream_for_topic(self, topic, kafka):
        return (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", kafka)
            .option("subscribe", topic)
            .load()
            .selectExpr("CAST(value AS STRING)")
        )

    def prepare_for_kafka(self, df):
        pass

class CallInfoPreprocessor(Preprocessor):
    def __init__(self, spark, kafka, filepath):
        Preprocessor.__init__(
            self,
            spark=spark,
            topic="callInfoUpdate",
            filepath=filepath,
            kafka=kafka,
            table=os.environ["TABLE"],
            helper=CallInfoPreprocessorHelper(spark),
        )

    def prepare_for_kafka(self, df):
        return df.select(func.to_json(func.struct("datetime",
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
                "week_day_number",
                "hour")).alias("value"))

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
            .cast(IntegerType())
            .alias("current_participants"),
            func.collect_list("participants").alias("participant_array"),
        )

        grouped.printSchema()

        preprocessed = (
            grouped.withColumn(
                "datetime", self.helper.get_last_date_udf(grouped.date_array)
            )
            .withColumn("time_diff", self.helper.get_time_diff_udf(grouped.date_array))
            .withColumn("call_id", grouped.call)
            .withColumn(
                "recording", self.helper.get_if_active_udf(grouped.recording_array)
            )
            .withColumn(
                "streaming", self.helper.get_if_active_udf(grouped.streaming_array)
            )
            .withColumn(
                "locked", self.helper.get_if_locked_udf(grouped.lockState_array)
            )
            .withColumn("cospace", self.helper.get_if_cospace_udf(grouped.callType))
            .withColumn("adhoc", self.helper.get_if_adhoc_udf(grouped.callType))
            .withColumn(
                "lync_conferencing", self.helper.get_if_lync_udf(grouped.callType)
            )
            .withColumn(
                "forwarding", self.helper.get_if_forwarding_udf(grouped.callType)
            )
            .withColumn(
                "max_participants", self.helper.get_max_udf(grouped.participant_array)
            )
            .withColumn(
                "mean_participants", self.helper.get_mean_udf(grouped.participant_array)
            )
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

        return self.do_post_preprocessing(preprocessed)


class RosterPreprocessor(Preprocessor):
    def __init__(self, spark, kafka, filepath):
        Preprocessor.__init__(
            self,
            spark=spark,
            topic="rosterUpdate",
            filepath=filepath,
            kafka=kafka,
            table=os.environ["TABLE"],
            helper=RosterPreprocessorHelper(spark),
        )

    def prepare_for_kafka(self, df):
        return df.select(func.to_json(func.struct("initial",
            "connected",
            "onhold",
            "ringing",
            "presenter",
            "active_speaker",
            "endpoint_recording",
            "datetime",
            "call_id",
            "week_day_number",
            "hour")).alias("value"))

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
            "call_stats", self.helper.get_call_stats_udf(grouped.struct_array)
        )
        stats = preprocessed.call_stats

        final = preprocessed.select(
            stats.initial.alias("initial"),
            stats.connected.alias("connected"),
            stats.onhold.alias("onhold"),
            stats.ringing.alias("ringing"),
            stats.presenter.alias("presenter"),
            stats.active_speaker.alias("active_speaker"),
            stats.endpoint_recording.alias("endpoint_recording"),
            stats.datetime.alias("datetime"),
            preprocessed.call.alias("call_id"),
        )

        return self.do_post_preprocessing(final)