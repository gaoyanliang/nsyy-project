import warnings

import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import logging
import time
import io
import os
from typing import Union, List, Dict
from pdf2image import convert_from_path
import re
from typing import Optional

logger = logging.getLogger(__name__)


def pdf_to_jpg(pdf_path, output_dir="output_jpg", dpi=300):
    """
    将 PDF 转换为 JPG 格式图片。
    """
    try:
        # 获取 PDF 文件名（不含扩展名）
        pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        images = convert_from_path(pdf_path, dpi=dpi, fmt='jpg')
    except Exception as e:
        logger.error(f"{pdf_path} PDF 转换失败: {e}")
        return []

    # 保存图片并记录完整路径
    jpg_paths = []
    for i, image in enumerate(images):
        # 使用 PDF 文件名作为前缀
        jpg_filename = f"{pdf_filename}_page_{i + 1}.jpg"
        jpg_path = os.path.join(output_dir, jpg_filename)
        try:
            image.save(jpg_path, "JPEG")
            # 获取完整路径
            full_path = os.path.abspath(jpg_path)
            jpg_paths.append(full_path)
        except Exception as e:
            logger.error(f"保存第 {i + 1} 页失败: {e}")

    return jpg_paths


def delete_files(file_paths):
    """
    根据给定的文件路径删除文件。
    """
    # 如果输入是单个路径，转换为列表
    if isinstance(file_paths, str):
        file_paths = [file_paths]

    # 存储删除结果
    results = {}

    for file_path in file_paths:
        try:
            # 检查文件是否存在
            if os.path.exists(file_path):
                os.remove(file_path)
                results[file_path] = True
            else:
                results[file_path] = False
                logger.warning(f"文件不存在: {os.path.abspath(file_path)}")
        except Exception as e:
            results[file_path] = False
            logger.error(f"删除文件失败 ({os.path.abspath(file_path)}): {e}")

    return results


def extract_name_from_text(text: str) -> Optional[str]:
    """
    修复版姓名提取函数，适配更多格式变体
    支持格式：
    - "姓名 袁翼航 ID号：2025032804"
    - "姓袁翼航 ID号：2025032804"
    - "姓名: 张三 年龄：30"
    - "姓: 张三 年龄：30"
    - "Name: John Smith Age: 25"
    - "袁翼航 检查日期：28-03-2025"
    - "Patient: 李四 ID: 12345"
    """
    # 定义修复后的匹配模式（按优先级排序）
    patterns = [
        # 中文格式（带"姓名"前缀，支持空格或冒号分隔）
        r'(?:姓名|名字|姓)[\s:：]*([^\s\d：:]{2,4})(?=\s|$|ID|年龄|性别|检查日期)',
        # 英文格式
        r'(?:Name|Patient)[\s:：]*([A-Za-z]+\s+[A-Za-z]+)(?=\s|$|Age|ID|Gender)',
        # 前缀后直接接姓名（如"姓袁翼航"）
        r'(?:姓名|名字|姓)([^\s\d：:]{2,4})(?=\s|$|ID|年龄|性别|检查日期)',
    ]

    for pattern in patterns:
        try:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                """验证是否为有效姓名 2-4个中文字符 英文名（2-3个单词，首字母大写）"""
                if (re.fullmatch(r'[\u4e00-\u9fa5]{2,4}', name) or
                        re.fullmatch(r'([A-Z][a-z]+\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?)', name)):
                    return name
        except re.error:
            continue  # 跳过有问题的正则模式

    return None


