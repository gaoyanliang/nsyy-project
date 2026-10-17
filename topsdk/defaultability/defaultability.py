from topsdk.client import TopApiClient, BaseRequest

class Defaultability:

    def __init__(self, client: TopApiClient):
        self._client = client

    """
        异常码详情列表
    """
    def alibaba_alihealth_drug_myj_codewarn_codewarninginfodetaillist(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        码预警列表
    """
    def alibaba_alihealth_drug_myj_codewarn_codewarninglist(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        生成码预警任务
    """
    def alibaba_alihealth_drug_myj_codewarn_createcodewarntask(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
    """
        同步获取码预警信息
    """
    def alibaba_alihealth_drug_myj_codewarn_getwarninfo(self, request: BaseRequest):
        return self._client.execute(request.get_api_name(), request.to_dict(), request.get_file_param_dict())
