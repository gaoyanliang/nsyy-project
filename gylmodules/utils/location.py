import math

from typing import Tuple


class CoordinateConvert:
    PI = 3.1415926535897932384626
    EE = 0.00669342162296594323
    A = 6378245.0

    @staticmethod
    def wgs84_to_gcj02(lng: float, lat: float) -> Tuple[float, float]:
        """
        WGS84 转 GCJ02
        :param lng: 经度
        :param lat: 纬度
        :return: (经度, 纬度)
        """
        if CoordinateConvert.out_of_china(lng, lat):
            return lng, lat

        d_lat = CoordinateConvert.transform_lat(lng - 105.0, lat - 35.0)
        d_lng = CoordinateConvert.transform_lng(lng - 105.0, lat - 35.0)
        rad_lat = lat / 180.0 * CoordinateConvert.PI
        magic = math.sin(rad_lat)
        magic = 1 - CoordinateConvert.EE * magic * magic
        sqrt_magic = math.sqrt(magic)
        d_lat = (d_lat * 180.0) / (
                    (CoordinateConvert.A * (1 - CoordinateConvert.EE)) / (magic * sqrt_magic) * CoordinateConvert.PI)
        d_lng = (d_lng * 180.0) / (CoordinateConvert.A / sqrt_magic * math.cos(rad_lat) * CoordinateConvert.PI)
        return lng + d_lng, lat + d_lat

    @staticmethod
    def out_of_china(lng: float, lat: float) -> bool:
        """
        判断坐标是否在中国范围外
        :param lng: 经度
        :param lat: 纬度
        :return: True 如果在中国范围外，否则 False
        """
        return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)

    @staticmethod
    def transform_lat(x: float, y: float) -> float:
        """
        纬度转换
        :param x: 经度偏移
        :param y: 纬度偏移
        :return: 转换后的纬度偏移
        """
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * CoordinateConvert.PI) + 20.0 * math.sin(
            2.0 * x * CoordinateConvert.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * CoordinateConvert.PI) + 40.0 * math.sin(y / 3.0 * CoordinateConvert.PI)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * CoordinateConvert.PI) + 320 * math.sin(
            y * CoordinateConvert.PI / 30.0)) * 2.0 / 3.0
        return ret

    @staticmethod
    def transform_lng(x: float, y: float) -> float:
        """
        经度转换
        :param x: 经度偏移
        :param y: 纬度偏移
        :return: 转换后的经度偏移
        """
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * CoordinateConvert.PI) + 20.0 * math.sin(
            2.0 * x * CoordinateConvert.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * CoordinateConvert.PI) + 40.0 * math.sin(x / 3.0 * CoordinateConvert.PI)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * CoordinateConvert.PI) + 300.0 * math.sin(
            x / 30.0 * CoordinateConvert.PI)) * 2.0 / 3.0
        return ret