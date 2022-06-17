import os
import datetime

os.chdir('/home/ec2bot')

today = datetime.date.today().strftime('%Y-%m-%d')

uptime = []
with open("uptime.txt", "rt") as text:
    for line in text:
        if today in line:
            uptime.append(line[12:25])
        else:
            break
text.close()
totalUptime = datetime.timedelta()
for i in uptime:
    (h, m, s) = i.split(':')
    d = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(float(s)))
    totalUptime += d
print(str(totalUptime))
