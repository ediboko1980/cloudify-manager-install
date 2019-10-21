docker ps -q | xargs docker rm -f

docker run --name postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -e POSTGRES_PASSWORD=postgres -d postgres
docker run --name cloudify-manager-queue -d -v $(pwd)/config_queue.yaml:/etc/cloudify/config.yaml cloudify-manager-queue

docker exec -it cloudify-manager-queue tail -f  /var/log/cloudify/manager/cfy_manager.log
docker cp cloudify-manager-queue:/etc/cloudify/ssl/rabbitmq-cert.pem rabbitmq-cert.pem

docker run --name cloudify-manager -v $(pwd)/config2.yaml:/tmp/config.yaml -v $(pwd)/rabbitmq-cert.pem:/tmp/rabbitmq-cert.pem cloudify-manager
docker exec -it cloudify-manager tail -f  /var/log/cloudify/manager/cfy_manager.log
docker exec -it cloudify-manager grep Finished /var/log/cloudify/manager/cfy_manager.log

docker cp cloudify-manager:/etc/cloudify/ssl/cloudify_internal_ca_key.pem ca_key.pem
docker cp cloudify-manager:/etc/cloudify/ssl/cloudify_internal_ca_cert.pem ca_cert.pem

docker run --name cloudify-manager-2 -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN  -v $(pwd)/config3.yaml:/etc/cloudify/config.yaml  -v $(pwd)/rabbitmq-cert.pem:/tmp/rabbitmq-cert.pem -v $(pwd)/ca_cert.pem:/tmp/ca_cert.pem -v $(pwd)/ca_key.pem:/tmp/ca_key.pem cloudify-manager

docker exec -it cloudify-manager-2 tail -f  /var/log/cloudify/manager/cfy_manager.log
docker exec -it cloudify-manager-2 grep Finished /var/log/cloudify/manager/cfy_manager.log
