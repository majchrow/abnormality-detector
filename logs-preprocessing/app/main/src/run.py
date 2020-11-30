import os
from pyspark.sql import SparkSession
from argparse import ArgumentParser
from preprocessing import CallInfoPreprocessor, RosterPreprocessor, CallsPreprocessor

os.environ[
    "PYSPARK_SUBMIT_ARGS"
] = "--packages com.datastax.spark:spark-cassandra-connector_2.12:3.0.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.1 pyspark-shell"

PREPROCESSORS = {"callInfo": CallInfoPreprocessor, "roster": RosterPreprocessor, "calls": CallsPreprocessor}

if __name__ == "__main__":
    cores = os.environ["CORES"] if "CORES" in os.environ else "*"

    SPARK = (
    SparkSession.builder.appName("LogsAnalysisWithSpark")
    .master(f"local[{cores}]")
    .getOrCreate()
)

    SPARK.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
    SPARK.conf.set("spark.cassandra.connection.host", os.environ["CASSANDRA_HOST"])
    SPARK.conf.set("spark.cassandra.connection.port", os.environ["CASSANDRA_PORT"])
    SPARK.conf.set("spark.cassandra.auth.username", os.environ["CASSANDRA_USER"])
    SPARK.conf.set("spark.cassandra.auth.password", os.environ["CASSANDRA_PASSWORD"])
    SPARK.conf.set("spark.sql.shuffle.partitions", 5)
    path = os.environ["FILEPATH"]
    kafka = os.environ["KAFKA"]
    preprocessor = PREPROCESSORS[os.environ["UPDATE_TYPE"]](SPARK, kafka, path)
    writer = preprocessor.create_output_stream(os.environ["OUTPUT_MODE"])
    query = writer.start()
    query.awaitTermination()
