d <- odbc()
adi <- data.table(d$q(sprintf("select
 bl_date as date,
 case when cntry_code in ('US','DE','BR','FR','IN','ID','RU','PL','IT','GB','ES','CN','CA','JP','MX') then cntry_code
        else 'others'
 end as covgeo,
 sum(tot_requests_on_date) as adi
 from
 copy_adi_dimensional_by_date
 where bl_date >='2016-01-01' and product='Firefox' and v_prod_major>'42'
 group by 1,2 order by 1,2")))


ladi <- data.table(d$q(sprintf("select
 bl_date as date,
 sum(tot_requests_on_date) as adi
 from
 copy_adi_dimensional_by_date
 where bl_date >='2014-01-01' and product='Firefox'   
 group by 1 order by 1")))

save(ladi,adi,file="/tmp/adi")


system('aws s3 cp s3://mozilla-metrics/sguha/tmp/dauActivity.csv /tmp/')
system('aws s3 cp s3://mozilla-metrics/sguha/tmp/dauSubmission.csv /tmp/')

dsu <- fread("/tmp/dauSubmission.csv")[, V1:=NULL][dauSubmission>100,][, date:=as.Date(as.character(date),"%Y%m%d")]
dac <- fread("/tmp/dauActivity.csv")[, V1:=NULL][dauActivity>100,][, date:=as.Date(as.character(date),"%Y-%m-%d")]
dau <- merge(dsu,dac, by=c('date','covgeo'))
load("/tmp/adi")

adi <- rbind(adi, adi[, list(covgeo='all', adi=sum(adi)),by=date])[, date:=as.Date(date,'%Y-%m-%d')]
alldi <- merge(dau, adi,  by=c('date','covgeo'))[order(date,covgeo),]
alldiall <- alldi[covgeo=='all',][, ":="( s2a=dauSubmission/dauActivity, s2adi=dauSubmission/adi)]
alldiall[, ":="(year=strftime(date,"%Y"),doy=as.numeric(as.character(strftime(date,"%j")))
               ,woy=as.character(strftime(date,"%U")))]
NN <- 14
alldiall[,":="(sDauAc=as.numeric(filter(dauActivity/1e6,rep(1,NN)/NN,side=1)),
               sDauSub=as.numeric(filter(dauSubmission/1e6,rep(1,NN)/NN,side=1)),
               sAdi=as.numeric(filter(adi/1e6,rep(1,NN)/NN,side=1)))]

alldiall[,":="(ss2a=sDauSub/sDauAc, ss2adi=sDauSub/sAdi)]

alldiall[, delta:=sDauSub-sAdi]


ladi[, ":="(year=strftime(date,"%Y"),doy=as.numeric(as.character(strftime(date,"%j")))
           ,woy=as.character(strftime(date,"%U")))]
NN <- 14; NNSmall <- 7
ladi[,":="( madi=adi/1e6,sAdi=as.numeric(filter(adi/1e6,rep(1,NN)/NN,side=1)),
           s2Adi=as.numeric(filter(adi/1e6,rep(1,NNSmall)/NNSmall,side=1)))]
ladi[, qtr:= sapply(strftime(date,"%B"), function(s){
    if(s %in% c("January","February","March")) '2016-01-01:2016-03-30'
    else if(s %in% c("April","May","June")) '2016-04-01:2016-06-30'
    else if(s %in% c("July","August","September")) '2016-07-01:2016-09-30'
    else if(s %in% c("October","November","December")) '2016-10-01:2016-12-31'
    })]

ladi$month <- strftime(ladi$date,"%b")
ladi$dom <- as.integer(strftime(ladi$date,"%d"))
ladi <- ladi[order(month,date),][ ,id:=1:.N,by=list(month)][,]
adi <- ladi[order(month, id),]



ladi[,reldiff:={
    ty <- .SD
    ly <- ladi[month == .BY$month & year == as.numeric(.BY$year) -1 ,]
    if(nrow(ly)==0) {
        NA_real_
    } else {
        r  = (ty$sAdi - ly$sAdi)/ly$sAdi*100
        if(length(r) > nrow(.SD) ) {
            r <- head(r,nrow(.SD))
        }
        r
    }
},by=list(month,year)]

ladi[,diff:={
    ty <- .SD
    ly <- ladi[month == .BY$month & year == as.numeric(.BY$year) -1 ,]
    if(nrow(ly)==0) {
        NA_real_
    } else {
        r  = (ty$sAdi - ly$sAdi)
        if(length(r) > nrow(.SD) ) {
            r <- head(r,nrow(.SD))
        }
        r
    }
},by=list(month,year)]


fit=stl(ts(ladi$adi/1e6,frequency=12),s.window=12)
ladi[, seasonal:=fit$time.series[,"seasonal"]]
library(feather)
alldiall[, date:=as.character(date)]
ladi[, date:=as.character(date)]
write_feather(alldiall,"./web/alldiall.feather")
write_feather(ladi,"./web/ladi.feather")

### Get CSV for Shraddha
## adi For Firefox
adiAcrossYears = ladi[, list(date=date,year=year,dayOfYear=doy,smoothed14ADI=sAdi
                             ,reldiffYoYpct=reldiff,diffYoYmm=diff)][order(date),]

### Compare smoothedADI from versions
## adi is for Firefox and v>42
dailyUsageCompare=alldiall[, list(date=date,year=year,dayOfyear=doy,dauActivityDate=sDauAc,dauSubmissionDate=sDauSub,
                                  smoothed14ADI=sAdi)][order(date),]

write.csv(adiAcrossYears,"/tmp/adiAcrossYears.csv")
write.csv(dailyUsageCompare,"/tmp/dailyUsageCompare.csv")
