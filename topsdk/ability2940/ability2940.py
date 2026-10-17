from topsdk.client import TopApiClient, BaseRequest

class Ability2940:

    def __init__(self, client: TopApiClient):
        self._client = client

    """
        查询本企业出入库单数量
    """
    def alibaba_alihealth_drug_yljg_query_billcount(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        查询上游出库单数量
    """
    def alibaba_alihealth_drug_yljg_query_upoutbillcount(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        零售单据上传接口
    """
    def alibaba_alihealth_drugtrace_top_yljg_uploadretail(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        出入库单据上传
    """
    def alibaba_alihealth_drugtrace_top_yljg_uploadinoutbill(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        上传单据后处理状态查询
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_billstatus(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        查询药品信息
    """
    def alibaba_alihealth_drugtrace_top_yljg_getdruglist(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        通过一个码，查询这个码对应的上游企业出库单的单据号
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_upbillcode(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        根据单据号查询单据的详情信息【注意：查询的是本企业的单据】
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_upbilldetail(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        单码关联关系查询
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_relation(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        由于无法返回多条匹配信息，本接口已不再推荐使用，推荐使用新接口，新接口名称：alibaba.alihealth.drug.yljg.getentinfolist
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_getentinfo(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        部分处理成功单据处理失败的码明细
    """
    def alibaba_alihealth_drugtrace_top_yljg_listbillprocesspartsuccess(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        根据码查询码信息
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_codedetail(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        医疗机构查询本企业上游企业出库单据信息
    """
    def alibaba_alihealth_drugtrace_top_yljg_listupout(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        上游出库单单据明细查询
    """
    def alibaba_alihealth_drugtrace_top_yljg_listupout_detail(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        新增往来单位企业
    """
    def alibaba_alihealth_drug_yljg_saveent(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        由于无法返回多条匹配信息，本接口已不再推荐使用，推荐使用新接口，新接口名称：alibaba.alihealth.drug.yljg.getentinfolist
    """
    def alibaba_alihealth_drug_yljg_getentinfonew(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        获取服务截止日期
    """
    def alibaba_alihealth_drugtrace_top_yljg_service_getenddate(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        获取重点追溯品种明细下载URL
    """
    def alibaba_alihealth_drugtrace_top_yljg_getkeyflagdruginfo_downloadurl(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        通过时间段批量查询入出库单信息。
    """
    def alibaba_alihealth_drug_yljg_searchbill(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        往来单位查询
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_listparts(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        企业信息-根据企业名称或证号查询企业信息列表
    """
    def alibaba_alihealth_drug_yljg_getentinfolist(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        查询药品目录信息
    """
    def alibaba_alihealth_drugtrace_top_yljg_drugtable(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        根据企业唯一标识查看企业详细信息
    """
    def alibaba_alihealth_drugtrace_top_yljg_query_getbyrefentid(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
