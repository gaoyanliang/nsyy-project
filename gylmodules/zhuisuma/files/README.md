# 药品追溯码与医嘱撮合系统 - 使用指南

## 系统概述

本系统用于医院药品追溯码与医嘱的自动撮合绑定,支持高并发、数据持久化和多种匹配策略。

### 核心特性

✅ **高效匹配** - 基于药品名称分组索引,O(1)查找复杂度  
✅ **双模式匹配** - 支持单追溯码和多追溯码两种匹配策略  
✅ **数据持久化** - 自动缓存到JSON文件,服务重启后数据不丢失  
✅ **线程安全** - 使用RLock保证并发安全  
✅ **批量处理** - 支持批量添加追溯码和批量匹配医嘱  

---

## 快速开始

### 1. 基础使用

```python
from medicine_matcher import MedicineMatcher, Prescription

# 创建撮合器实例
matcher = MedicineMatcher(cache_file="hospital_cache.json")

# 添加追溯码(从医院HIS系统获取的出入库数据)
matcher.batch_add_trace_codes([
    {"code": "20250205001", "medicine_name": "阿莫西林胶囊", "total_quantity": 24},
    {"code": "20250205002", "medicine_name": "阿莫西林胶囊", "total_quantity": 24},
    {"code": "20250205003", "medicine_name": "布洛芬片", "total_quantity": 12},
])

# 医生开具医嘱
prescription = Prescription(
    prescription_id="RX20250205001",
    patient_name="张三",
    medicine_name="阿莫西林胶囊",
    quantity=10  # 10粒
)

# 执行撮合(单追溯码模式)
binding = matcher.match_prescription(prescription, allow_multiple=False)

if binding:
    print(f"匹配成功: {binding.trace_codes}")
else:
    print("库存不足或无匹配追溯码")
```

### 2. 批量处理(适合定时任务)

```python
# 每天定时从HIS系统拉取当日医嘱
prescriptions = [
    Prescription("RX001", "患者A", "阿莫西林胶囊", 10),
    Prescription("RX002", "患者B", "阿莫西林胶囊", 6),
    Prescription("RX003", "患者C", "布洛芬片", 8),
    # ... 更多医嘱
]

# 批量匹配
results = matcher.batch_match_prescriptions(prescriptions, allow_multiple=True)

# 处理结果
for prescription_id, binding in results.items():
    if binding:
        # 匹配成功,可以将绑定关系写回数据库
        print(f"{prescription_id}: 成功绑定 {binding.trace_codes}")
    else:
        # 匹配失败,需要人工处理或报警
        print(f"{prescription_id}: 库存不足,匹配失败")
```

---

## 两种匹配模式详解

### 模式1: 单追溯码匹配 (allow_multiple=False)

**策略**: 只绑定一个追溯码,选择剩余数量>=需求且最接近需求的追溯码

**适用场景**: 
- 医院要求严格的一盒一医嘱管理
- 追溯码管理规范要求单一绑定

**示例**:
```
库存: A001(10粒), A002(20粒), A003(50粒)
需求: 15粒

结果: 选择A002(20粒),因为它最接近15粒
      A002剩余: 5粒
```

### 模式2: 多追溯码匹配 (allow_multiple=True)

**策略**: 可绑定多个追溯码,优先用完快用完的追溯码(FIFO原则)

**适用场景**:
- 允许跨盒发药
- 需要快速消耗库存避免过期

**示例**:
```
库存: A001(4粒), A002(10粒), A003(50粒)
需求: 15粒

结果: 先用A001(4粒) + A002(10粒) + A003(1粒)
      A001剩余: 0粒
      A002剩余: 0粒
      A003剩余: 49粒
```

---

## 核心API参考

### MedicineMatcher 类

#### 初始化
```python
matcher = MedicineMatcher(cache_file="cache.json")
```

#### 添加追溯码
```python
# 单个添加
matcher.add_trace_code(
    code="追溯码",
    medicine_name="药品名称",
    total_quantity=数量
)

# 批量添加(推荐)
matcher.batch_add_trace_codes([
    {"code": "001", "medicine_name": "药品A", "total_quantity": 10},
    {"code": "002", "medicine_name": "药品A", "total_quantity": 10},
])
```

#### 匹配医嘱
```python
# 单个匹配
binding = matcher.match_prescription(prescription, allow_multiple=False)

# 批量匹配
results = matcher.batch_match_prescriptions(prescriptions, allow_multiple=True)
```

#### 查询功能
```python
# 查询追溯码状态
status = matcher.get_trace_code_status("001")

# 查询医嘱绑定关系
binding = matcher.get_binding("RX001")

# 查询药品库存
inventory = matcher.get_medicine_inventory("阿莫西林胶囊")
```

---

## 集成方案建议

### 方案1: 定时任务模式(推荐)

