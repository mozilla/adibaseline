## We need DAU for as far back we can go
## need pyspark!!

import sys
import datetime
import json
import random
import subprocess
import time
import pandas as pd

useALL = True

ms = spark.read.load("s3://telemetry-parquet/main_summary_v4", "parquet",mergeSchema=True)
ms2 = spark.sql("select sample_id, client_id, submission_date_s3, country, subsession_start_date from main_summary")
ms2 = ms.select("sample_id","client_id","submission_date_s3","country","subsession_start_date")
sqlContext.registerDataFrameAsTable(ms2, "ms2")

if useALL:
    text = ""
else:
    random.seed(10)
    sampleids = [ random.randint(1,100) for x in range(10)]
    samplechar = [ "'{}'".format(str(x)) for x in sampleids]
    text = "and sample_id in ({})".format( ",".join(samplechar))

sqlContext.registerDataFrameAsTable(ms3, "ms3")

ms4 = spark.sql("""
   select 
   client_id,
   submission_date_s3 as submissiondate,
   substring(subsession_start_date,1,10) as activitydate
   from main_summary
   where app_name='Firefox'
   {}
""".format(text))
sqlContext.registerDataFrameAsTable(ms4,"ms4")



dauActivity = spark.sql("""
    select 
    activitydate,
    covgeo,
    count(distinct(client_id)) as dau
    from ms4
    where activitydate > '2016-01-01' 
    group by 1, 2
    order by 1,2
""").toPandas()

dauSubmission = spark.sql("""
    select 
    submissiondate,
    covgeo,
    count(distinct(client_id)) as dau
    from ms4
    where submissiondate > '20160101' 
    group by 1,2
    order by 1,2
""").toPandas()


dauSubmission.write_csv("/tmp/dauSubmission.csv")
dauActivity.write_csv("/tmp/dauActivity.csv")

#import cPickle as pickle
#pickle.dump( [ dauActivity, dauSubmission] , open( "/tmp/dauBaseLine.pb", "wb" ) )
#subprocess.call(["aws","s3","cp","/tmp/dauBaseLine.pb","s3://mozilla-metrics/sguha/"])


subprocess.call(["aws","s3","cp","/tmp/dauActivity.csv","s3://mozilla-metrics/sguha/"])
subprocess.call(["aws","s3","cp","/tmp/dauSubmission.csv","s3://mozilla-metrics/sguha/"])



