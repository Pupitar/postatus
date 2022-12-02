# postatus

Here's mine, slightly harder? to configure approach for PoGO metrics.

First you need to get this script working, and populate own `config.json` with needed things. After that start it using `uvicorn main:app --port 9839` command.
Setup it so it will be visible from Prometheus instance. In my case Prometheus is on another server hence I created nginx proxy on `metrics.domain.com`

After that setup a Prometheus instance. And add scrape config like that:

```
global:
  scrape_interval:     30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: "pogo"
    scrape_interval: 30s

    basic_auth:
      username: "prometheus_username"
      password: "prometheus_password"

    scheme: https
    static_configs:
      - targets: ['metrics.domain.com']
```

Lastly add Prometheus as new Data Source to Grafana and load dashboard https://github.com/Pupitar/postatus/issues/1 
