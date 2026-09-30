from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import heapq


@dataclass
class TraceCode:
    """追溯码实体（优化版）"""
    code: str
    drug_name: str
    total_quantity: int
    used_quantity: int = 0
    batch_id: Optional[str] = None
    expiration_date: Optional[str] = None

    @property
    def remaining(self) -> int:
        return self.total_quantity - self.used_quantity

    @property
    def is_available(self) -> bool:
        return self.remaining > 0


class OptimizedTraceCodePool:
    """优化的追溯码池"""

    def __init__(self):
        self.codes: Dict[str, TraceCode] = {}
        self.drug_codes: Dict[str, List[TraceCode]] = defaultdict(list)
        # 为每种药品维护多个索引
        self.available_by_drug: Dict[str, List[TraceCode]] = defaultdict(list)
        self._cached_available = {}

    def add_trace_code(self, code: TraceCode):
        self.codes[code.code] = code
        self.drug_codes[code.drug_name].append(code)
        if code.is_available:
            self.available_by_drug[code.drug_name].append(code)

    def get_best_match_greedy(self, drug_name: str, quantity: int) -> List[Tuple[TraceCode, int]]:
        """贪心算法：优先使用剩余多的"""
        available = [c for c in self.available_by_drug.get(drug_name, []) if c.is_available]
        if not available:
            return []

        available.sort(key=lambda x: x.remaining, reverse=True)
        result = []
        remaining_qty = quantity

        for code in available:
            if remaining_qty <= 0:
                break
            use = min(code.remaining, remaining_qty)
            result.append((code, use))
            remaining_qty -= use

        if remaining_qty > 0:
            return []  # 无法完全匹配

        return result

    def find_min_waste_single(self, drug_name: str, quantity: int) -> Optional[TraceCode]:
        """找到浪费最少的单个追溯码"""
        available = self.available_by_drug.get(drug_name, [])
        if not available:
            return None

        # 优先选择剩余量刚好满足或略多的
        best_match = None
        min_waste = float('inf')

        for code in available:
            if code.remaining >= quantity:
                waste = code.remaining - quantity
                if waste < min_waste:
                    min_waste = waste
                    best_match = code

        return best_match


