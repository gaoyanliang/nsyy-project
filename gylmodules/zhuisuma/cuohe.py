from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import itertools


@dataclass
class TraceCode:
    """追溯码实体"""
    code: str  # 追溯码
    drug_name: str  # 药品名称
    specification: str  # 规格描述
    total_quantity: int  # 总数量（粒/颗）
    used_quantity: int = 0  # 已使用数量
    batch_id: Optional[str] = None  # 批次号
    expiration_date: Optional[str] = None  # 有效期

    @property
    def remaining_quantity(self) -> int:
        """剩余数量"""
        return self.total_quantity - self.used_quantity

    @property
    def is_available(self) -> bool:
        """是否还有剩余"""
        return self.remaining_quantity > 0

    def use_quantity(self, quantity: int) -> Tuple[int, int]:
        """
        使用一定数量的药品
        返回：(实际使用数量, 剩余需要数量)
        """
        if quantity <= 0:
            return 0, 0

        available = self.remaining_quantity
        if available >= quantity:
            self.used_quantity += quantity
            return quantity, 0
        else:
            self.used_quantity = self.total_quantity
            return available, quantity - available


@dataclass
class MedicalOrder:
    """医嘱实体"""
    order_id: str  # 医嘱ID
    patient_id: str  # 患者ID
    patient_name: str  # 患者姓名
    drug_name: str  # 药品名称
    required_quantity: int  # 需要数量（粒/颗）
    status: str = "pending"  # 状态：pending, matched, completed

    def __post_init__(self):
        if self.required_quantity <= 0:
            raise ValueError("药品数量必须大于0")


class TraceCodePool:
    """追溯码池管理"""

    def __init__(self):
        self.trace_codes: Dict[str, TraceCode] = {}  # code -> TraceCode
        self.drug_trace_map: Dict[str, List[TraceCode]] = {}  # drug_name -> List[TraceCode]

    def add_trace_code(self, trace_code: TraceCode):
        """添加追溯码到池中"""
        self.trace_codes[trace_code.code] = trace_code

        # 按药品名称索引
        if trace_code.drug_name not in self.drug_trace_map:
            self.drug_trace_map[trace_code.drug_name] = []
        self.drug_trace_map[trace_code.drug_name].append(trace_code)

    def get_available_codes_by_drug(self, drug_name: str) -> List[TraceCode]:
        """获取指定药品的可用追溯码（按剩余数量排序）"""
        if drug_name not in self.drug_trace_map:
            return []

        # 过滤可用并排序：剩余多的在前
        available_codes = [
            code for code in self.drug_trace_map[drug_name]
            if code.is_available
        ]
        available_codes.sort(key=lambda x: x.remaining_quantity, reverse=True)
        return available_codes

    def get_trace_code(self, code: str) -> Optional[TraceCode]:
        """根据追溯码获取信息"""
        return self.trace_codes.get(code)

    def reset_usage(self):
        """重置所有追溯码使用状态（用于测试或重新分配）"""
        for code in self.trace_codes.values():
            code.used_quantity = 0


