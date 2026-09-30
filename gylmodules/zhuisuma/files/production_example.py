"""
生产环境集成示例
演示如何将撮合系统集成到医院HIS系统中
"""

import json
from datetime import datetime
from typing import List, Dict
from medicine_matcher import MedicineMatcher, Prescription


# ============== 模拟HIS系统数据接口 ==============

def fetch_daily_trace_codes() -> List[Dict]:
    """
    从HIS系统获取当日出入库的追溯码数据
    
    实际场景中,这个函数应该连接HIS数据库查询:
    SELECT trace_code, medicine_name, specification, quantity 
    FROM drug_inventory 
    WHERE operation_date = CURRENT_DATE AND operation_type = 'IN'
    """
    # 模拟数据
    return [
        {
            "code": "TC20250205001",
            "medicine_name": "阿莫西林胶囊",
            "total_quantity": 24,  # 24粒/盒
        },
        {
            "code": "TC20250205002",
            "medicine_name": "阿莫西林胶囊",
            "total_quantity": 24,
        },
        {
            "code": "TC20250205003",
            "medicine_name": "布洛芬片",
            "total_quantity": 12,  # 12片/盒
        },
        {
            "code": "TC20250205004",
            "medicine_name": "头孢克肟胶囊",
            "total_quantity": 12,
        },
    ]


def fetch_daily_prescriptions() -> List[Dict]:
    """
    从HIS系统获取当日医嘱数据
    
    实际场景中:
    SELECT prescription_id, patient_name, medicine_name, quantity
    FROM prescriptions
    WHERE prescription_date = CURRENT_DATE AND status = 'PENDING'
    """
    # 模拟数据
    return [
        {
            "prescription_id": "RX20250205001",
            "patient_name": "张三",
            "medicine_name": "阿莫西林胶囊",
            "quantity": 18,
        },
        {
            "prescription_id": "RX20250205002",
            "patient_name": "李四",
            "medicine_name": "阿莫西林胶囊",
            "quantity": 12,
        },
        {
            "prescription_id": "RX20250205003",
            "patient_name": "王五",
            "medicine_name": "布洛芬片",
            "quantity": 8,
        },
        {
            "prescription_id": "RX20250205004",
            "patient_name": "赵六",
            "medicine_name": "头孢克肟胶囊",
            "quantity": 10,
        },
    ]


def save_binding_to_his(binding_data: Dict) -> bool:
    """
    将绑定关系保存到HIS数据库
    
    实际场景中:
    INSERT INTO prescription_trace_binding 
    (prescription_id, trace_code, used_quantity, bind_time)
    VALUES (?, ?, ?, ?)
    """
    print(f"  → 保存绑定关系到HIS数据库: {binding_data['prescription_id']}")
    # 这里应该是实际的数据库INSERT操作
    return True


def send_alert(message: str):
    """发送告警通知"""
    print(f"  ⚠️  告警: {message}")
    # 实际应该调用企业微信、钉钉或短信接口


# ============== 核心业务逻辑 ==============

