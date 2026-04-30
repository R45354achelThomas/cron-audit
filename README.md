# cron-audit

> Parses and documents cron jobs across servers into a unified human-readable report with conflict detection.

## Installation

```bash
pip install cron-audit
```

## Usage

Point `cron-audit` at one or more crontab files or remote servers and generate a consolidated report:

```bash
# Audit a local crontab file
cron-audit --file /etc/crontab --output report.html

# Audit multiple servers via SSH
cron-audit --hosts web1,web2,db1 --user deploy --output report.md

# Detect scheduling conflicts only
cron-audit --file /var/spool/cron/crontabs/* --conflicts-only
```

**Example output:**

```
[INFO] Parsed 24 cron jobs across 3 hosts
[WARN] Conflict detected: web1 and web2 both schedule /usr/bin/backup.sh at 02:00 daily
[OK]   Report written to report.md
```

Supported output formats: `markdown`, `html`, `json`, `plaintext`

## Configuration

Optional `cron-audit.yml` for persistent settings:

```yaml
hosts:
  - web1.example.com
  - web2.example.com
user: deploy
output: report.md
format: markdown
```

## Requirements

- Python 3.8+
- `paramiko` (for SSH-based auditing)
- `croniter` (for schedule parsing and conflict detection)

## License

This project is licensed under the [MIT License](LICENSE).