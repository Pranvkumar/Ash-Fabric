# Scale service replicas (used by Triage Agent for predictive scaling)
service_name  = "api-gateway"
service_image = "nginx:alpine"
replica_count = 2
memory_limit  = 512
cpu_limit     = 1024
