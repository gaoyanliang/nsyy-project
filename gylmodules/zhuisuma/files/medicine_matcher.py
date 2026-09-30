"""
药品追溯码与医嘱撮合绑定系统
支持高效匹配、缓存管理、数据持久化
"""

import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime
import threading

"""追溯码数据结构"""

@dataclass
class TraceCode:
    code: str  # 追溯码
    medicine_name: str  # 药品名称
    total_quantity: int  # 总数量(粒/颗)
    remaining_quantity: int  # 剩余数量
    created_at: str = None  # 创建时间
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


"""医嘱数据结构"""

@dataclass
class Prescription:
    prescription_id: str  # 医嘱ID
    patient_name: str  # 患者姓名
    medicine_name: str  # 药品名称
    quantity: int  # 需要数量(粒/颗)
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


"""绑定关系数据结构"""


@dataclass
class Binding:
    prescription_id: str  # 医嘱ID
    trace_codes: List[Dict]  # 绑定的追溯码列表 [{"code": "001", "used_quantity": 6}, ...]
    bind_time: str = None
    
    def __post_init__(self):
        if self.bind_time is None:
            self.bind_time = datetime.now().isoformat()


"""药品追溯码撮合器"""


class MedicineMatcher:
    """
    初始化撮合器

    Args:
        cache_file: 缓存文件路径,用于持久化
    """
    def __init__(self, cache_file: str = "matcher_cache.json"):
        self.cache_file = cache_file
        self.lock = threading.RLock()  # 线程安全锁
        
        # 核心数据结构 - 按药品名称分组的追溯码字典
        # 结构: {药品名称: [TraceCode1, TraceCode2, ...]}
        self.trace_codes_by_medicine: Dict[str, List[TraceCode]] = defaultdict(list)
        
        # 追溯码索引 - 快速查找
        # 结构: {追溯码: TraceCode}
        self.trace_code_index: Dict[str, TraceCode] = {}
        
        # 绑定关系记录
        # 结构: {医嘱ID: Binding}
        self.bindings: Dict[str, Binding] = {}
        
        # 从缓存文件加载数据
        self._load_from_cache()

    """
    添加追溯码到池中

    Args:
        code: 追溯码
        medicine_name: 药品名称
        total_quantity: 总数量(粒)
    """
    def add_trace_code(self, code: str, medicine_name: str, total_quantity: int):
        with self.lock:
            # 检查是否已存在
            if code in self.trace_code_index:
                print(f"追溯码 {code} 已存在,跳过添加")
                return
            
            trace_code = TraceCode(
                code=code,
                medicine_name=medicine_name,
                total_quantity=total_quantity,
                remaining_quantity=total_quantity
            )
            
            self.trace_codes_by_medicine[medicine_name].append(trace_code)
            self.trace_code_index[code] = trace_code
            
            # 按剩余数量降序排序,优先使用数量多的
            self.trace_codes_by_medicine[medicine_name].sort(
                key=lambda x: x.remaining_quantity, 
                reverse=True
            )

    """
    批量添加追溯码

    Args:
        trace_codes: 追溯码列表 [{"code": "001", "medicine_name": "药品A", "total_quantity": 10}, ...]
    """
    def batch_add_trace_codes(self, trace_codes: List[Dict]):
        for tc in trace_codes:
            self.add_trace_code(tc['code'], tc['medicine_name'], tc['total_quantity'])
        self._save_to_cache()


    """
    单追溯码匹配模式 - 只绑定一个追溯码
    找到剩余数量>=需求数量的最小追溯码

    Args:
        prescription: 医嘱对象

    Returns:
        Binding对象或None
    """
    def match_single_code(self, prescription: Prescription) -> Optional[Binding]:
        with self.lock:
            medicine_name = prescription.medicine_name
            needed_quantity = prescription.quantity
            
            # 获取该药品的所有追溯码
            available_codes = self.trace_codes_by_medicine.get(medicine_name, [])
            
            # 筛选出剩余数量足够的追溯码
            suitable_codes = [
                tc for tc in available_codes 
                if tc.remaining_quantity >= needed_quantity
            ]
            
            if not suitable_codes:
                return None
            
            # 选择剩余数量最接近需求的追溯码(最优分配)
            best_code = min(suitable_codes, key=lambda x: x.remaining_quantity)
            
            # 扣减数量
            best_code.remaining_quantity -= needed_quantity
            
            # 创建绑定关系
            binding = Binding(
                prescription_id=prescription.prescription_id,
                trace_codes=[{
                    "code": best_code.code,
                    "used_quantity": needed_quantity
                }]
            )
            
            self.bindings[prescription.prescription_id] = binding
            
            # 重新排序
            self.trace_codes_by_medicine[medicine_name].sort(
                key=lambda x: x.remaining_quantity, 
                reverse=True
            )
            
            return binding


    """
    多追溯码匹配模式 - 可以绑定多个追溯码
    优先使用剩余数量少的追溯码(先进先出原则)

    Args:
        prescription: 医嘱对象

    Returns:
        Binding对象或None
    """
    def match_multiple_codes(self, prescription: Prescription) -> Optional[Binding]:
        with self.lock:
            medicine_name = prescription.medicine_name
            needed_quantity = prescription.quantity
            
            # 获取该药品的所有追溯码
            available_codes = self.trace_codes_by_medicine.get(medicine_name, [])
            
            # 按剩余数量升序排序,优先用完快用完的
            available_codes_sorted = sorted(
                [tc for tc in available_codes if tc.remaining_quantity > 0],
                key=lambda x: x.remaining_quantity
            )
            
            if not available_codes_sorted:
                return None
            
            # 贪心算法: 从剩余量少的开始分配
            remaining_needed = needed_quantity
            used_codes = []
            
            for trace_code in available_codes_sorted:
                if remaining_needed <= 0:
                    break
                
                # 计算本次使用数量
                use_quantity = min(trace_code.remaining_quantity, remaining_needed)
                
                # 记录使用情况
                used_codes.append({
                    "code": trace_code.code,
                    "used_quantity": use_quantity
                })
                
                # 扣减
                trace_code.remaining_quantity -= use_quantity
                remaining_needed -= use_quantity
            
            # 检查是否满足需求
            if remaining_needed > 0:
                # 回滚扣减
                for used in used_codes:
                    code = used["code"]
                    self.trace_code_index[code].remaining_quantity += used["used_quantity"]
                return None
            
            # 创建绑定关系
            binding = Binding(
                prescription_id=prescription.prescription_id,
                trace_codes=used_codes
            )
            
            self.bindings[prescription.prescription_id] = binding
            
            # 重新排序
            self.trace_codes_by_medicine[medicine_name].sort(
                key=lambda x: x.remaining_quantity, 
                reverse=True
            )
            
            return binding


    """
    撮合医嘱与追溯码

    Args:
        prescription: 医嘱对象
        allow_multiple: 是否允许绑定多个追溯码

    Returns:
        Binding对象或None
    """
    def match_prescription(self, prescription: Prescription, 
                          allow_multiple: bool = False) -> Optional[Binding]:
        if allow_multiple:
            binding = self.match_multiple_codes(prescription)
        else:
            binding = self.match_single_code(prescription)
        
        if binding:
            self._save_to_cache()
        
        return binding

    """
    批量撮合医嘱

    Args:
        prescriptions: 医嘱列表
        allow_multiple: 是否允许绑定多个追溯码

    Returns:
        {医嘱ID: Binding或None}
    """
    def batch_match_prescriptions(self, prescriptions: List[Prescription], 
                                  allow_multiple: bool = False) -> Dict[str, Optional[Binding]]:
        results = {}
        for prescription in prescriptions:
            binding = self.match_prescription(prescription, allow_multiple)
            results[prescription.prescription_id] = binding
        
        return results

    """
    查询追溯码状态

    Args:
        code: 追溯码

    Returns:
        追溯码信息字典
    """
    def get_trace_code_status(self, code: str) -> Optional[Dict]:
        with self.lock:
            trace_code = self.trace_code_index.get(code)
            if trace_code:
                return asdict(trace_code)
            return None
    
    def get_binding(self, prescription_id: str) -> Optional[Binding]:
        """
        查询医嘱绑定关系
        
        Args:
            prescription_id: 医嘱ID
            
        Returns:
            Binding对象或None
        """
        with self.lock:
            return self.bindings.get(prescription_id)
    
    def get_medicine_inventory(self, medicine_name: str) -> Dict:
        """
        查询某药品的库存情况
        
        Args:
            medicine_name: 药品名称
            
        Returns:
            库存统计信息
        """
        with self.lock:
            codes = self.trace_codes_by_medicine.get(medicine_name, [])
            total_remaining = sum(tc.remaining_quantity for tc in codes)
            
            return {
                "medicine_name": medicine_name,
                "total_trace_codes": len(codes),
                "available_trace_codes": len([tc for tc in codes if tc.remaining_quantity > 0]),
                "total_remaining_quantity": total_remaining,
                "trace_codes": [asdict(tc) for tc in codes]
            }
    
    def _save_to_cache(self):
        """保存数据到缓存文件"""
        try:
            cache_data = {
                "trace_codes": [
                    asdict(tc) 
                    for codes in self.trace_codes_by_medicine.values() 
                    for tc in codes
                ],
                "bindings": {
                    pid: asdict(binding) 
                    for pid, binding in self.bindings.items()
                }
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def _load_from_cache(self):
        """从缓存文件加载数据"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 恢复追溯码
            for tc_data in cache_data.get("trace_codes", []):
                trace_code = TraceCode(**tc_data)
                self.trace_codes_by_medicine[trace_code.medicine_name].append(trace_code)
                self.trace_code_index[trace_code.code] = trace_code
            
            # 排序
            for medicine_name in self.trace_codes_by_medicine:
                self.trace_codes_by_medicine[medicine_name].sort(
                    key=lambda x: x.remaining_quantity, 
                    reverse=True
                )
            
            # 恢复绑定关系
            for pid, binding_data in cache_data.get("bindings", {}).items():
                self.bindings[pid] = Binding(**binding_data)
            
            print(f"从缓存加载数据成功: {len(self.trace_code_index)} 个追溯码, {len(self.bindings)} 个绑定")
        except FileNotFoundError:
            print("缓存文件不存在,使用空数据初始化")
        except Exception as e:
            print(f"加载缓存失败: {e}")
    
    def clear_cache(self):
        """清空缓存(谨慎使用)"""
        with self.lock:
            self.trace_codes_by_medicine.clear()
            self.trace_code_index.clear()
            self.bindings.clear()
            self._save_to_cache()


# ==================== 使用示例 ====================

def example_usage():
    """使用示例"""
    
    # 创建撮合器
    matcher = MedicineMatcher(cache_file="medicine_cache.json")
    
    print("=" * 60)
    print("示例: 药品追溯码撮合系统")
    print("=" * 60)
    
    # 1. 批量添加追溯码
    print("\n[步骤1] 添加追溯码到池中")
    trace_codes = [
        {"code": "001", "medicine_name": "药品A", "total_quantity": 10},
        {"code": "002", "medicine_name": "药品A", "total_quantity": 10},
        {"code": "003", "medicine_name": "药品B", "total_quantity": 20},
    ]
    matcher.batch_add_trace_codes(trace_codes)
    print(f"已添加 {len(trace_codes)} 个追溯码")
    
    # 2. 查看库存
    print("\n[步骤2] 查看药品A库存")
    inventory = matcher.get_medicine_inventory("药品A")
    print(f"药品A总库存: {inventory['total_remaining_quantity']} 粒")
    
    # 3. 单追溯码匹配
    print("\n[步骤3] 单追溯码匹配 - 患者A开6粒药品A")
    prescription_a = Prescription(
        prescription_id="P001",
        patient_name="患者A",
        medicine_name="药品A",
        quantity=6
    )
    binding_a = matcher.match_prescription(prescription_a, allow_multiple=False)
    if binding_a:
        print(f"✓ 匹配成功: {binding_a.trace_codes}")
        status = matcher.get_trace_code_status(binding_a.trace_codes[0]['code'])
        print(f"  追溯码 {status['code']} 剩余: {status['remaining_quantity']} 粒")
    
    # 4. 多追溯码匹配
    print("\n[步骤4] 多追溯码匹配 - 患者B开6粒药品A")
    prescription_b = Prescription(
        prescription_id="P002",
        patient_name="患者B",
        medicine_name="药品A",
        quantity=6
    )
    binding_b = matcher.match_prescription(prescription_b, allow_multiple=True)
    if binding_b:
        print(f"✓ 匹配成功: {binding_b.trace_codes}")
        for used in binding_b.trace_codes:
            status = matcher.get_trace_code_status(used['code'])
            print(f"  追溯码 {status['code']} 使用 {used['used_quantity']} 粒, 剩余: {status['remaining_quantity']} 粒")
    
    # 5. 查看最终库存
    print("\n[步骤5] 查看最终库存")
    inventory = matcher.get_medicine_inventory("药品A")
    print(f"药品A总库存: {inventory['total_remaining_quantity']} 粒")
    for tc in inventory['trace_codes']:
        print(f"  - {tc['code']}: {tc['remaining_quantity']}/{tc['total_quantity']} 粒")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    example_usage()