class EfficientMedicationMatcher:
    """高效的药品匹配器"""

    def __init__(self, allow_multiple_codes: bool = True):
        self.pool = OptimizedTraceCodePool()
        self.allow_multiple_codes = allow_multiple_codes

        # 缓存匹配结果
        self.match_cache = {}
        self.order_counter = 0

    def load_trace_codes(self, codes: List[TraceCode]):
        for code in codes:
            self.pool.add_trace_code(code)

    def match_with_dp(self, drug_name: str, quantity: int, max_codes: int = 3) -> List[Tuple[TraceCode, int]]:
        """
        使用动态规划找到最小化追溯码数量的组合
        限制追溯码数量以避免组合爆炸
        """
        available = [c for c in self.pool.available_by_drug.get(drug_name, [])
                     if c.is_available]

        if not available:
            return []

        # 按剩余数量排序
        available.sort(key=lambda x: x.remaining, reverse=True)

        # 限制数量，避免组合爆炸
        if len(available) > 20:
            available = available[:20]

        # 使用DP找到最小数量组合
        # dp[i][j] = 用前i个追溯码达到数量j所需的最小追溯码数
        INF = float('inf')
        n = len(available)

        # 压缩状态：只存储可能的数量
        max_qty = min(quantity * 2, sum(c.remaining for c in available))

        dp = [INF] * (max_qty + 1)
        prev = [None] * (max_qty + 1)
        dp[0] = 0

        for i, code in enumerate(available):
            new_dp = dp.copy()
            new_prev = prev.copy()

            for j in range(max_qty + 1):
                if dp[j] < INF:
                    for use in range(1, min(code.remaining, max_qty - j) + 1):
                        if dp[j] + 1 < new_dp[j + use]:
                            new_dp[j + use] = dp[j] + 1
                            new_prev[j + use] = (i, j, use)

            dp = new_dp
            prev = new_prev

        # 找到满足需求的最小数量组合
        if quantity <= max_qty and dp[quantity] < INF and dp[quantity] <= max_codes:
            # 回溯构造结果
            result = []
            q = quantity
            while q > 0:
                i, prev_q, use = prev[q]
                code = available[i]
                result.append((code, use))
                q = prev_q

            return result

        return []

    def match_order(self, order) -> Optional[Dict]:
        """匹配单个医嘱"""
        self.order_counter += 1

        # 1. 先尝试单追溯码匹配（效率最高）
        single_code = self.pool.find_min_waste_single(order.drug_name, order.required_quantity)
        if single_code:
            used, _ = single_code.use_quantity(order.required_quantity)
            return self._create_result(order, [(single_code, used)], "single")

        # 2. 如果允许多追溯码，尝试组合匹配
        if self.allow_multiple_codes:
            # 先尝试最小化追溯码数量的组合
            dp_result = self.match_with_dp(order.drug_name, order.required_quantity)
            if dp_result:
                # 应用使用量
                for code, use in dp_result:
                    code.used_quantity += use
                return self._create_result(order, dp_result, "dp_optimal")

            # 回退到贪心算法
            greedy_result = self.pool.get_best_match_greedy(order.drug_name, order.required_quantity)
            if greedy_result:
                for code, use in greedy_result:
                    code.used_quantity += use
                return self._create_result(order, greedy_result, "greedy")

        return None

    def _create_result(self, order, matches, strategy):
        trace_info = []
        for code, use in matches:
            trace_info.append({
                "code": code.code,
                "used_quantity": use,
                "remaining_in_code": code.remaining,
                "batch_id": code.batch_id
            })

        return {
            "order_id": order.order_id,
            "patient_name": order.patient_name,
            "drug_name": order.drug_name,
            "required_quantity": order.required_quantity,
            "matched_quantity": sum(use for _, use in matches),
            "trace_codes": trace_info,
            "strategy": strategy,
            "num_codes_used": len(matches)
        }

    def batch_match_optimized(self, orders: List) -> List[Dict]:
        """批量匹配优化版"""
        # 按药品分组处理，减少重复查询
        orders_by_drug = defaultdict(list)
        for order in orders:
            orders_by_drug[order.drug_name].append(order)

        results = []

        # 对每种药品独立处理
        for drug_name, drug_orders in orders_by_drug.items():
            # 可以进一步优化：按需求量排序处理
            for order in sorted(drug_orders, key=lambda x: x.required_quantity):
                result = self.match_order(order)
                if result:
                    results.append(result)

        return results


class PriorityBasedMatcher:
    """基于优先级的匹配器"""

    def __init__(self):
        self.pool = OptimizedTraceCodePool()
        # 优先队列：按（过期时间，剩余数量）排序
        self.priority_queues = defaultdict(list)

    def add_trace_code(self, code: TraceCode):
        self.pool.add_trace_code(code)
        # 构建优先队列（近效期优先，剩余少优先）
        if code.is_available:
            priority = (
                code.expiration_date or "9999-12-31",  # 效期早的优先
                -code.remaining  # 剩余少的优先（减少浪费）
            )
            heapq.heappush(self.priority_queues[code.drug_name], (priority, code))

    def match_order_priority(self, order) -> Optional[Dict]:
        """使用优先队列匹配"""
        if order.drug_name not in self.priority_queues:
            return None

        required = order.required_quantity
        matches = []
        temp_used = []  # 临时记录使用量，如果匹配失败要回滚

        while required > 0 and self.priority_queues[order.drug_name]:
            # 获取最高优先级的追溯码
            priority, code = heapq.heappop(self.priority_queues[order.drug_name])

            if not code.is_available:
                continue

            use = min(code.remaining, required)
            code.used_quantity += use
            required -= use
            matches.append((code, use))
            temp_used.append((code, use))

            # 如果还有剩余，重新入队
            if code.is_available:
                new_priority = (
                    code.expiration_date or "9999-12-31",
                    -code.remaining
                )
                heapq.heappush(self.priority_queues[order.drug_name], (new_priority, code))

        if required == 0:
            # 匹配成功
            return self._create_result(order, matches)
        else:
            # 匹配失败，回滚使用量
            for code, use in temp_used:
                code.used_quantity -= use
            # 将取出的追溯码重新放回队列
            for priority, code in temp_used:
                heapq.heappush(self.priority_queues[order.drug_name],
                               ((code.expiration_date or "9999-12-31", -code.remaining), code))
            return None

    def _create_result(self, order, matches):
        trace_info = []
        for code, use in matches:
            trace_info.append({
                "code": code.code,
                "used_quantity": use,
                "remaining_in_code": code.remaining
            })

        return {
            "order_id": order.order_id,
            "matched_quantity": order.required_quantity,
            "trace_codes": trace_info,
            "num_codes_used": len(matches)
        }


