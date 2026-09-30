"""
性能测试与优化建议
用于评估系统在高并发场景下的表现
"""

import time
import random
from concurrent.futures import ThreadPoolExecutor
from medicine_matcher import MedicineMatcher, Prescription


class PerformanceTester:
    """性能测试工具"""
    
    def __init__(self):
        self.matcher = MedicineMatcher(cache_file="perf_test.json")
        self.matcher.clear_cache()
    
    def test_large_scale_data(self):
        """测试大规模数据处理能力"""
        print("\n" + "="*70)
        print("测试1: 大规模数据处理")
        print("="*70)
        
        # 准备大量追溯码
        num_medicines = 50  # 50种药品
        codes_per_medicine = 100  # 每种药品100个追溯码
        
        print(f"\n准备数据: {num_medicines}种药品, 每种{codes_per_medicine}个追溯码...")
        
        trace_codes = []
        for med_idx in range(num_medicines):
            medicine_name = f"药品{med_idx:03d}"
            for code_idx in range(codes_per_medicine):
                trace_codes.append({
                    "code": f"TC{med_idx:03d}_{code_idx:04d}",
                    "medicine_name": medicine_name,
                    "total_quantity": random.choice([10, 20, 30, 50])
                })
        
        # 批量添加
        start_time = time.time()
        self.matcher.batch_add_trace_codes(trace_codes)
        add_time = time.time() - start_time
        
        print(f"✓ 添加完成: {len(trace_codes)} 个追溯码")
        print(f"  耗时: {add_time:.3f}秒")
        print(f"  平均速度: {len(trace_codes)/add_time:.0f} 个/秒")
        
        # 准备大量医嘱
        num_prescriptions = 1000
        print(f"\n准备 {num_prescriptions} 条医嘱...")
        
        prescriptions = []
        for i in range(num_prescriptions):
            prescriptions.append(Prescription(
                prescription_id=f"RX{i:06d}",
                patient_name=f"患者{i}",
                medicine_name=f"药品{random.randint(0, num_medicines-1):03d}",
                quantity=random.randint(5, 25)
            ))
        
        # 批量匹配
        start_time = time.time()
        results = self.matcher.batch_match_prescriptions(prescriptions, allow_multiple=True)
        match_time = time.time() - start_time
        
        success_count = sum(1 for r in results.values() if r is not None)
        
        print(f"\n✓ 匹配完成:")
        print(f"  耗时: {match_time:.3f}秒")
        print(f"  平均速度: {num_prescriptions/match_time:.0f} 条/秒")
        print(f"  成功率: {success_count/num_prescriptions*100:.1f}%")
        
        return {
            "add_time": add_time,
            "match_time": match_time,
            "success_rate": success_count/num_prescriptions
        }
    
    def test_concurrent_access(self):
        """测试并发访问性能"""
        print("\n" + "="*70)
        print("测试2: 并发访问性能")
        print("="*70)
        
        # 准备数据
        self.matcher.clear_cache()
        trace_codes = []
        for i in range(200):
            trace_codes.append({
                "code": f"CONC{i:04d}",
                "medicine_name": "并发测试药品",
                "total_quantity": 50
            })
        self.matcher.batch_add_trace_codes(trace_codes)
        
        # 准备医嘱
        prescriptions = [
            Prescription(f"RX_CONC_{i:04d}", f"患者{i}", "并发测试药品", 
                        random.randint(5, 15))
            for i in range(100)
        ]
        
        def match_task(prescription):
            """单个匹配任务"""
            return self.matcher.match_prescription(prescription, allow_multiple=True)
        
        # 不同并发级别测试
        for num_threads in [1, 5, 10, 20]:
            print(f"\n并发线程数: {num_threads}")
            
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                results = list(executor.map(match_task, prescriptions))
            elapsed = time.time() - start_time
            
            success = sum(1 for r in results if r is not None)
            
            print(f"  耗时: {elapsed:.3f}秒")
            print(f"  吞吐量: {len(prescriptions)/elapsed:.0f} 条/秒")
            print(f"  成功: {success}/{len(prescriptions)}")
    
    def test_memory_usage(self):
        """测试内存占用"""
        print("\n" + "="*70)
        print("测试3: 内存占用分析")
        print("="*70)
        
        import sys
        
        self.matcher.clear_cache()
        
        # 添加不同规模的数据并测量内存
        scales = [100, 500, 1000, 5000]
        
        for scale in scales:
            self.matcher.clear_cache()
            
            trace_codes = [
                {"code": f"MEM{i:06d}", "medicine_name": f"药品{i%10}", "total_quantity": 20}
                for i in range(scale)
            ]
            
            self.matcher.batch_add_trace_codes(trace_codes)
            
            # 估算内存占用
            size = sys.getsizeof(self.matcher.trace_code_index)
            size += sum(sys.getsizeof(codes) for codes in self.matcher.trace_codes_by_medicine.values())
            
            print(f"\n追溯码数量: {scale}")
            print(f"  估算内存: {size/1024:.2f} KB")
            print(f"  单个追溯码: {size/scale:.0f} bytes")
    
    def test_cache_persistence(self):
        """测试缓存持久化性能"""
        print("\n" + "="*70)
        print("测试4: 缓存持久化性能")
        print("="*70)
        
        self.matcher.clear_cache()
        
        # 添加数据
        num_codes = 1000
        trace_codes = [
            {"code": f"CACHE{i:06d}", "medicine_name": f"药品{i%20}", "total_quantity": 30}
            for i in range(num_codes)
        ]
        
        print(f"\n添加 {num_codes} 个追溯码...")
        self.matcher.batch_add_trace_codes(trace_codes)
        
        # 测试保存性能
        start_time = time.time()
        self.matcher._save_to_cache()
        save_time = time.time() - start_time
        print(f"✓ 保存耗时: {save_time:.3f}秒")
        
        # 测试加载性能
        new_matcher = MedicineMatcher(cache_file="perf_test.json")
        # 加载在初始化时已经完成
        
        # 验证数据完整性
        print(f"✓ 加载验证: {len(new_matcher.trace_code_index)} 个追溯码")


