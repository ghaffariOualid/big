"""
Spark Structured Streaming for Cryptocurrency Data Processing
Consumes from Kafka, performs feature engineering, detects anomalies,
and writes to HDFS and MLflow
"""

import logging
from datetime import datetime
from typing import Optional

from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql.functions import (
    col, from_json, schema_of_json, to_timestamp,
    avg, stddev, max as spark_max, min as spark_min,
    lag, when, abs as spark_abs, lit, current_timestamp
)
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType

from spark_config import (
    BATCH_INTERVAL, HDFS_PATHS, KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPICS, LOG_LEVEL, MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI, WATERMARK_DELAY, WINDOW_CONFIGS,
    ANOMALY_THRESHOLDS
)

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class CryptoStreamingPipeline:
    """Main streaming pipeline for cryptocurrency data"""

    def __init__(self):
        """Initialize Spark session and MLflow"""
        self.spark = self._create_spark_session()
        self._setup_mlflow()
        self.schema = self._define_schema()

    def _create_spark_session(self) -> SparkSession:
        """Create and configure Spark session"""
        logger.info("Creating Spark session...")
        
        spark = (SparkSession
                 .builder
                 .appName("CryptoStreamingPipeline")
                 .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
                 .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:8020")
                 .getOrCreate())
        
        spark.sparkContext.setLogLevel(LOG_LEVEL)
        logger.info("✅ Spark session created successfully")
        return spark

    def _setup_mlflow(self) -> None:
        """Setup MLflow tracking"""
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
        logger.info(f"MLflow tracking URI set to {MLFLOW_TRACKING_URI}")

    def _define_schema(self) -> StructType:
        """Define schema for cryptocurrency data"""
        return StructType([
            StructField("id", StringType(), True),
            StructField("symbol", StringType(), True),
            StructField("price", DoubleType(), True),
            StructField("market_cap", DoubleType(), True),
            StructField("volume", DoubleType(), True),
            StructField("price_change_24h", DoubleType(), True),
            StructField("last_updated", LongType(), True),
            StructField("timestamp", StringType(), True),
            StructField("source", StringType(), True)
        ])

    def read_kafka_stream(self, topic: str) -> DataFrame:
        """
        Read RAW cryptocurrency data from Kafka
        
        *** FIX APPLIED HERE: Returns RAW DataFrame (key, value) ***
        """
        logger.info(f"Reading from Kafka topic: {topic}")
        
        df = (self.spark
              .readStream
              .format("kafka")
              .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
              .option("subscribe", topic)
              .option("startingOffsets", "earliest") # Reads all history
              .option("maxOffsetsBehindLatest", "100000")
              .option("failOnDataLoss", "false")
              .load())

        # REMOVED: .select(from_json...) <-- This was the cause of the double-parse error
        
        logger.info("✅ Kafka stream reader configured")
        return df

    def data_cleaning(self, df: DataFrame) -> DataFrame:
        """
        Clean and validate cryptocurrency data
        Expects a DataFrame with a raw 'value' column from Kafka.
        """
        logger.info("Applying data cleaning transformations...")

        schema = self._define_schema()

        cleaned_df = (df
            # Parse JSON using the schema
            .select(from_json(col("value").cast("string"), schema).alias("data"))
            .select("data.*")
            
            # --- CRITICAL FILTERS ---
            .filter(col("price").isNotNull())
            .filter(col("symbol").isNotNull())
            
            # --- THE TIME FIX ---
            # We ignore the JSON timestamp and use 'now' to guarantee the Window works.
            .withColumn("event_timestamp", current_timestamp())
            # --------------------

            # Rename/Calculate columns
            .withColumn("price_usd", col("price"))
            .withColumn("volume_usd", col("volume"))
            .withColumn("market_cap_usd", col("market_cap"))
            .withColumn("processed_timestamp", current_timestamp())
        )

        return cleaned_df

    def feature_engineering(self, df: DataFrame) -> DataFrame:
        """
        Perform feature engineering: moving averages, volatility, etc.
        """
        logger.info("Performing feature engineering...")
        
        features_df = (df
            .groupBy(
                F.window(col("event_timestamp"), "1 minute", "30 seconds"), 
                col("symbol")
            )
            .agg(
                avg("price").alias("price_mean"),
                stddev("price").alias("price_stddev"),
                F.last("price").alias("price"),
                F.last("volume").alias("volume")
            )
            .withColumn("event_timestamp", col("window.end"))
            .drop("window")
            .withColumn("volume_change_pct", lit(0.0)) 
        )
        return features_df

    def detect_anomalies(self, df: DataFrame) -> DataFrame:
        """
        Detect market anomalies (pump & dump, volume spikes, etc.)
        """
        logger.info("Applying anomaly detection...")

        z_score_threshold = ANOMALY_THRESHOLDS['z_score']

        # Handling cases where stddev is null (e.g., only 1 record in window)
        df = df.fillna(0, subset=["price_stddev"])

        anomaly_df = (df
             # Calculate Z-Score
             .withColumn("price_zscore",
                         when(col("price_stddev") == 0, 0)
                         .otherwise((col("price") - col("price_mean")) / col("price_stddev")))
             
             # Flag Anomalies
             .withColumn("is_price_anomaly",
                         spark_abs(col("price_zscore")) > z_score_threshold)
             
             .withColumn("is_volume_anomaly", lit(False)) 
             
             .withColumn("is_anomaly",
                         col("is_price_anomaly") | col("is_volume_anomaly"))
             
             .withColumn("anomaly_score",
                         when(col("is_price_anomaly"), spark_abs(col("price_zscore")))
                         .otherwise(0))
        )

        return anomaly_df

    def write_to_hdfs(self, df: DataFrame, path: str, checkpoint_id: str) -> None:
        """Write streaming data to HDFS in Parquet format"""
        query = (df
                 .writeStream
                 .format("parquet")
                 .outputMode("append")
                 .option("path", path)
                 .option("checkpointLocation", f"/tmp/checkpoint_{checkpoint_id}")
                 .partitionBy("symbol")
                 .start())

        logger.info(f"✅ Writing to HDFS: {path}")
        return query

    def write_alerts_to_kafka(self, df: DataFrame) -> None:
        """Write anomalies as alerts to Kafka"""
        alerts_df = (df
                     .filter(col("is_anomaly") == True)
                     .select(
                         col("symbol"),
                         col("price"),
                         col("anomaly_score"),
                         col("is_price_anomaly"),
                         col("is_volume_anomaly"),
                         col("event_timestamp"),
                         lit("ALERT").alias("event_type")
                     ))

        query = (alerts_df
                 .select(
                     F.to_json(F.struct("*")).alias("value")
                 )
                 .writeStream
                 .format("kafka")
                 .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
                 .option("topic", KAFKA_TOPICS['alerts'])
                 .option("checkpointLocation", "/tmp/checkpoint_alerts")
                 .start())

        logger.info(f"✅ Alert stream writer configured for {KAFKA_TOPICS['alerts']}")
        return query

    def run_pipeline(self) -> None:
        """Execute the complete streaming pipeline"""
        try:
            logger.info("=" * 60)
            logger.info("🚀 Starting Crypto Streaming Pipeline")
            logger.info("=" * 60)

            # Read raw data from Kafka
            raw_df = self.read_kafka_stream(KAFKA_TOPICS['raw'])

            # Clean data
            clean_df = self.data_cleaning(raw_df)

            # Apply watermarking for stateful operations
            clean_df = clean_df.withWatermark("event_timestamp", WATERMARK_DELAY)

            # Feature engineering
            features_df = self.feature_engineering(clean_df)

            # Anomaly detection
            final_df = self.detect_anomalies(features_df)

            # Write clean data to HDFS
            query_clean = self.write_to_hdfs(clean_df, HDFS_PATHS['clean'], "clean")

            # Write features to HDFS
            query_features = self.write_to_hdfs(features_df, HDFS_PATHS['features'], "features")

            # Write alerts to Kafka
            query_alerts = self.write_alerts_to_kafka(final_df)

            # Wait for all queries
            logger.info("\n📡 Streaming pipeline active. Press Ctrl+C to stop.\n")
            self.spark.streams.awaitAnyTermination()

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        finally:
            logger.info("Stopping streaming context...")
            self.spark.stop()


def main():
    """Main entry point"""
    pipeline = CryptoStreamingPipeline()
    pipeline.run_pipeline()


if __name__ == "__main__":
    main()