# 性能测试工具
import time
import random


def performance_test():
    """性能测试"""
    print("性能测试...")

    # 生成测试数据
    def generate_test_data(num_codes=1000, num_orders=500):
        # 生成追溯码
        codes = []
        for i in range(num_codes):
            drug = random.choice(["药品A", "药品B", "药品C"])
            codes.append(TraceCode(
                code=f"CODE{i:06d}",
                drug_name=drug,
                total_quantity=random.randint(10, 100),
                batch_id=f"BATCH{i // 100:04d}",
                expiration_date=f"202{random.randint(5, 8)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            ))

        # 生成医嘱
        orders = []
        for i in range(num_orders):
            drug = random.choice(["药品A", "药品B", "药品C"])
            orders.append(type('Order', (), {
                'order_id': f"ORDER{i:06d}",
                'patient_name': f"患者{i}",
                'drug_name': drug,
                'required_quantity': random.randint(1, 30)
            })())

        return codes, orders

    # 测试原始实现
    codes, orders = generate_test_data(100, 50)

    start = time.time()
    matcher_original = EfficientMedicationMatcher()
    matcher_original.load_trace_codes(codes)
    results1 = matcher_original.batch_match_optimized(orders)
    time1 = time.time() - start

    # 测试优化版本
    codes, orders = generate_test_data(100, 50)

    start = time.time()
    matcher_priority = PriorityBasedMatcher()
    for code in codes:
        matcher_priority.add_trace_code(code)

    results2 = []
    for order in orders:
        result = matcher_priority.match_order_priority(order)
        if result:
            results2.append(result)
    time2 = time.time() - start

    print(f"原始实现: {len(results1)} 个匹配, 耗时: {time1:.3f}s")
    print(f"优化实现: {len(results2)} 个匹配, 耗时: {time2:.3f}s")
    print(f"性能提升: {(time1 - time2) / time1:.1%}")


# 实际使用示例
def practical_example():
    """实际使用示例"""
    # 1. 数据准备
    codes = [
        TraceCode("A001", "阿莫西林", 24, batch_id="B231201"),
        TraceCode("A002", "阿莫西林", 24, batch_id="B231202"),
        TraceCode("A003", "阿莫西林", 12, batch_id="B231203"),
        TraceCode("B001", "布洛芬", 20, batch_id="B231204"),
    ]

    class Order:
        def __init__(self, oid, name, drug, qty):
            self.order_id = oid
            self.patient_name = name
            self.drug_name = drug
            self.required_quantity = qty

    orders = [
        Order("O001", "患者A", "阿莫西林", 30),
        Order("O002", "患者B", "阿莫西林", 15),
        Order("O003", "患者C", "布洛芬", 10),
    ]

    # 2. 使用高效匹配器
    print("使用高效匹配器...")
    matcher = EfficientMedicationMatcher(allow_multiple_codes=True)
    matcher.load_trace_codes(codes)
    results = matcher.batch_match_optimized(orders)

    # 3. 输出结果
    for result in results:
        print(f"\n医嘱 {result['order_id']} ({result['patient_name']}):")
        print(f"  药品: {result['drug_name']}, 需要: {result['required_quantity']}")
        print(f"  匹配策略: {result['strategy']}, 使用追溯码数: {result['num_codes_used']}")
        for trace in result['trace_codes']:
            print(f"  - {trace['code']}: 使用 {trace['used_quantity']}, 剩余 {trace['remaining_in_code']}")


if __name__ == "__main__":
    print("=" * 50)
    print("高效药品追溯码匹配系统")
    print("=" * 50)

    practical_example()
    print("\n" + "=" * 50)
    performance_test()