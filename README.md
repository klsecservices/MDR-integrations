<p align="center">
   <img src="https://img.shields.io/badge/Version-v1.0-blue" alt="Version">
   <a href="/LICENSE"><img src="https://img.shields.io/badge/License-Unlicense-brightgreen" alt="License"></a>
   <a href="/issues"><img src="https://img.shields.io/github/issues/klsecservices/MDR-integrations.svg?maxAge=60&style=flat-square" alt="Issues"></a>
</p>

# Kaspersky MDR Integration

Kaspersky MDR integration is a tool designed to provide the capability to integrate third-party systems with the Kaspersky Managed Detection and Response (MDR) Console. It helps to automatically route MDR incidents to the appropriate IRP/SOAR or ticket system for a more convenient way of communication with the Security Operations Team.

If you have a problem, request, or question then please open a new issue [here](/issues).

## Content

1. Overview (**[EN](overview_en.md)**, **[RU](overview_ru.md)**)
2. **[MDR Integration Utility](mdr_integration/README.md)**
3. **[TheHive integration package](integrations/thehive/README.md)**

## How it works

1. The tool connects to the Kaspersky MDR Console
2. New incidents and updates (such as comments, responses, attachments) from the Kaspersky MDR are saved in the directory
3. These incidents and updates can then be processed and uploaded to the third-party system for further action

Supported destinations: KUMA, TheHive, and any generic TCP/UDP receiver (e.g. a SIEM/syslog server) via the Event Sender module, in LEEF, CEF or raw JSON format.

## Requirements

These requirements are for the environment:

* Any Linux, MacOS or Windows
* Python 3.8+
* Python packages (see `requirements.txt`)
  * default: os, pathlib, re, json, logging, time, multiprocessing
  * PyYAML
  * requests
  * PyJWT
  * thehive4py - only required if the `thehive` integration module is enabled

## Installation

Before you start the installation, please read the **[Online documentation](https://support.kaspersky.com/MDR/en-US/204467.htm)**

First step:

```
git clone https://github.com/klsecservices/integration.git
```

Install the Python dependencies (skip `thehive4py` if you don't plan to enable the `thehive` module):

```
pip install -r requirements.txt
```

Second step, configure your connection with MDR Console

```
cd integration/mdr_integration/conf
touch .refresh_token
cp sample_config.yml config.yml
```

Create your refresh token using [this guide (kaspersky.com)](https://support.kaspersky.com/MDR/en-US/258278.htm). Paste the generated token into the .refresh_token file.

Configure ```conf/config.yml``` file. The most important settings:

* ```client_id``` - copy it from the MDR Console
* ```mdr_sync.modules.incident.filter.min_creation_time``` - specify the starting time for the download updates. Use Unix timestamp format with milliseconds (13 digits)
* Enable and configure at least one destination module (```kuma```, ```thehive``` or ```event_sender```) by setting its ```modules.incident.enable``` (and, where applicable, ```modules.asset.enable```) to ```true``` - otherwise incidents are only downloaded to the local data directory and never delivered anywhere

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

#### Automatic recovery from a crash loop

`main.py` supervises its own subprocesses and restarts any of them that dies. However, if the same subprocess keeps crashing repeatedly in a short period (see `CRASH_LOOP_THRESHOLD` / `CRASH_LOOP_WINDOW` in `main.py`), the whole service exits with a non-zero code instead of retrying forever, since the integration as a whole isn't useful with a module stuck down.

By default the example unit above has no `Restart=` directive, so systemd will **not** bring the service back up automatically after such an exit - it is left in a `failed` state for an operator to investigate. If you'd rather have systemd retry automatically, add to the `[Service]` section, e.g.:

```
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=600
StartLimitBurst=3
```

This is optional and left to each deployment to decide, since automatic restarts can mask a persistently broken configuration instead of surfacing it.

## References
* [Request a Free Kaspersky MDR POC](https://www.kaspersky.com/enterprise-security/managed-detection-and-response)
* [Kaspersky MDR Datasheet](https://content.kaspersky-labs.com/se/media/en/business-security/kaspersky-mdr-datasheet.pdf)
* [Kaspersky MDR Help](https://support.kaspersky.com/MDR/en-US/255956.htm)
* [Kaspersky MDR Open REST API Reference](https://support.kaspersky.com/MDR/RestAPI/REST_API_doc.html)
* [KUMA Community: Интеграция с Kaspersky MDR](https://kb.kuma-community.ru/books/integracii/page/integraciia-s-kaspersky-mdr)

## License

Project is distributed under the [Unlicense license](/LICENSE).