# Kaspersky MDR Integration

Kaspersky MDR integration is a tool designed to provide the capability to integrate third-party systems with the Kaspersky Managed Detection and Response (MDR) Console. It helps to automatically route MDR incidents to the appropriate IRP/SOAR or ticket system for more convinient way of communication with Security Operation Team.

## Content

1. Overview (**[EN](overview_en.md)**, **[RU](overview_ru.md)**)
2. **[MDR Integration Utility](mdr_integration/README.md)**
3. **[TheHive integration package](integrations/thehive/README.md)**

## How it works

1. The tool connects to the Kaspersky MDR Console
2. New incidents and updates (such as comments, responses, attachmetns) from the Kaspersky MDR are saved in the directory
3. These incidents and updates can then be processed and uploaded to the third-party system for further action

## Requirements

These requirements are for the environment:

* Any Linux, MacOS or Windows
* Python 3.8+
* Python packages
  * default: os, pathlib, re, json, logging, time, multiprocessing, re
  * yaml
  * requests
  * PyJWT

## Installation

Before start to install please read the **[Online documentation](https://support.kaspersky.com/MDR/en-US/204467.htm)**

First step:

```
git clone https://github.com/klsecservices/integration.git
```

Second step, configure you connection with MDR Console

```
cd integration/mdr_integration/conf
touch .refresh_token
cp sample_config.yml config.yml
```

Create your refresh token using [this guide (kaspersky.com)](https://support.kaspersky.com/MDR/en-US/204468.htm). Paste generated token to the .refresh_token file.

Configure ```conf/config.yml``` file. The most important settings:

* ```client_id``` - copy it from the MDR Console
* ```mdr_sync.filter.incidents.min_creation_time``` - specify the starting time for the download updates. Use Unix timestamp fotmat with miliseconds (13 digits)

Third step, run script

```
python main.py
```

### Server SSL certificate validation

Optional. In order to enable server certificate verification you need to download certificate chain in PEM format:

```
-----BEGIN CERTIFICATE-----
...<server cert>...
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
...<CA cert>...
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
...<root cert>...
-----END CERTIFICATE-----
```

Change ```conf/config.yml``` file:
```
ssl_cert: conf/mdr.pem
```

### Run util as a service

Optional. Create service config file. Example:

```
[Unit]
Description=Kaspersky MDR Integration Service
Wants=network-online.target
After=network-online.target

[Service]
WorkingDirectory=/opt/integration/mdr_integration

User=mdr_user
Group=mdr_user

ExecStart=/usr/bin/python3 /opt/integration/mdr_integration/main.py

StandardOutput=null
StandardError=null

# Disable timeout logic and wait until process is stopped
TimeoutStopSec=0

# SIGTERM signal is used to stop the Java process
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

Save the file ```mdr_integration.service``` to the directory ```/etc/systemd/system/```

Create, register and start the service:

```
sudo systemctl daemon-reload
sudo systemctl enable mdr_integration.service
sudo systemctl start mdr_integration.service
sudo systemctl status mdr_integration.service
```

## References
* [Kaspersky MDR (kaspersky.com)](https://support.kaspersky.com/MDR/en-US/255956.htm)
* [Kaspersky MDR Open REST API Reference](https://support.kaspersky.com/MDR/RestAPI/REST_API_doc.html)
* [KUMA Community: Интеграция с Kaspersky MDR](https://kb.kuma-community.ru/books/integracii/page/integraciia-s-kaspersky-mdr)