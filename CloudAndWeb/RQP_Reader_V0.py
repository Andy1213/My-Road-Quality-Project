# Purpose: read JSON data from vehicle logger file and resample to 1 Hz
# 2017 10 17 AJL Created file

import json
import platform
import pandas as pd

# init
JSONs = [] # a list of the decoded JSON strings
vTime = []
vRQM = []
vFlt = []
vDIF = []
vET = []
vReason = []

# open road roughness data file
fIn = open("C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\\20171017173700.csv","r")

# read it
icount = 0
for line in fIn:
    JSONs.append(json.loads(line))
    vRQM.append(JSONs[icount]['RQM'])
    vFlt.append(JSONs[icount]['FLT'])
    vDIF.append(JSONs[icount]['DIF'])
    vDIF[icount] = float(vDIF[icount])
    vReason.append(JSONs[icount]['Reason'])
    vRQM[icount] = float(vRQM[icount])
    vTime.append(JSONs[icount]['TimeStamp'])
    vET.append(icount * 3)
    #print vTime[icount], vET[icount], vRQM[icount]
    icount = icount + 1

# combine the lists together for pandas
myDataFrame = pd.DataFrame(data=vDIF, index=vET, columns=["vDIF"])
print "myDataFrame old index"
print myDataFrame

# resample to 1 Hz
print "Len vET ", len(vET), " and 3vET ", len(vET * 3)
newET = range(len(vET * 3))
print newET[0:12]
myDataFrame2 = myDataFrame.reindex(newET)
print "myDataFrame NEW index"              
print myDataFrame2
myDataFrame3 = myDataFrame2.interpolate(method='linear', limit=3, limit_direction='forward')
myDataFrame3.index.name = 'Tseconds'
print "myDataFrame Interpolated"              
print myDataFrame3

# save to csv file
myDataFrame3.to_csv("C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\\RQM_Interpolated.csv")

#print json.dumps(JSONs[1])
#print JSONs[1]['RQM']

# close the input file
fIn.close()
    




