# **ASH-Fabric Automation Logic Table**

| Event | Condition | Automated Action | Secondary Agent Action |
| :---- | :---- | :---- | :---- |
| **OOM Kill** | Memory \> 95% | Restart Container | Scale memory limit in K8s manifest by 20% |
| **Latency Spike** | Latency \> 500ms | Check DB connections | If DB connections full, spin up a Read Replica |
| **Zombie Resource** | CPU \< 1% for 4hrs | Send Warning | Terminate instance and backup data |
| **Disk Full** | Storage \> 90% | Purge /tmp and old logs | Expand Volume via Cloud API (AWS/GCP/Azure) |
| **Predictive Peak** | Forecast \> Capacity | Warm-up instances | Pre-fetch data into Redis Cache |

