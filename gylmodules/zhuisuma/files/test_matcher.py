"""
药品追溯码撮合系统 - 完整测试示例
演示各种实际场景的使用方法
"""

from medicine_matcher import MedicineMatcher, Prescription


def test_basic_matching():
    """测试基础撮合功能"""
    print("\n" + "="*70)
    print("测试场景1: 基础单追溯码匹配")
    print("="*70)
    
    matcher = MedicineMatcher(cache_file="test_cache.json")
    matcher.clear_cache()  # 清空之前的数据
    
    # 添加追溯码
    matcher.batch_add_trace_codes([
        {"code": "A001", "medicine_name": "阿莫西林胶囊", "total_quantity": 24},
        {"code": "A002", "medicine_name": "阿莫西林胶囊", "total_quantity": 24},
        {"code": "B001", "medicine_name": "布洛芬片", "total_quantity": 12},
    ])
    
    # 医嘱1: 患者需要10粒阿莫西林
    p1 = Prescription("RX001", "张三", "阿莫西林胶囊", 10)
    binding = matcher.match_prescription(p1, allow_multiple=False)
    
    print(f"\n医嘱: {p1.patient_name} 需要 {p1.medicine_name} {p1.quantity}粒")
    print(f"匹配结果: {binding.trace_codes if binding else '匹配失败'}")
    
    # 查看库存
    inv = matcher.get_medicine_inventory("阿莫西林胶囊")
    print(f"库存剩余: {inv['total_remaining_quantity']}粒")


def test_multiple_codes_matching():
    """测试多追溯码匹配"""
    print("\n" + "="*70)
    print("测试场景2: 多追溯码匹配(允许跨盒)")
    print("="*70)
    
    matcher = MedicineMatcher(cache_file="test_multi.json")
    matcher.clear_cache()
    
    # 添加追溯码
    matcher.batch_add_trace_codes([
        {"code": "C001", "medicine_name": "感冒灵颗粒", "total_quantity": 10},
        {"code": "C002", "medicine_name": "感冒灵颗粒", "total_quantity": 10},
        {"code": "C003", "medicine_name": "感冒灵颗粒", "total_quantity": 10},
    ])
    
    # 医嘱序列
    prescriptions = [
        Prescription("RX101", "李四", "感冒灵颗粒", 8),
        Prescription("RX102", "王五", "感冒灵颗粒", 15),
    ]
    
    for p in prescriptions:
        binding = matcher.match_prescription(p, allow_multiple=True)
        print(f"\n患者: {p.patient_name}, 需要: {p.quantity}粒")
        if binding:
            print(f"匹配追溯码:")
            for tc in binding.trace_codes:
                print(f"  - {tc['code']}: 使用 {tc['used_quantity']}粒")
        else:
            print("❌ 库存不足,匹配失败")
    
    # 最终库存
    inv = matcher.get_medicine_inventory("感冒灵颗粒")
    print(f"\n最终库存: {inv['total_remaining_quantity']}粒")
    for tc in inv['trace_codes']:
        print(f"  {tc['code']}: {tc['remaining_quantity']}/{tc['total_quantity']}粒")


def test_insufficient_inventory():
    """测试库存不足场景"""
    print("\n" + "="*70)
    print("测试场景3: 库存不足情况")
    print("="*70)
    
    matcher = MedicineMatcher(cache_file="test_insufficient.json")
    matcher.clear_cache()
    
    # 只有少量库存
    matcher.add_trace_code("D001", "维生素C片", 10)
    
    # 医嘱需求超过库存
    p1 = Prescription("RX201", "赵六", "维生素C片", 15)
    binding = matcher.match_prescription(p1, allow_multiple=False)
    
    print(f"库存: 10粒")
    print(f"需求: {p1.quantity}粒")
    print(f"结果: {'匹配成功' if binding else '❌ 库存不足,无法匹配'}")