def run_all_tests():
    """运行所有性能测试"""
    tester = PerformanceTester()
    
    print("\n" + "="*70)
    print("药品撮合系统 - 性能测试报告")
    print("="*70)
    
    # 测试1: 大规模数据
    metrics1 = tester.test_large_scale_data()
    
    # 测试2: 并发访问
    tester.test_concurrent_access()
    
    # 测试3: 内存占用
    tester.test_memory_usage()
    
    # 测试4: 缓存持久化
    tester.test_cache_persistence()
    
    # 总结
    print("\n" + "="*70)
    print("性能测试总结")
    print("="*70)
    print("\n✓ 所有测试完成!")
    print("\n建议:")
    print("  1. 对于10万级追溯码,建议配合数据库使用")
    print("  2. 高并发场景建议使用Redis做分布式锁")
    print("  3. 定期清理已用完的追溯码以节省内存")
    print("  4. 缓存文件建议定期备份")


# ============== 优化建议 ==============

def optimization_tips():
    """系统优化建议"""
    print("\n" + "="*70)
    print("系统优化建议")
    print("="*70)
    
    print("""
## 1. 数据库集成优化

建议使用MySQL/PostgreSQL存储核心数据,缓存仅作为加速层:

```python
class DatabaseMatcher(MedicineMatcher):
    def __init__(self, db_connection):
        super().__init__()
        self.db = db_connection
    
    def _save_to_cache(self):
        # 同时保存到数据库
        with self.db.cursor() as cursor:
            for tc in self.trace_code_index.values():
                cursor.execute(
                    "UPDATE trace_codes SET remaining_quantity = %s WHERE code = %s",
                    (tc.remaining_quantity, tc.code)
                )
            self.db.commit()
        super()._save_to_cache()
```

## 2. Redis缓存层

使用Redis提升查询性能:

```python
import redis
import pickle

class RedisMatcher(MedicineMatcher):
    def __init__(self):
        super().__init__()
        self.redis = redis.Redis(host='localhost', port=6379)
    
    def get_medicine_inventory(self, medicine_name):
        # 先查Redis
        cache_key = f"inventory:{medicine_name}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return pickle.loads(cached)
        
        # 缓存未命中,查原始数据
        result = super().get_medicine_inventory(medicine_name)
        self.redis.setex(cache_key, 300, pickle.dumps(result))  # 5分钟过期
        return result
```

## 3. 异步处理

使用消息队列处理批量任务:

```python
import pika

def async_match_worker():
    connection = pika.BlockingConnection()
    channel = connection.channel()
    channel.queue_declare(queue='prescriptions')
    
    matcher = MedicineMatcher()
    
    def callback(ch, method, properties, body):
        prescription_data = json.loads(body)
        prescription = Prescription(**prescription_data)
        
        binding = matcher.match_prescription(prescription)
        
        if binding:
            save_binding_to_his(binding)
        else:
            send_alert(f"医嘱 {prescription.prescription_id} 匹配失败")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(queue='prescriptions', on_message_callback=callback)
    channel.start_consuming()
```

## 4. 分片策略

大规模数据可按药品分片:

```python
class ShardedMatcher:
    def __init__(self, num_shards=10):
        self.shards = [
            MedicineMatcher(cache_file=f"shard_{i}.json")
            for i in range(num_shards)
        ]
    
    def _get_shard(self, medicine_name):
        # 根据药品名称hash到不同分片
        shard_id = hash(medicine_name) % len(self.shards)
        return self.shards[shard_id]
    
    def match_prescription(self, prescription):
        shard = self._get_shard(prescription.medicine_name)
        return shard.match_prescription(prescription)
```

## 5. 监控指标

建议监控以下指标:

- 匹配成功率
- 匹配延迟(P50, P95, P99)
- 库存周转率
- 追溯码利用率
- 系统QPS/TPS

使用Prometheus + Grafana可视化监控。

## 6. 定期清理

```python
def cleanup_job():
    matcher = MedicineMatcher()
    
    # 清理已用完的追溯码
    for medicine_name, codes in matcher.trace_codes_by_medicine.items():
        active = [tc for tc in codes if tc.remaining_quantity > 0]
        matcher.trace_codes_by_medicine[medicine_name] = active
    
    # 归档旧绑定记录(超过30天)
    cutoff_date = datetime.now() - timedelta(days=30)
    archived = {}
    
    for pid, binding in list(matcher.bindings.items()):
        if binding.bind_time < cutoff_date.isoformat():
            archived[pid] = binding
            del matcher.bindings[pid]
    
    # 保存归档
    with open(f"archive_{datetime.now().date()}.json", 'w') as f:
        json.dump(archived, f)
    
    matcher._save_to_cache()
```
    """)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "tips":
        optimization_tips()
    else:
        run_all_tests()