class MacOCRProcessor:
    def __init__(self):
        self._ocr_engine = None
        self.language_map = {
            'ch': {'lang': 'ch', 'cls_model_dir': None},  # macOS建议禁用分类器
            'en': {'lang': 'en', 'cls_model_dir': None},
            'multi': {'lang': 'ch_en', 'cls_model_dir': None}
        }

    @property
    def ocr_engine(self):
        """macOS优化版引擎初始化"""
        if self._ocr_engine is None:
            logger.info("初始化 PDF OCR 解析工具...")
            try:
                self._ocr_engine = PaddleOCR(
                    lang='ch',
                    use_angle_cls=False,  # macOS上建议禁用角度分类
                    use_gpu=False,  # macOS默认禁用GPU加速
                    enable_mkldnn=False,  # macOS不需要此参数
                    show_log=False,
                    det_model_dir='inference/ch_ppocr_server_v2.0_det_infer/',
                    rec_model_dir='inference/ch_ppocr_server_v2.0_rec_infer/',
                    cls_model_dir=None  # 显式禁用分类模型
                    # cls_model_dir = r'./inference/ch_ppocr_mobile_v2.0_cls_infer/',
                )
            except Exception as e:
                logger.error(f"初始化失败: {str(e)}")
                raise
        return self._ocr_engine

    def load_image(self, image_input: Union[str, np.ndarray, bytes]) -> np.ndarray:
        """macOS专属图像加载方法"""
        try:
            # 处理UNIX路径格式
            if isinstance(image_input, str):
                with open(image_input, 'rb') as f:
                    img = Image.open(io.BytesIO(f.read()))
                    # 处理macOS截图可能带有alpha通道的情况
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        img = img.convert('RGB')

            # 其他类型处理与Windows版相同
            elif isinstance(image_input, bytes):
                img = Image.open(io.BytesIO(image_input)).convert('RGB')
            elif isinstance(image_input, np.ndarray):
                img = Image.fromarray(image_input)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

            return np.array(img)

        except Exception as e:
            logger.error(f"图像加载失败: {str(e)}")
            raise

    def ocr_image(self, image_input: Union[str, np.ndarray, bytes], language: str = 'ch', merge_level: int = 1) -> Dict:
        """macOS优化版OCR方法, merge_level 0:不合并 1:行合并 2:段落合并"""
        ret_data = {"code": 20000, "data": []}

        try:
            # 1. 加载图像
            img_array = self.load_image(image_input)

            # 2. 执行OCR（macOS特定参数）
            ocr_result = self.ocr_engine.ocr(img_array, cls=False)  # 禁用分类

            # 3. 处理结果
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    if len(line) >= 2:
                        points, (text, confidence) = line
                        ret_data["data"].append({
                            "text": text.strip(),
                            "confidence": float(confidence),
                            "position": [list(map(int, p)) for p in points]
                        })

                # macOS特有的合并策略
                if merge_level > 0:
                    ret_data["data"] = self._mac_merge_lines(ret_data["data"], level=merge_level)

            return ret_data

        except Exception as e:
            logger.error(f"OCR处理失败: {str(e)}")
            return {"code": 50000, "error": str(e)}

    def _mac_merge_lines(self, text_blocks: List[Dict], level: int = 1) -> List[Dict]:
        """
        macOS专属文本合并策略  level参数: 0 - 不合并  1 - 行合并（默认） 2 - 段落合并（适合多栏文本）
        """
        if level == 0 or len(text_blocks) <= 1:
            return text_blocks

        # 按Y坐标排序（考虑macOS的Retina显示屏高DPI特性）
        sorted_blocks = sorted(
            text_blocks,
            key=lambda x: (sum(p[1] for p in x["position"]) / 4, x["position"][0][0])
        )

        merged = []
        current = sorted_blocks[0]

        for block in sorted_blocks[1:]:
            c_box = np.array(current["position"])
            n_box = np.array(block["position"])

            # 计算垂直重叠（macOS需要更宽松的阈值）
            y_overlap = min(c_box[:, 1].max(), n_box[:, 1].max()) - max(c_box[:, 1].min(), n_box[:, 1].min())
            min_height = min(c_box[:, 1].max() - c_box[:, 1].min(), n_box[:, 1].max() - n_box[:, 1].min())

            # 合并条件判断
            if (y_overlap > min_height * 0.3 and  # 宽松垂直重叠条件
                    (n_box[0, 0] - c_box[1, 0]) < (c_box[1, 0] - c_box[0, 0]) * 2.5):  # 动态水平间距阈值

                # 合并文本框
                new_pos = [
                    [min(c_box[0, 0], n_box[0, 0]), min(c_box[0, 1], n_box[0, 1])],
                    [max(c_box[1, 0], n_box[1, 0]), min(c_box[1, 1], n_box[1, 1])],
                    [max(c_box[2, 0], n_box[2, 0]), max(c_box[2, 1], n_box[2, 1])],
                    [min(c_box[3, 0], n_box[3, 0]), max(c_box[3, 1], n_box[3, 1])]
                ]
                sep = ' ' if level == 1 else '\n'  # 段落合并换行
                current = {
                    "text": current["text"] + sep + block["text"],
                    "confidence": min(current["confidence"], block["confidence"]),
                    "position": new_pos
                }
            else:
                merged.append(current)
                current = block

        merged.append(current)
        return merged


# macOS环境检测
if __name__ == "__main__":
    start_time = time.time()

    pdf_file = "/Users/gaoyanliang/各个系统文档整理/眼科医院/眼科医院仪器检查报告和病历/202角膜内皮显微镜/202 角膜内皮细胞报告.pdf"  # 替换为你的 PDF 文件路径
    output_directory = "./"  # 替换为你的输出目录
    saved_jpgs = pdf_to_jpg(pdf_file, output_directory)
    print("转换完成的 JPG 文件完整路径:")
    for path in saved_jpgs:
        print(path)

    print("PDF 转换 JPG 完成，耗时:", round(time.time() - start_time, 2), "秒")

    # 使用示例
    processor = MacOCRProcessor()

    # 示例1: 识别PNG截图（处理透明背景）
    # result = processor.ocr_image(r"/Users/gaoyanliang/Downloads/L角膜OCT.jpg", merge_level=2)
    # result = processor.ocr_image(saved_jpgs[0], merge_level=2)

    # 示例2: 识别PDF转换的图片
    with open(saved_jpgs[0], "rb") as f:
        result = processor.ocr_image(f.read(), language='en')

    # 打印结果
    for item in result.get("data", []):
        if item['confidence'] < 0.90:
            print(f"{item['text']} | 置信度: {item['confidence']:.2f}")
        else:
            print(f"{item['text']}")
        print('=========== ', extract_name_from_text(item['text']))

    print("识别完成，耗时:", round(time.time() - start_time, 2), "秒")
    delete_files(saved_jpgs)