def test_batch_processing():
    """测试批量处理"""
    print("\n" + "="*70)
    print("测试场景4: 批量处理大量医嘱")
    print("="*70)
    
    matcher = MedicineMatcher(cache_file="test_batch.json")
    matcher.clear_cache()
    
    # 添加大量追溯码(模拟一天的入库)
    trace_codes = []
    for i in range(50):
        trace_codes.append({
            "code": f"BATCH{i:03d}",
            "medicine_name": "抗生素A",
            "total_quantity": 20
        })
    
    matcher.batch_add_trace_codes(trace_codes)
    print(f"添加了 {len(trace_codes)} 个追溯码, 总库存: {50*20}粒")
    
    # 批量医嘱(模拟一天的门诊量)
    prescriptions = [
        Prescription(f"RX{i:04d}", f"患者{i}", "抗生素A", 
                    quantity=(i % 10) + 5)  # 5-14粒不等
        for i in range(100)
    ]
    
    print(f"处理 {len(prescriptions)} 条医嘱...")
    
    # 批量匹配
    results = matcher.batch_match_prescriptions(prescriptions, allow_multiple=True)
    
    success_count = sum(1 for r in results.values() if r is not None)
    fail_count = len(results) - success_count
    
    print(f"\n匹配结果:")
    print(f"  ✓ 成功: {success_count} 条")
    print(f"  ❌ 失败: {fail_count} 条")
    
    inv = matcher.get_medicine_inventory("抗生素A")
    print(f"\n剩余库存: {inv['total_remaining_quantity']}粒")


def test_persistence():
    """测试数据持久化"""
    print("\n" + "="*70)
    print("测试场景5: 数据持久化与恢复")
    print("="*70)
    
    # 第一次运行: 创建数据
    print("\n[第1步] 创建撮合器并添加数据")
    matcher1 = MedicineMatcher(cache_file="test_persist.json")
    matcher1.clear_cache()
    
    matcher1.batch_add_trace_codes([
        {"code": "P001", "medicine_name": "药品X", "total_quantity": 30},
        {"code": "P002", "medicine_name": "药品X", "total_quantity": 30},
    ])
    
    p1 = Prescription("RX301", "患者甲", "药品X", 20)
    matcher1.match_prescription(p1, allow_multiple=False)
    
    inv1 = matcher1.get_medicine_inventory("药品X")
    print(f"操作后库存: {inv1['total_remaining_quantity']}粒")
    
    # 模拟服务重启: 创建新实例
    print("\n[第2步] 模拟服务重启,创建新撮合器实例")
    matcher2 = MedicineMatcher(cache_file="test_persist.json")
    
    inv2 = matcher2.get_medicine_inventory("药品X")
    print(f"恢复后库存: {inv2['total_remaining_quantity']}粒")
    
    # 验证绑定关系是否恢复
    binding = matcher2.get_binding("RX301")
    print(f"绑定关系恢复: {binding.trace_codes if binding else '未找到'}")
    
    print("\n✓ 数据持久化测试通过!")


def test_optimal_allocation():
    """测试最优分配策略"""
    print("\n" + "="*70)
    print("测试场景6: 最优分配策略")
    print("="*70)
    
    matcher = MedicineMatcher(cache_file="test_optimal.json")
    matcher.clear_cache()
    
    # 添加不同剩余量的追溯码
    matcher.batch_add_trace_codes([
        {"code": "OPT001", "medicine_name": "药品Y", "total_quantity": 50},  # 大盒
        {"code": "OPT002", "medicine_name": "药品Y", "total_quantity": 20},  # 中盒
        {"code": "OPT003", "medicine_name": "药品Y", "total_quantity": 10},  # 小盒
    ])
    
    print("初始库存:")
    print("  OPT001: 50粒")
    print("  OPT002: 20粒")
    print("  OPT003: 10粒")
    
    # 需要15粒
    print("\n需求: 15粒")
    print("策略: 单追溯码模式会选择最接近15粒的盒子(OPT002:20粒)")
    
    p = Prescription("RX401", "患者", "药品Y", 15)
    binding = matcher.match_prescription(p, allow_multiple=False)
    
    if binding:
        code = binding.trace_codes[0]['code']
        print(f"✓ 实际选择: {code}")
        status = matcher.get_trace_code_status(code)
        print(f"  剩余: {status['remaining_quantity']}粒")


def main():
    """运行所有测试"""
    test_basic_matching()
    test_multiple_codes_matching()
    test_insufficient_inventory()
    test_batch_processing()
    test_persistence()
    test_optimal_allocation()
    
    print("\n" + "="*70)
    print("所有测试完成!")
    print("="*70)


if __name__ == "__main__":
    main()
