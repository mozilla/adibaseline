## We need DAU for as far back we can go


import sys
import datetime
import json
import random
import subprocess
import time
import pandas as pd

useALL = True

ms = sqlContext.read.load("s3://telemetry-parquet/main_summary/v3", "parquet",mergeSchema=True)
ms2 = ms.select("sample_id","client_id","submission_date_s3","country","subsession_start_date")
if useALL:
    ms3 = ms2.filter("app_name='Firefox'")
else:
    random.seed(10)
    sampleids = [ random.randint(1,100) for x in range(1)]
    samplechar = [ "'{}'".format(str(x)) for x in sampleids]
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



dauActivity = sqlContext.sql("""
    select 
    activitydate,
    covgeo,
    count(distinct(client_id)) as dau
    from ms4
    where activitydate > '2016-01-01' 
    group by 1, 2
    order by 1,2
""").toPandas()

dauSubmission = sqlContext.sql("""
    select 
    submissiondate,
    covgeo,
    count(distinct(client_id)) as dau
    from ms4
    where submissiondate > '20160101' 
    group by 1,2
    order by 1,2
""").toPandas()


import cPickle as pickle
pickle.dump( [ dauActivity, dauSubmission] , open( "/tmp/dauBaseLine.pb", "wb" ) )
subprocess.call(["aws","s3","cp","/tmp/dauBaseLine.pb","s3://mozilla-metrics/sguha/"])



