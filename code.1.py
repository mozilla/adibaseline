################################################################################
## PySpark Invocation
## submit code using /usr/lib/spark/bin/spark-submit review.py
################################################################################
import pyspark
import py4j
from pyspark import SparkContext
from pyspark.sql import SQLContext
sc = pyspark.SparkContext()
sqlContext = SQLContext(sc)
print(sqlContext)



import sys
import datetime
import json
import random
import subprocess
import time
import pandas as pd

useALL = False

ms = sqlContext.read.load("s3://telemetry-parquet/main_summary/v4", "parquet",mergeSchema=True)
ms2 = ms.select("sample_id","client_id","submission_date_s3","country","subsession_start_date")
if useALL:
    ms3 = ms2.filter("app_name='Firefox'")
    FAC=1.0
else:
    random.seed(10)
    sampleids = [ random.randint(1,100) for x in range(10)]
    samplechar = [ "'{}'".format(str(x)) for x in sampleids]
    FAC=100.0/float(len(sampleids))
    ms3 = ms2.filter("app_name='Firefox' and sample_id in ({})".format( ",".join(samplechar)))

sqlContext.registerDataFrameAsTable(ms3, "ms3")

ms4 = sqlContext.sql("""
   select 
   client_id,
   submission_date_s3 as submissiondate,
   substring(subsession_start_date,1,10) as activitydate,
   case when country in ('US','DE','BR','FR','IN','ID','RU','PL','IT','GB','ES','CN','CA','JP','MX') then country
        else 'others'
   end as covgeo
   from ms3
""")
sqlContext.registerDataFrameAsTable(ms4,"ms4")

today = datetime.datetime.today()

dauActivity = sqlContext.sql("""
    select 
    activitydate as date,
    covgeo,
    count(distinct(client_id)) * {} as dauActivity
    from ms4
    where activitydate > '2016-01-01' 
    and activitydate < '{}'
    group by activitydate,covgeo  GROUPING SETS (
       (activitydate,covgeo), (activitydate)
    )
    having dauActivity>100
    order by 1,2
""".format(FAC, today.strftime("%Y-%m-%d"))).toPandas()
print(dauActivity)

dauSubmission = sqlContext.sql("""
    select 
    submissiondate as date,
    covgeo,
    count(distinct(client_id)) * {}  as dauSubmission
    from ms4
    where submissiondate > '20160101'  and submissiondate < '{}'
    group by submissiondate,covgeo  GROUPING SETS (
       (submissiondate,covgeo), (submissiondate)
    )
    having dauSubmission>100
    order by 1,2
""".format(FAC,today.strftime("%Y%m%d"))).toPandas()
print(dauSubmission)


for col in ('covgeo',): dauActivity.loc[dauActivity[col].isnull(), col] = 'all'
for col in ('covgeo',): dauSubmission.loc[dauSubmission[col].isnull(), col] = 'all'


dauActivity.to_csv("/tmp/dauActivity.csv",sep=",")
dauSubmission.to_csv("/tmp/dauSubmission.csv",sep=",")
subprocess.call(["aws","s3","cp","/tmp/dauSubmission.csv","s3://mozilla-metrics/user/sguha/tmp/"])
subprocess.call(["aws","s3","cp","/tmp/dauActivity.csv","s3://mozilla-metrics/user/sguha/tmp/"])

import sys
sys.exit()
