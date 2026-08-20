## mdr_integration

The core service that talks to the Kaspersky MDR Console and forwards incidents to the configured destinations. A single entrypoint (`main.py`) starts one subprocess per module and supervises them - see the root [README](../README.md) for installation and running as a service.

### Modules

* **token_updater** - keeps the access/refresh token pair in `conf/` up to date.
* **mdr_sync** - polls the MDR Console REST API and writes new incidents, updates and asset exports to `data/` as JSON files.
* **kuma** - reads the files from `data/` and creates/updates incidents in KUMA.
* **thehive** - reads the files from `data/` and creates/updates cases in TheHive.
* **event_sender** - reads the files from `data/` and forwards incidents to a generic TCP/UDP receiver (e.g. a SIEM/syslog server) in LEEF, CEF or raw JSON format.

Each module is independently enabled/disabled and configured under its own section in `conf/config.yml` - see `conf/sample_config.yml` for all available options and comments.

### Directory layout

* `conf/` - configuration file, tokens, and per-module processing state
* `data/` - incidents/updates/assets downloaded from MDR, pending delivery to the enabled destination modules
* `log/` - application log (`app.log`, rotated daily)
