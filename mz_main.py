# -*- coding: utf-8 -*-
import logging
import os
import uuid
import threading
from datetime import datetime, date

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# ---------- 第一步：先导入日志配置函数并立即执行 ----------
from gylmodules.global_tools import setup_logging
from gylmodules import global_config

# 立即配置日志（放在最前面，确保其他模块导入前生效）
if global_config.run_in_local:
    setup_logging(log_file='mz.log', level=logging.DEBUG)
else:
    setup_logging(log_file='mz.log', level=logging.INFO)

logger = logging.getLogger(__name__)

# ---------- 第二步：再导入其他依赖（这些模块此时会使用已配置的日志） ----------
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, Request, Response
from fastapi import Request
import uvicorn

# ---------- 导入 FastAPI 应用 ----------
from outpatient_queue.mz_server import mz_router


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一的 request_id，并注入到日志中"""
    async def dispatch(self, request: Request, call_next):
        # 生成 request_id
        request_id = str(uuid.uuid4())
        # 绑定到 request.state，便于在 endpoint 中使用
        request.state.request_id = request_id

        # 为当前线程/协程的 logger 添加上下文（简单实现）
        # 这里使用 logging 的 extra 方式在实际 logger 调用时传入
        response = None
        start_time = datetime.utcnow()

        try:
            response = await call_next(request)
        finally:
            # 计算耗时
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            # 记录请求日志
            logger.debug(
                f"{request.method} {request.url.path} {response.status_code if response else 500}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code if response else 500,
                    "duration_ms": round(duration, 2),
                    "client_host": request.client.host if request.client else None,
                }
            )

        return response


# ====================== FastAPI 应用 ======================
app = FastAPI(title="南阳南石医院")

# 中间件（RequestID + CORS）
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ====================== 全局异常处理器 ======================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 50000, "res": str(exc)}
    )

# --------------------- 将路由注册到 app ---------------------
app.include_router(mz_router)

# ====================== 静态文件服务（保持原路径，不加 /gyl 前缀） ======================
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

mz_doctor_dir = os.path.join(BASE_DIR, "mz_doctor_window")
mz_business_dir = os.path.join(BASE_DIR, "mz_business_window")
mz_summary_dir = os.path.join(BASE_DIR, "mz_summary")
mz_pharmacy_dir = os.path.join(BASE_DIR, "mz_pharmacy")
test_dir = os.path.join(BASE_DIR, "test")
asr_dir = os.path.join(BASE_DIR, "asr")

if os.path.exists(mz_summary_dir):
    app.mount("/mz/mz_summary", StaticFiles(directory=mz_summary_dir, html=True), name="mz_summary")
if os.path.exists(mz_doctor_dir):
    app.mount("/mz/mz_doctor_window", StaticFiles(directory=mz_doctor_dir, html=True), name="mz_doctor")
if os.path.exists(mz_business_dir):
    app.mount("/mz/mz_business_window", StaticFiles(directory=mz_business_dir, html=True), name="mz_business")
if os.path.exists(mz_pharmacy_dir):
    app.mount("/mz/mz_pharmacy", StaticFiles(directory=mz_pharmacy_dir, html=True), name="mz_pharmacy")
if os.path.exists(test_dir):
    app.mount("/mz/test", StaticFiles(directory=test_dir, html=True), name="test")
if os.path.exists(asr_dir):
    app.mount("/mz/asr", StaticFiles(directory=asr_dir, html=True), name="asr")



# ====================== 根路径 ======================
@app.get("/mz/index", response_class=FileResponse)
async def root():
    return FileResponse("index.html")

# ====================== 定时任务启动（在 FastAPI 启动时） ======================
@app.on_event("startup")
def startup_event():
    def run_scheduler():
        logger.info("FastAPI 启动...")

    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    logger.info("FastAPI startup 启动")

# ====================== 启动入口 ======================
if __name__ == "__main__":
    uvicorn.run("mz_main:app", host='0.0.0.0', port=8081 if global_config.run_in_local else 6094, access_log=False, reload=False)

