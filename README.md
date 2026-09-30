## 数据库账号

1. 本地数据库 Mysql 127.0.0.1:3306 root/gyl.2015
2. 服务器数据库 Mysql 192.168.3.12:3306 gyl/123456
3. 邮箱服务器 MariaDB 192.168.3.92:3306 root/NSYYnsyy@123 vmail
4. 新HIS数据库 PostgreSQL 192.168.8.57:6000 ogg/nyogg@2024 df_his       京颐移动护理系统  jk_jingyiydhl/jingyiydhl@123  df_his
5. 老HIS数据库 Oracle 192.168.3.8:1521 Service Name=ORCL zlhis/.1451534F81B 
6. OA服务器数据库 Mysql 192.168.3.12:3306 root/123123
7. PACS 数据库 SQL Server 192.168.3.53:1433 sa/NYS@intechhosun
8. 危机值数据库 Oracle 192.168.3.240:1521 Service Name=ORCL system/d67v7rbZyV

## 服务器账号

1. 192.168.3.240 gyl/gaoyanliang123     管理员  root/wy123qwe.
2. 192.168.3.12  gyl/gyl123    
3. 192.168.3.45  yifei/yifei
4. 192.168.3.92  cc/NSYYnsyy@123    邮箱服务器
5. 192.168.9.75  gyl/nsyy0601.      文件服务器

 


## 医体融合项目 sport_mng

### 电子健康卡服务

电子健康卡服务分测试环境和正式环境，所有配置均在 `sport_mng/ehc_config.py` 中，其中通过 `isDebug` 配置来区分使用那个环境。

## 消息推送

android 使用的华为推送

iOS 使用的 apple APNs 推送，需要生成 推送证书（有效期一年，一年后需要重新生成）


创建推送证书
    选择 "Certificates" → "+" 创建新证书
    选择 "Apple Push Notification service SSL (Sandbox & Production)"
    选择对应的 App ID
    按照指示创建 CSR 文件（使用 Keychain Access）
    上传 CSR 文件并下载证书（.cer 文件）
    双击安装到钥匙串，然后导出为 .p12 文件（需要密码）

配置推送证书
    使用之前导出的 .p12 文件
    或者将证书转换为 PEM 格式：

```shell
openssl x509 -in aps.cer -inform der -out PushCert.pem
openssl pkcs12 -nocerts -out PushKey.pem -in 证书.p12 -legacy
cat PushCert.pem PushKey.pem > ck.pem

验证生成的 PEM 文件
openssl x509 -in ck.pem -text -noout  # 验证证书部分
openssl rsa -in ck.pem -check  # 验证私钥部分（如果有错误会提示）
```


改用 aioapns 库之后，aioapns 和 httpx 的 cert= 参数都不支持传密码，所以它会卡住等输入；在 PyCharm 这类无交互终端里则会一直阻塞，最终被系统 SIGKILL。
ck.pem 里同时包含 BEGIN CERTIFICATE 和 BEGIN ENCRYPTED PRIVATE KEY 两段，即证书 + 加密私钥合并文件。
需要改为无密码的证书
```shell
cd /Users/gaoyanliang/nsyy/nsyy-project/gylmodules/workstation/message/

# 1. 提取并解密私钥（用你原来的密码 gyl.2015）
openssl rsa -in ck.pem -out ck_nopass.key -passin pass:gyl.2015

# 2. 提取证书
openssl x509 -in ck.pem -out ck.crt

# 3. 合并成无密码 PEM
cat ck_nopass.key ck.crt > ck_nopass.pem

# 4. 清理中间文件
rm ck_nopass.key ck.crt

# 5. 验证：应直接输出 "RSA key ok"，不再提示 Enter PEM pass phrase
openssl rsa -in ck_nopass.pem -check -noout

# 生成后的使用方式，把 get_apns_client() 里的 cert= 指向新文件：

python
pem_path = os.path.join(script_dir, "ck_nopass.pem")
APNS_CLIENT = httpx.Client(
    http2=True,
    cert=pem_path,
    timeout=httpx.Timeout(10.0, connect=5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
)
```



发送测试推送

    可以使用命令行工具如 curl 或专用工具（如 Pusher、Postman）
    示例 cURL 命令（开发环境）：

```shell
curl -v \
-d '{"aps":{"alert":"Test push notification","sound":"default"}}' \
-H "apns-topic: YOUR_BUNDLE_ID" \
-H "apns-push-type: alert" \
-H "apns-priority: 10" \
--http2 \
--cert /path/to/cert.pem \
https://api.development.push.apple.com/3/device/DEVICE_TOKEN
```


生成不需要密码的证书

```shell
1. 先把所有证书文件备份一份到 /Users/gaoyanliang/nsyy/ios/配置推送证书/back

然后 

步骤 1：解密私钥（如果加密）（输入原始密码）
openssl rsa -in PushKey.pem -out PushKey_unencrypted.pem

步骤 2：重新合并文件
# 合并证书 + 无密码私钥
cat PushCert.pem PushKey_unencrypted.pem > ck1_fixed.pem

步骤 3：验证最终文件

# 检查证书
openssl x509 -in ck1_fixed.pem -noout -text

# 检查私钥
openssl rsa -in ck1_fixed.pem -check -noout

步骤 4：在代码中使用

from aioapns import APNs

apns = APNs(
    client_cert="ck1_fixed.pem",  # 使用修复后的文件
    use_sandbox=True,  # 开发环境=True，生产环境=False
)
```


## github 免登录

# 1. 检查是否已存在SSH密钥
ls ~/.ssh/id_rsa.pub

# 2. 如果没有，生成新的SSH密钥
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 3. 将公钥添加到GitHub
cat ~/.ssh/id_rsa.pub
# 复制输出内容，到GitHub Settings > SSH and GPG keys > New SSH key

# 4. 修改远程仓库URL为SSH格式
git remote set-url origin git@github.com:gaoyanliang/nsyy-project.git

# 5. 再次尝试推送
git push origin main



## 在眼科医院服务器上部署多个前端项目

sudo su (nsyy0601.)

进入 /var/www/ 创建对应项目的目录 （例如 dip）

然后将 index.html 放入对应目录

在 vim /etc/nginx/sites-available/default 中添加配置

```nginx.conf
# 添加一个子路径页面
        location = /dip {
                return 301 /dip/;
        }
        location /dip/ {
                alias /var/www/dip/;
                index index.html;
                try_files $uri $uri/ /dip/index.html =404;
        }
```

检查配置是否有问题

```shell
root@nsyy-yk:/var/www# nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
root@nsyy-yk:/var/www# 
```

reload nginx

sudo nginx -s reload





# 一下文件和目录数据 文件取号机服务实现
nsyy-project
    mz_business_window
    mz_doctor_window
    mz_pharmacy
    mz_summary
    outpatient_queue
    mz_main.py
    index.html

nohup python3 -u ./mz_main.py >> nohup_mz.log 2>&1 &


# 其他服务数据 OA GYL

nohup python3 -u ./main_gyl.py >> nohup.log 2>&1 &
    