class MedicationMatcher:
    """药品追溯码匹配器"""

    def __init__(self, allow_multiple_codes: bool = True):
        """
        初始化匹配器
        :param allow_multiple_codes: 是否允许一个医嘱绑定多个追溯码
        """
        self.pool = TraceCodePool()
        self.allow_multiple_codes = allow_multiple_codes

    def load_trace_codes(self, trace_codes: List[TraceCode]):
        """加载追溯码到池中"""
        for code in trace_codes:
            self.pool.add_trace_code(code)

    def match_single_order_single_code(self, order: MedicalOrder) -> Optional[Dict]:
        """
        为单个医嘱匹配单个追溯码（最优匹配）
        优先选择剩余量最接近的追溯码
        """
        available_codes = self.pool.get_available_codes_by_drug(order.drug_name)
        if not available_codes:
            return None

        # 找到剩余量足够的追溯码
        sufficient_codes = [
            code for code in available_codes
            if code.remaining_quantity >= order.required_quantity
        ]

        if sufficient_codes:
            # 选择剩余量最少的（避免浪费）
            best_code = min(sufficient_codes, key=lambda x: x.remaining_quantity)
            used, remaining = best_code.use_quantity(order.required_quantity)

            return {
                "order_id": order.order_id,
                "patient_id": order.patient_id,
                "patient_name": order.patient_name,
                "drug_name": order.drug_name,
                "required_quantity": order.required_quantity,
                "matched_quantity": used,
                "remaining_in_order": remaining,
                "trace_codes": [
                    {
                        "code": best_code.code,
                        "specification": best_code.specification,
                        "used_quantity": used,
                        "remaining_in_code": best_code.remaining_quantity,
                        "batch_id": best_code.batch_id,
                        "expiration_date": best_code.expiration_date
                    }
                ],
                "strategy": "single_code"
            }

        return None

    def match_single_order_multiple_codes(self, order: MedicalOrder) -> Optional[Dict]:
        """
        为单个医嘱匹配多个追溯码（组合匹配）
        使用贪心算法：优先使用剩余量多的追溯码
        """
        available_codes = self.pool.get_available_codes_by_drug(order.drug_name)
        if not available_codes:
            return None

        remaining_quantity = order.required_quantity
        matched_codes = []

        # 贪心算法：每次选择剩余最多的追溯码
        for code in available_codes:
            if remaining_quantity <= 0:
                break

            if code.remaining_quantity > 0:
                used, remaining_quantity = code.use_quantity(remaining_quantity)
                if used > 0:
                    matched_codes.append({
                        "code": code.code,
                        "specification": code.specification,
                        "used_quantity": used,
                        "remaining_in_code": code.remaining_quantity,
                        "batch_id": code.batch_id,
                        "expiration_date": code.expiration_date
                    })

        if remaining_quantity == 0 and matched_codes:
            return {
                "order_id": order.order_id,
                "patient_id": order.patient_id,
                "patient_name": order.patient_name,
                "drug_name": order.drug_name,
                "required_quantity": order.required_quantity,
                "matched_quantity": order.required_quantity,
                "remaining_in_order": 0,
                "trace_codes": matched_codes,
                "strategy": "multiple_codes"
            }

        # 如果未能完全匹配，回滚使用量
        for code_info in matched_codes:
            code = self.pool.get_trace_code(code_info["code"])
            if code:
                code.used_quantity -= code_info["used_quantity"]

        return None

    def match_order(self, order: MedicalOrder) -> Optional[Dict]:
        """
        匹配单个医嘱（根据策略选择匹配方式）
        """
        # 先尝试单追溯码匹配
        result = self.match_single_order_single_code(order)

        # 如果单追溯码匹配失败且允许多追溯码匹配
        if not result and self.allow_multiple_codes:
            result = self.match_single_order_multiple_codes(order)

        if result:
            order.status = "matched"

        return result

    def batch_match_orders(self, orders: List[MedicalOrder],
                           priority_strategy: str = "fifo") -> List[Dict]:
        """
        批量匹配医嘱
        :param orders: 医嘱列表
        :param priority_strategy: 优先级策略
            - fifo: 先到先得（按顺序）
            - largest_first: 需求量大的优先
            - smallest_first: 需求量小的优先
        """
        # 根据策略排序医嘱
        if priority_strategy == "largest_first":
            sorted_orders = sorted(orders, key=lambda x: x.required_quantity, reverse=True)
        elif priority_strategy == "smallest_first":
            sorted_orders = sorted(orders, key=lambda x: x.required_quantity)
        else:  # fifo
            sorted_orders = orders

        results = []

        for order in sorted_orders:
            if order.status != "pending":
                continue

            result = self.match_order(order)
            if result:
                results.append(result)

        return results

    def get_match_statistics(self) -> Dict:
        """获取匹配统计信息"""
        total_codes = len(self.pool.trace_codes)
        used_codes = sum(1 for code in self.pool.trace_codes.values() if code.used_quantity > 0)
        available_codes = sum(1 for code in self.pool.trace_codes.values() if code.is_available)

        total_quantity = sum(code.total_quantity for code in self.pool.trace_codes.values())
        used_quantity = sum(code.used_quantity for code in self.pool.trace_codes.values())

        return {
            "total_trace_codes": total_codes,
            "used_trace_codes": used_codes,
            "available_trace_codes": available_codes,
            "total_quantity": total_quantity,
            "used_quantity": used_quantity,
            "remaining_quantity": total_quantity - used_quantity,
            "utilization_rate": used_quantity / total_quantity if total_quantity > 0 else 0
        }


class AdvancedMedicationMatcher(MedicationMatcher):
    """高级匹配器（支持更多策略）"""

    def __init__(self, allow_multiple_codes: bool = True,
                 optimize_strategy: str = "min_waste"):
        """
        :param optimize_strategy: 优化策略
            - min_waste: 最小化浪费
            - min_codes: 最小化追溯码使用数量
            - expiry_first: 近效期优先
        """
        super().__init__(allow_multiple_codes)
        self.optimize_strategy = optimize_strategy

    def match_single_order_single_code(self, order: MedicalOrder) -> Optional[Dict]:
        """重写单追溯码匹配，支持不同优化策略"""
        available_codes = self.pool.get_available_codes_by_drug(order.drug_name)
        if not available_codes:
            return None

        # 根据策略选择最佳追溯码
        if self.optimize_strategy == "expiry_first":
            # 近效期优先：需要追溯码有有效期信息
            available_codes.sort(key=lambda x: x.expiration_date or "9999-12-31")
        elif self.optimize_strategy == "min_codes":
            # 优先使用剩余量大的，为后续匹配留空间
            available_codes.sort(key=lambda x: x.remaining_quantity, reverse=True)
        else:  # min_waste
            available_codes.sort(key=lambda x: x.remaining_quantity)

        # 找到第一个剩余量足够的追溯码
        for code in available_codes:
            if code.remaining_quantity >= order.required_quantity:
                used, remaining = code.use_quantity(order.required_quantity)

                return {
                    "order_id": order.order_id,
                    "patient_id": order.patient_id,
                    "patient_name": order.patient_name,
                    "drug_name": order.drug_name,
                    "required_quantity": order.required_quantity,
                    "matched_quantity": used,
                    "remaining_in_order": remaining,
                    "trace_codes": [
                        {
                            "code": code.code,
                            "specification": code.specification,
                            "used_quantity": used,
                            "remaining_in_code": code.remaining_quantity,
                            "batch_id": code.batch_id,
                            "expiration_date": code.expiration_date
                        }
                    ],
                    "strategy": f"single_code_{self.optimize_strategy}"
                }

        return None


