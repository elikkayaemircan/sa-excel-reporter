#!/reports/virtualenv/bin/python3

import os, re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

allAdmins = { "DNUSERNAME" : ("NAME SURNAME"),
}

WORKDIR="/reports"
CHECK="TELEGRAF"
TIMESTAMP=datetime.now().strftime("%Y-%m-%d")

names_check = ["HOSTNAME", "CHECK", "MESSAGE"]
df_check = pd.read_csv("/reports/"+CHECK+"/"+TIMESTAMP+"_TELEGRAF.csv", header=None, delimiter=",", names=names_check)
df_check["HOSTNAME"] = df_check["HOSTNAME"].str.upper()
df_check["HOSTNAME"] = df_check["HOSTNAME"].str.split(".").str[0]

names_maindb = ["HOSTNAME", "HOSTID", "COL1", "ADMIN"]
df_maindb = pd.read_csv("/reports/tmp/"+TIMESTAMP+"-MAINDB-INVENTORY.csv", header=None, dtype=str, names=names_maindb)
drops_maindb=["COL1"]
df_maindb.drop(drops_maindb, inplace=True, axis=1)
df_maindb["ADMIN"] = df_maindb["ADMIN"].str.strip()
df_maindb["HOSTNAME"] = df_maindb["HOSTNAME"].str.split(".").str[0]

merged = pd.merge(df_maindb, df_check, on="HOSTNAME", how="left")
merged["CHECK"] = merged["CHECK"].fillna("checkNA")
merged["MESSAGE"] = merged["MESSAGE"].fillna("sunucu management uygulamasinde bulunamadi")

for key in allAdmins:
    merged["ADMIN"] = merged["ADMIN"].replace([key], allAdmins[key])

writer = pd.ExcelWriter("/reports/"+CHECK+"/telegrafControl_"+TIMESTAMP+".xlsx", engine="xlsxwriter")
merged.to_excel(writer, sheet_name="Results", index=None, header=True)

wb = writer.book
ws = writer.sheets["Results"]

(max_row, max_col) = merged.shape
column_settings = [{'header': column} for column in merged.columns]
ws.add_table(0, 0, max_row, max_col - 1, {'columns': column_settings})
ws.set_column(0, max_col - 1, 12)

writer.save()

merged.drop( ["HOSTID", "MESSAGE"] , inplace=True , axis=1 )
merged["CHECK"].replace( {"EXCEPTION": "c_except", "FAIL": "a_fail", "OK": "d_ok", "checkNA": "b_checkna"}, inplace=True )

pivot = merged.pivot_table(index="ADMIN", columns="CHECK", aggfunc=len, fill_value=0)
pivot = pivot.reindex(pivot["HOSTNAME"].sort_values(by="a_fail", ascending=False).index)
pivot.columns = ["FAIL", "checkNA", "EXCEPTION", "OK"]
pivot = pivot.to_html()

html_string = """
<html>
  <head></head>
  <body>
    <p> <b> Rapor Tarihi:</b> {date}
    </p>
    <p> <b> Sunucu Grup:</b> Tum Linux Sunucular, RHEL5 haric <br>
        <b> Kurulum Scripti:</b> install_telegraf.sh <br>
    </p>
    <p> <b> checkNA:</b> NOT APPLICABLE, detay icin Excel icerisinde MESSAGE kolonunu kontrol ediniz <br>
        <b> EXCEPTION:</b> dosya icinde tanim yapabilirsiniz <br>
    </p>
    <p> http://127.0.0.1/grafana adresinden sunuculardan toplanan metrikleri kontrol edebilirsiniz
    </p>
    {table}
    <p> Powered by Python <br> Developed by EE <p>
  </body>
</html>
"""
html_string = html_string.format(date=TIMESTAMP, table=pivot)

xlsFile=WORKDIR+"/reports/"+CHECK+"/telegrafControl_"+TIMESTAMP+".xlsx"

smtp = SMTP("smtp.example.com")
msg = MIMEMultipart()
msg['Subject'] = ("Telegraf Ajan Kontrolu")
msg['From'] = "reporter@example.com"

_FILENAME = "telegrafControl_"+TIMESTAMP+".xlsx"
part = MIMEApplication(open(xlsFile, "rb").read())
part.add_header('Content-Disposition', 'attachment', filename=_FILENAME)
msg.attach(part)

part = MIMEText(html_string, 'html')
msg.attach(part)

msg['To'] = "user@mail.example.com"
smtp.sendmail(msg['From'], msg['To'], msg.as_string())