class HospitalMedicineManager:
    """医院药品撮合管理器"""
    
    def __init__(self, cache_file: str = "/data/matcher_cache.json"):
        self.matcher = MedicineMatcher(cache_file=cache_file)
        self.allow_multiple = True  # 是否允许跨盒配药
    
    def daily_sync_and_match(self):
        """每日同步与撮合任务"""
        print("\n" + "="*70)
        print(f"开始每日撮合任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 步骤1: 同步追溯码
        print("\n[步骤1] 从HIS系统同步当日追溯码...")
        trace_codes = fetch_daily_trace_codes()
        self.matcher.batch_add_trace_codes(trace_codes)
        print(f"  ✓ 同步完成: {len(trace_codes)} 个追溯码")
        
        # 步骤2: 获取医嘱
        print("\n[步骤2] 从HIS系统获取当日医嘱...")
        prescription_data = fetch_daily_prescriptions()
        print(f"  ✓ 获取完成: {len(prescription_data)} 条医嘱")
        
        # 步骤3: 转换为Prescription对象
        prescriptions = [
            Prescription(
                prescription_id=p['prescription_id'],
                patient_name=p['patient_name'],
                medicine_name=p['medicine_name'],
                quantity=p['quantity']
            )
            for p in prescription_data
        ]
        
        # 步骤4: 批量撮合
        print(f"\n[步骤3] 执行撮合匹配(allow_multiple={self.allow_multiple})...")
        results = self.matcher.batch_match_prescriptions(
            prescriptions, 
            allow_multiple=self.allow_multiple
        )
        
        # 步骤5: 处理结果
        print("\n[步骤4] 处理撮合结果...")
        success_count = 0
        fail_count = 0
        
        for prescription_id, binding in results.items():
            if binding:
                # 保存绑定关系到HIS
                binding_data = {
                    "prescription_id": binding.prescription_id,
                    "trace_codes": binding.trace_codes,
                    "bind_time": binding.bind_time
                }
                save_binding_to_his(binding_data)
                success_count += 1
            else:
                # 匹配失败,发送告警
                prescription = next(p for p in prescriptions if p.prescription_id == prescription_id)
                send_alert(
                    f"医嘱 {prescription_id} 匹配失败 - "
                    f"患者: {prescription.patient_name}, "
                    f"药品: {prescription.medicine_name}, "
                    f"需求: {prescription.quantity}粒"
                )
                fail_count += 1
        
        # 步骤6: 生成报告
        print("\n[步骤5] 生成撮合报告...")
        self._generate_report(success_count, fail_count)
        
        print("\n" + "="*70)
        print("撮合任务完成")
        print("="*70 + "\n")
    
    def _generate_report(self, success_count: int, fail_count: int):
        """生成撮合报告"""
        print("\n" + "-"*70)
        print("撮合结果统计:")
        print(f"  ✓ 成功: {success_count} 条")
        print(f"  ❌ 失败: {fail_count} 条")
        print(f"  成功率: {success_count/(success_count+fail_count)*100:.1f}%")
        print("-"*70)
        
        # 库存预警
        print("\n库存情况:")
        all_medicines = set(
            tc.medicine_name 
            for codes in self.matcher.trace_codes_by_medicine.values() 
            for tc in codes
        )
        
        for medicine_name in all_medicines:
            inv = self.matcher.get_medicine_inventory(medicine_name)
            print(f"  {medicine_name}: {inv['total_remaining_quantity']}粒 "
                  f"({inv['available_trace_codes']}个可用追溯码)")
            
            # 库存不足预警
            if inv['total_remaining_quantity'] < 20:
                send_alert(f"{medicine_name} 库存不足! 仅剩 {inv['total_remaining_quantity']}粒")
    
    def real_time_match(self, prescription_data: Dict) -> Dict:
        """
        实时撮合接口(供药房实时调用)
        
        Args:
            prescription_data: {"prescription_id": "RX001", "patient_name": "张三", ...}
        
        Returns:
            {"success": True/False, "binding": {...}, "error": "..."}
        """
        prescription = Prescription(
            prescription_id=prescription_data['prescription_id'],
            patient_name=prescription_data['patient_name'],
            medicine_name=prescription_data['medicine_name'],
            quantity=prescription_data['quantity']
        )
        
        binding = self.matcher.match_prescription(
            prescription, 
            allow_multiple=self.allow_multiple
        )
        
        if binding:
            # 保存到HIS
            save_binding_to_his({
                "prescription_id": binding.prescription_id,
                "trace_codes": binding.trace_codes,
                "bind_time": binding.bind_time
            })
            
            return {
                "success": True,
                "binding": {
                    "prescription_id": binding.prescription_id,
                    "trace_codes": binding.trace_codes
                }
            }
        else:
            return {
                "success": False,
                "error": "库存不足或无可用追溯码"
            }
    
    def query_inventory(self, medicine_name: str) -> Dict:
        """查询药品库存"""
        return self.matcher.get_medicine_inventory(medicine_name)


# ============== 使用示例 ==============

def example_daily_task():
    """示例: 每日定时任务"""
    manager = HospitalMedicineManager(cache_file="hospital_prod.json")
    manager.daily_sync_and_match()


def example_real_time_api():
    """示例: 实时API调用"""
    print("\n" + "="*70)
    print("实时撮合API示例")
    print("="*70)
    
    manager = HospitalMedicineManager(cache_file="hospital_api.json")
    
    # 先添加一些库存
    manager.matcher.batch_add_trace_codes([
        {"code": "API001", "medicine_name": "速效救心丸", "total_quantity": 30},
    ])
    
    # 模拟API调用
    print("\n[API请求] 患者需要速效救心丸 15粒")
    result = manager.real_time_match({
        "prescription_id": "RX_API_001",
        "patient_name": "急诊患者",
        "medicine_name": "速效救心丸",
        "quantity": 15
    })
    
    print(f"[API响应] {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 查询库存
    print("\n[API请求] 查询速效救心丸库存")
    inventory = manager.query_inventory("速效救心丸")
    print(f"[API响应] 剩余库存: {inventory['total_remaining_quantity']}粒")


def example_with_schedule():
    """示例: 使用schedule库实现定时任务"""
    print("\n" + "="*70)
    print("定时任务调度示例")
    print("="*70)
    print("\n建议安装: pip install schedule")
    print("\n示例代码:")
    print("""
import schedule
import time

def job():
    manager = HospitalMedicineManager()
    manager.daily_sync_and_match()

# 每天凌晨1点执行
schedule.every().day.at("01:00").do(job)

# 或者每小时执行一次
# schedule.every().hour.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
    """)


if __name__ == "__main__":
    print("\n选择运行示例:")
    print("1. 每日定时任务示例")
    print("2. 实时API示例")
    print("3. 定时调度说明")
    
    choice = input("\n请输入选项(1/2/3): ").strip()
    
    if choice == "1":
        example_daily_task()
    elif choice == "2":
        example_real_time_api()
    elif choice == "3":
        example_with_schedule()
    else:
        print("默认运行每日任务示例")
        example_daily_task()
