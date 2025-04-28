import argparse
import subprocess
import logging
import requests
import time
from prometheus_client import start_http_server, Gauge

job = "qdrant_exporter"

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义 Prometheus 指标
collection_segments_count = Gauge('qdrant_collection_segments_count', 'Segments count of collection', ['collection_id', 'job'])
collection_points_count = Gauge('qdrant_collection_points_count', 'Points count of collection', ['collection_id', 'job'])
collection_status = Gauge('qdrant_collection_status', 'Status of collection', ['collection_id', 'job'])
shard_status = Gauge('qdrant_shard_status', 'Status of shards', ['collection_id', 'shard_id', 'job'])

# 获取本机IP
def get_local_ip():
    try:
        result = subprocess.run(
            "for device in $(ls -l /sys/class/net/ | sed 1d | awk '!/virtual/{print $9}'); do ip -4 -o addr show $device primary | awk -F'[/ ]' '{print $7}'; done | head -n1",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.stdout.decode('utf-8').strip()
    except Exception as e:
        logging.error(f"Failed to get local IP: {e}")
        return "127.0.0.1"

# 采集Qdrant metrics
def collect_qdrant_metrics(api_key, qdrant_port, ip):
    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        base_url = f"http://{ip}:{qdrant_port}"

        # 获取所有 collection
        resp = requests.get(f"{base_url}/collections", headers=headers, timeout=5)
        resp.raise_for_status()
        collections = resp.json()['result']['collections']

        for coll in collections:
            coll_name = coll['name']

            # 获取 collection 详情
            resp = requests.get(f"{base_url}/collections/{coll_name}", headers=headers, timeout=5)
            resp.raise_for_status()
            result = resp.json()['result']

            status = result.get('status', 'unknown')
            segments_count = result.get('segments_count', 0)
            points_count = result.get('points_count', 0)

            collection_segments_count.labels(collection_id=coll_name, job=job).set(segments_count)
            collection_points_count.labels(collection_id=coll_name, job=job).set(points_count)

            status_map = {
                'green': 1,
                'yellow': 2,
                'red': 3
            }
            collection_status.labels(collection_id=coll_name, job=job).set(status_map.get(status, 0))

            # 拉取 shard 状态
            resp = requests.get(f"{base_url}/collections/{coll_name}/cluster", headers=headers, timeout=5)
            resp.raise_for_status()
            shards_info = resp.json()['result']['local_shards']

            for shard in shards_info:
                shard_id = str(shard['shard_id'])
                state = shard['state']
                if state == 'Active':
                    shard_status.labels(collection_id=coll_name, shard_id=shard_id, job=job).set(1)
                elif state == 'Partial':
                    shard_status.labels(collection_id=coll_name, shard_id=shard_id, job=job).set(2)
                elif state == 'Dead':
                    shard_status.labels(collection_id=coll_name, shard_id=shard_id, job=job).set(3)
                else:
                    shard_status.labels(collection_id=coll_name, shard_id=shard_id, job=job).set(0)

    except Exception as e:
        logging.error(f"Failed to collect qdrant metrics: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Qdrant Prometheus Exporter')
    parser.add_argument('--api_key', required=True, help='API Key for Qdrant')
    parser.add_argument('--qdrant_port', type=int, default=6333, help='Qdrant server port (default 6333)')
    parser.add_argument('--interval', type=int, default=10, help='Collect interval seconds (default 10)')
    parser.add_argument('--listen_port', type=int, default=8090, help='Exporter HTTP listen port (default 8090)')
    parser.add_argument('--ip', type=str, default=None, help='Qdrant Server IP address (optional)')
    args = parser.parse_args()

    if args.ip:
        IP = args.ip
        logging.info(f"Using specified IP: {IP}")
    else:
        IP = get_local_ip()
        logging.info(f"Detected local IP: {IP}")

    # 启动HTTP server
    start_http_server(args.listen_port)
    logging.info(f"Exporter started on port {args.listen_port}")

    # 循环采集
    while True:
        collect_qdrant_metrics(args.api_key, args.qdrant_port, IP)
        time.sleep(args.interval)
