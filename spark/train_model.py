"""
Machine Learning Model Training for Cryptocurrency Prediction
Trains models for anomaly detection and trend prediction
"""

import logging
from typing import Dict, Any

import mlflow
import mlflow.spark
from pyspark.ml import Pipeline
from pyspark.ml.classification import RandomForestClassifier, LogisticRegression
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit, rand

from spark_config import (
    HDFS_PATHS, LOG_LEVEL,
    MLFLOW_EXPERIMENT_NAME, MLFLOW_TRACKING_URI
)

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class CryptoMLPipeline:
    """Machine learning pipeline for cryptocurrency analysis"""

    def __init__(self):
        """Initialize ML pipeline"""
        self.spark = self._create_spark_session()
        self._setup_mlflow()

    def _create_spark_session(self) -> SparkSession:
        """Create Spark session"""
        spark = (SparkSession
                 .builder
                 .appName("CryptoMLTraining")
                 .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:8020")
                 .getOrCreate())
        logger.info("✅ Spark session created")
        return spark

    def _setup_mlflow(self) -> None:
        """Setup MLflow"""
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
        logger.info("✅ MLflow configured")

    def read_features_from_hdfs(self) -> DataFrame:
        """Read engineered features from HDFS"""
        path = HDFS_PATHS['features']
        logger.info(f"Reading features from {path}")
        
        # Allow schema inference to handle potential missing columns gracefully
        df = (self.spark
              .read
              .option("mergeSchema", "true")
              .format("parquet")
              .load(path)
              .limit(1000) )

        logger.info(f"Loaded {df.count()} records from HDFS")
        return df

    def prepare_anomaly_detection_data(self, df: DataFrame) -> DataFrame:
        """Prepare data for anomaly detection model"""
        logger.info("Preparing data for anomaly detection...")

        # NOTE: We use 'price_mean' and 'price_stddev' because those are the actual names
        # in your streaming_job.py.
        
        # Synthesize a label for testing if 'is_anomaly' is missing
        if "is_anomaly" not in df.columns:
            logger.warning("'is_anomaly' column missing. Generating synthetic labels for testing.")
            # FIX: Randomly mark 10% of data as anomalies to ensure we have both classes (0 and 1)
            df = df.withColumn("is_anomaly", when(rand() > 0.9, True).otherwise(False))

        prepared_df = (df
                       .select(
                           col("symbol"),
                           col("price"),
                           col("volume"),
                           col("price_mean").alias("ma_1min"),     # Renaming to match expected feature
                           col("price_stddev").alias("volatility_1min"),
                           col("volume_change_pct"),
                           col("is_anomaly").cast("int").alias("label")
                       )
                       .na.fill(0)) # Fill nulls to prevent dropping all data

        logger.info(f"Prepared {prepared_df.count()} records for training")
        return prepared_df

    def prepare_prediction_data(self, df: DataFrame) -> DataFrame:
        """Prepare data for trend prediction"""
        logger.info("Preparing data for trend prediction...")

        # Create price direction label (Next price > Current price)
        # In a real batch job, you'd join with the "next minute's" data.
        # For this test, we'll simulate a target variable.
        
        prediction_df = (df
                         .withColumn("future_target", when(col("price") > col("price_mean"), 1).otherwise(0))
                         .select(
                             col("symbol"),
                             col("price"),
                             col("price_mean").alias("ma_1min"),
                             col("price_stddev").alias("volatility_1min"),
                             col("volume_change_pct"),
                             col("future_target").alias("label")
                         )
                         .na.fill(0))

        logger.info(f"Prepared {prediction_df.count()} records for prediction training")
        return prediction_df

    def train_anomaly_detection_model(self, train_df: DataFrame) -> Dict[str, Any]:
        """Train anomaly detection model using Random Forest"""
        logger.info("Training anomaly detection model...")

        with mlflow.start_run(run_name="Anomaly_Detection") as run:
            mlflow.log_param("model_type", "RandomForest")

            feature_cols = ["price", "volume", "ma_1min", "volatility_1min", "volume_change_pct"]
            assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")

            rf = RandomForestClassifier(labelCol="label", featuresCol="features", numTrees=20)
            pipeline = Pipeline(stages=[assembler, rf])

            train_data, test_data = train_df.randomSplit([0.8, 0.2], seed=42)
            model = pipeline.fit(train_data)

            predictions = model.transform(test_data)
            evaluator = BinaryClassificationEvaluator(labelCol="label")
            auc = evaluator.evaluate(predictions)

            logger.info(f"Anomaly Detection AUC: {auc:.4f}")
            mlflow.log_metric("auc", auc)
            mlflow.spark.log_model(model, "anomaly_model")

            return {"run_id": run.info.run_id}

    def train_prediction_model(self, train_df: DataFrame) -> Dict[str, Any]:
        """Train trend prediction model"""
        logger.info("Training trend prediction model...")

        with mlflow.start_run(run_name="Trend_Prediction") as run:
            mlflow.log_param("model_type", "LogisticRegression")

            feature_cols = ["price", "ma_1min", "volatility_1min", "volume_change_pct"]
            assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
            scaler = StandardScaler(inputCol="features", outputCol="scaledFeatures")
            lr = LogisticRegression(labelCol="label", featuresCol="scaledFeatures", maxIter=20)
            
            pipeline = Pipeline(stages=[assembler, scaler, lr])

            train_data, test_data = train_df.randomSplit([0.8, 0.2], seed=42)
            model = pipeline.fit(train_data)

            predictions = model.transform(test_data)
            evaluator = BinaryClassificationEvaluator(labelCol="label")
            auc = evaluator.evaluate(predictions)

            logger.info(f"Trend Prediction AUC: {auc:.4f}")
            mlflow.log_metric("auc", auc)
            mlflow.spark.log_model(model, "prediction_model")

            return {"run_id": run.info.run_id}

    def run_training(self) -> None:
        """Execute complete training pipeline"""
        try:
            logger.info("=" * 60)
            logger.info("🤖 Starting ML Model Training")
            logger.info("=" * 60)

            features_df = self.read_features_from_hdfs()
            
            # Check if we have enough data
            if features_df.count() == 0:
                logger.error("❌ No data found in HDFS! Cannot train model.")
                return

            anomaly_data = self.prepare_anomaly_detection_data(features_df)
            prediction_data = self.prepare_prediction_data(features_df)

            self.train_anomaly_detection_model(anomaly_data)
            self.train_prediction_model(prediction_data)

            logger.info("\n✅ Model training completed successfully")

        except Exception as e:
            logger.error(f"Training error: {e}", exc_info=True)
        finally:
            self.spark.stop()


def main():
    pipeline = CryptoMLPipeline()
    pipeline.run_training()


if __name__ == "__main__":
    main()