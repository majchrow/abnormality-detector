import os
from pyspark.sql import SparkSession
from argparse import ArgumentParser
from preprocessing import CallInfoPreprocessor, RosterPreprocessor

os.environ[
    "PYSPARK_SUBMIT_ARGS"
] = "--packages com.datastax.spark:spark-cassandra-connector_2.12:3.0.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.1 --conf spark.cassandra.connection.host=127.0.0.1 --conf spark.cassandra.connection.port=9042 --conf spark.cassandra.auth.username=cassandra --conf spark.cassandra.auth.password=cassandra pyspark-shell"
SPARK = (
    SparkSession.builder.appName("LogsAnalysisWithSpark")
    .master("local[*]")
    .getOrCreate()
)
PATHS = {
    "callInfo": "/run/media/jola/DATA/JOLEG/dokumenty/Inzynierka/abnormality-detector/logs-analysis/app/main/resources/callInfo_sample.json",
    "roster":  "/run/media/jola/DATA/JOLEG/dokumenty/Inzynierka/abnormality-detector/logs-analysis/app/main/resources/roster_sample.json"
}
PREPROCESSORS = {
    "callInfo": CallInfoPreprocessor,
    "roster": RosterPreprocessor
}


def create_parser():
    parser = ArgumentParser()
    parser.add_argument('--type',
                        type=str,
                        default='callInfo',
                        help='message type')
    return parser


if __name__ == "__main__":
    parser = create_parser()
    FLAGS = parser.parse_args()
    preprocessor = PREPROCESSORS[FLAGS.type]
    preprocessor.prepare_final_df()
    writer = preprocessor.create_output_stream()
    writer.start()
    writer.awaitTermination()