def create_sample_data() -> Tuple[List[TraceCode], List[MedicalOrder]]:
    """创建示例数据"""
    # 创建追溯码池
    trace_codes = [
        TraceCode(
            code="A001",
            drug_name="药品A",
            specification="10粒/盒",
            total_quantity=10,
            batch_id="B20250101",
            expiration_date="2026-12-31"
        ),
        TraceCode(
            code="A002",
            drug_name="药品A",
            specification="10粒/盒",
            total_quantity=10,
            batch_id="B20250102",
            expiration_date="2026-12-31"
        ),
        TraceCode(
            code="B001",
            drug_name="药品B",
            specification="20片/盒",
            total_quantity=20,
            batch_id="B20250103",
            expiration_date="2027-06-30"
        ),
    ]

    # 创建医嘱列表
    orders = [
        MedicalOrder(
            order_id="O001",
            patient_id="P001",
            patient_name="患者A",
            drug_name="药品A",
            required_quantity=6
        ),
        MedicalOrder(
            order_id="O002",
            patient_id="P002",
            patient_name="患者B",
            drug_name="药品A",
            required_quantity=6
        ),
        MedicalOrder(
            order_id="O003",
            patient_id="P003",
            patient_name="患者C",
            drug_name="药品B",
            required_quantity=15
        ),
    ]

    return trace_codes, orders


def main():
    """主函数示例"""
    print("=" * 50)
    print("药品追溯码与医嘱匹配系统")
    print("=" * 50)

    # 1. 准备数据
    trace_codes, orders = create_sample_data()

    # 2. 创建匹配器（允许多追溯码）
    print("\n1. 允许多追溯码匹配:")
    matcher1 = MedicationMatcher(allow_multiple_codes=True)
    matcher1.load_trace_codes(trace_codes)

    # 3. 执行匹配
    results1 = matcher1.batch_match_orders(orders)

    # 4. 输出结果
    for result in results1:
        print(f"\n医嘱 {result['order_id']} ({result['patient_name']}):")
        print(f"  药品: {result['drug_name']}, 需要: {result['required_quantity']}粒")
        print(f"  匹配策略: {result['strategy']}")
        for i, trace in enumerate(result['trace_codes'], 1):
            print(f"  追溯码{i}: {trace['code']}, 使用: {trace['used_quantity']}粒, "
                  f"剩余: {trace['remaining_in_code']}粒")

    # 5. 查看统计
    stats1 = matcher1.get_match_statistics()
    print(f"\n匹配统计:")
    print(f"  使用追溯码: {stats1['used_trace_codes']}/{stats1['total_trace_codes']}")
    print(f"  使用数量: {stats1['used_quantity']}/{stats1['total_quantity']}")
    print(f"  利用率: {stats1['utilization_rate']:.1%}")

    # 6. 测试不允许多追溯码的情况
    print("\n" + "=" * 50)
    print("2. 不允许多追溯码匹配:")

    # 重置数据
    for code in trace_codes:
        code.used_quantity = 0

    matcher2 = MedicationMatcher(allow_multiple_codes=False)
    matcher2.load_trace_codes(trace_codes)

    # 重新设置医嘱状态
    for order in orders:
        order.status = "pending"

    results2 = matcher2.batch_match_orders(orders)

    for result in results2:
        print(f"\n医嘱 {result['order_id']} ({result['patient_name']}):")
        print(f"  药品: {result['drug_name']}, 需要: {result['required_quantity']}粒")
        if result.get('remaining_in_order', 0) > 0:
            print(f"  ⚠️ 未能完全匹配，还缺 {result['remaining_in_order']} 粒")

    # 7. 测试高级匹配器
    print("\n" + "=" * 50)
    print("3. 高级匹配器（近效期优先）:")

    # 重置数据
    for code in trace_codes:
        code.used_quantity = 0

    advanced_matcher = AdvancedMedicationMatcher(
        allow_multiple_codes=True,
        optimize_strategy="expiry_first"
    )
    advanced_matcher.load_trace_codes(trace_codes)

    # 重新设置医嘱状态
    for order in orders:
        order.status = "pending"

    results3 = advanced_matcher.batch_match_orders(orders)

    for result in results3:
        print(f"\n医嘱 {result['order_id']} ({result['patient_name']}):")
        print(f"  匹配策略: {result['strategy']}")
        for trace in result['trace_codes']:
            expiry_info = f", 效期: {trace.get('expiration_date', '未知')}"
            print(f"  追溯码: {trace['code']}{expiry_info}")


if __name__ == "__main__":
    main()