```python
import schedule
import time
from medicine_matcher import MedicineMatcher, Prescription

def daily_match_job():
    """每天凌晨1点执行匹配任务"""
    matcher = MedicineMatcher(cache_file="/data/matcher_cache.json")
    
    # 1. 从HIS系统获取昨日出入库追溯码
    trace_codes = fetch_trace_codes_from_his()
    matcher.batch_add_trace_codes(trace_codes)
    
    # 2. 从HIS系统获取昨日医嘱
    prescriptions = fetch_prescriptions_from_his()
    
    # 3. 批量匹配
    results = matcher.batch_match_prescriptions(prescriptions, allow_multiple=True)
    
    # 4. 将匹配结果写回HIS数据库
    save_bindings_to_his(results)
    
    print(f"匹配完成: {len([r for r in results.values() if r])} 条成功")

# 设置定时任务
schedule.every().day.at("01:00").do(daily_match_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 方案2: 实时匹配模式

```python
# Flask API示例
from flask import Flask, request, jsonify
from medicine_matcher import MedicineMatcher, Prescription

app = Flask(__name__)
matcher = MedicineMatcher(cache_file="/data/matcher_cache.json")

@app.route('/api/match', methods=['POST'])
def match_prescription():
    """实时匹配接口"""
    data = request.json
    
    prescription = Prescription(
        prescription_id=data['prescription_id'],
        patient_name=data['patient_name'],
        medicine_name=data['medicine_name'],
        quantity=data['quantity']
    )
    
    binding = matcher.match_prescription(
        prescription, 
        allow_multiple=data.get('allow_multiple', False)
    )
    
    if binding:
        return jsonify({
            "success": True,
            "binding": {
                "prescription_id": binding.prescription_id,
                "trace_codes": binding.trace_codes
            }
        })
    else:
        return jsonify({
            "success": False,
            "error": "库存不足或无匹配追溯码"
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## 性能优化建议

### 1. 内存管理
```python
# 定期清理已完全用完的追溯码
def cleanup_empty_codes(matcher):
    """清理剩余量为0的追溯码(可选)"""
    for medicine_name, codes in matcher.trace_codes_by_medicine.items():
        active_codes = [tc for tc in codes if tc.remaining_quantity > 0]
        matcher.trace_codes_by_medicine[medicine_name] = active_codes
```

### 2. 数据库集成
```python
# 配合数据库使用,缓存仅作为加速层
class DatabaseMatcher(MedicineMatcher):
    def _save_to_cache(self):
        """重写保存方法,同时保存到数据库"""
        super()._save_to_cache()
        # 保存到数据库
        save_to_database(self.trace_code_index, self.bindings)
    
    def _load_from_cache(self):
        """优先从数据库加载"""
        try:
            load_from_database()
        except:
            super()._load_from_cache()
```

### 3. 并发控制
```python
# 使用Redis分布式锁(多服务器部署时)
import redis
from redis.lock import Lock

redis_client = redis.Redis()

def match_with_distributed_lock(matcher, prescription):
    lock = Lock(redis_client, "matcher_lock", timeout=5)
    
    if lock.acquire(blocking=True):
        try:
            return matcher.match_prescription(prescription)
        finally:
            lock.release()
```

---

## 常见问题 FAQ

### Q1: 服务重启后数据会丢失吗?
**A**: 不会。所有数据自动保存在JSON文件中,重启后会自动加载。

### Q2: 如何处理追溯码过期?
**A**: 可以在TraceCode中添加过期时间字段,匹配时过滤掉过期的追溯码。

### Q3: 支持并发吗?
**A**: 支持。使用了RLock线程锁,单进程多线程安全。多进程需要配合数据库或Redis。

### Q4: 如何回滚匹配?
**A**: 当前版本需要手动实现。可以记录操作日志,然后恢复追溯码的remaining_quantity。

### Q5: 匹配算法的时间复杂度?
**A**: 
- 单追溯码: O(n log n), n为该药品的追溯码数量
- 多追溯码: O(n), 贪心算法

---

## 监控指标建议

```python
def get_system_metrics(matcher):
    """获取系统运行指标"""
    total_codes = len(matcher.trace_code_index)
    total_bindings = len(matcher.bindings)
    
    # 统计各药品库存
    medicine_stats = {}
    for medicine_name, codes in matcher.trace_codes_by_medicine.items():
        total_qty = sum(tc.remaining_quantity for tc in codes)
        medicine_stats[medicine_name] = {
            "trace_codes": len(codes),
            "remaining_quantity": total_qty
        }
    
    return {
        "total_trace_codes": total_codes,
        "total_bindings": total_bindings,
        "medicines": medicine_stats
    }
```

---

## 总结

本系统提供了简单高效的药品追溯码撮合方案,适合中小型医院直接使用。对于大型医院,建议配合数据库和消息队列构建完整的追溯系统。
