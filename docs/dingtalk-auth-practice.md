# 钉钉认证接入实践：第三方网站扫码登录与企业内用户身份转换

## 版本说明

当前分支实现的是钉钉新版 OAuth2 登录链路，也就是：

```text
login.dingtalk.com/oauth2/auth
api.dingtalk.com/v1.0/oauth2/userAccessToken
api.dingtalk.com/v1.0/contact/users/me
```

新版 OAuth2 调用 `contact/users/me` 时需要 `Contact.User.Read` 权限。这个权限既要在钉钉开放平台的应用权限管理里申请，也要在授权 URL 的 `scope` 中请求：

```env
DINGTALK_SCOPE=openid Contact.User.Read
```

旧版 SNS 扫码登录链路仍保留为可选实现，可以通过环境变量切回：

```env
DINGTALK_AUTH_FLOW=legacy_sns
```

旧版 SNS 链路是：

```text
oapi.dingtalk.com/connect/qrconnect
oapi.dingtalk.com/sns/getuserinfo_bycode
oapi.dingtalk.com/gettoken
oapi.dingtalk.com/topapi/user/getbyunionid
```

新版 OAuth2 和旧版 SNS 不应在同一次登录流程里混用。当前分支默认使用 `DINGTALK_AUTH_FLOW=oauth2`。

## 背景

很多企业内部系统并不是直接运行在钉钉工作台里，而是一个独立 Web 网站。例如本项目是一个报销单据处理系统，用户在网页中上传发票、行程单，系统识别金额与明细后，再发起钉钉 OA 审批。

这类场景最容易混淆的是：钉钉提供了很多“免登”“扫码登录”“账号登录”能力，它们看起来都能让用户登录，但适用场景和最终拿到的身份信息并不一样。

本文记录本项目采用的实践：用户访问第三方网页，通过钉钉扫码完成身份验证，服务端拿到企业内 `userId`，后续用这个 `userId` 作为 OA 审批发起人。

## 先分清两件事

钉钉接入通常分成两层：

```text
认证登录：确认当前访问网页的人是谁
业务接口：用应用权限调用钉钉能力，例如发起 OA 审批
```

扫码登录只能解决第一件事：识别用户身份。

它不会自动帮你发起审批，也不会自动把数据写入某个钉钉应用。发起审批仍然需要后端用应用的 `access_token` 调用 OA 审批接口。

## 常见接入类型

### 企业内部应用免登

适用于企业内部应用，用户从钉钉工作台、钉钉客户端或企业内部应用入口打开页面。

典型流程是：

```text
钉钉客户端打开应用页面
前端调用钉钉 JSAPI 获取免登码
后端用免登码换企业内 userId
```

适合应用深度嵌在钉钉内的场景。

需要的信息通常包括：

```text
企业内部应用 AppKey / AppSecret
AgentId
JSAPI 安全域名
后端换取 userId 的接口权限
```

### 第三方企业应用免登

适用于 SaaS 应用服务多个企业。每个企业安装并授权应用后，第三方服务商按授权企业维度维护 `corpId`、授权信息、企业 token。

典型使用者是软件厂商，而不是单个企业自用系统。

需要的信息通常包括：

```text
SuiteKey / SuiteSecret
授权企业 corpId
企业授权 token
回调事件配置
应用市场或定向安装配置
```

### 应用管理后台免登

适用于应用管理后台页面，例如开发者或管理员从钉钉开放平台、应用管理入口进入你的管理页面。

它解决的是“当前管理应用的人是谁”，不是普通员工在业务系统里提交报销。

### 钉钉内免登第三方网站

适用于用户在钉钉客户端内打开一个第三方网站链接。网站可以借助钉钉运行环境拿到免登信息。

这种方式依赖用户从钉钉内打开页面。如果用户是在普通浏览器里访问网站，则不适用。

### 扫码登录第三方网站

适用于独立 Web 网站。用户在普通浏览器打开网站，点击“钉钉登录”，跳转到钉钉扫码页面，扫码确认后回到网站。

本项目采用的就是这种方式。

典型流程是：

```text
用户访问第三方网站
服务端生成扫码登录 URL
用户用钉钉扫码
钉钉回调 redirect_uri，携带临时 code
服务端用 code 获取 unionId
服务端用 unionId 换企业内 userId
服务端写入 session
```

需要的信息包括：

```text
Client ID，也就是原 AppKey
Client Secret，也就是原 AppSecret
登录回调域名
完整 redirect_uri
通讯录相关权限
```

### 使用钉钉账号登录第三方网站

这个能力更偏“用钉钉账号作为身份源登录网站”。如果你的业务需要企业内员工身份，例如作为 OA 审批发起人，最终仍然需要拿到企业内 `userId`。

因此，本项目没有采用纯钉钉账号登录，而是采用“扫码登录第三方网站 + unionId 换企业 userId”的方式。

## 本项目为什么选择扫码登录第三方网站

本项目的入口是：

```text
http://work.bdcatek.com:50010/
```

它不是钉钉工作台里的内嵌应用，而是一个独立 Web 服务。用户可能从浏览器直接访问，因此适合使用“扫码登录第三方网站”。

系统需要的最终身份不是昵称、手机号或头像，而是企业内 `userId`。原因是发起 OA 审批时需要：

```json
{
  "originatorUserId": "企业内 userId"
}
```

所以认证链路必须完成：

```text
code -> unionId -> userId
```

## 钉钉后台需要配置什么

### 登录回调域名

钉钉后台通常要求配置“登录回调域名”。这里填域名：

```text
work.bdcatek.com
```

不要填完整 URL。

代码中的 `redirect_uri` 才是完整地址：

```text
http://work.bdcatek.com:50010/auth/dingtalk/callback
```

钉钉会校验 `redirect_uri` 里的域名是否和后台配置一致。也就是说：

```text
redirect_uri 的域名部分：work.bdcatek.com
后台登录回调域名：work.bdcatek.com
```

二者必须一致。

### 应用信息

本项目需要配置：

```env
DINGTALK_CLIENT_ID=应用 AppKey
DINGTALK_CLIENT_SECRET=应用 AppSecret
DINGTALK_AGENT_ID=企业内部应用 AgentId
```

扫码登录本身主要使用 `Client ID / Client Secret / redirect_uri`。

`AgentId` 后续发起审批实例时使用。

### 权限

扫码登录后只能拿到临时 `code`。要换成企业内 `userId`，还需要通讯录相关权限。

本项目至少依赖：

```text
根据 unionId 获取 userId
根据 userId 获取用户详情
OA 审批发起能力
```

如果权限不足，常见表现是登录成功回调了，但服务端换 `userId` 或获取用户详情时报错。

## 本项目的环境变量

项目的本地配置文件在：

```text
bdca_order/.env
```

关键配置如下：

```env
DINGTALK_AUTH_ENABLED=true
DINGTALK_AGENT_ID=4641708513
DINGTALK_CLIENT_ID=dingxxxxxxxxxxxx
DINGTALK_CLIENT_SECRET=replace_with_secret
DINGTALK_REDIRECT_URI=http://work.bdcatek.com:50010/auth/dingtalk/callback
DINGTALK_SCOPE=snsapi_login
DINGTALK_AUTH_PUBLIC_HOSTS=work.bdcatek.com:50010
```

其中：

```text
DINGTALK_AUTH_ENABLED
是否启用钉钉认证。

DINGTALK_REDIRECT_URI
扫码确认后钉钉回调的完整地址。

DINGTALK_AUTH_PUBLIC_HOSTS
通过这些 Host 访问时强制钉钉登录。
```

本项目当前使用 Nginx Proxy Manager 的 Stream 转发。Stream 是 TCP 转发，不会把真实外网客户端 IP 传给 Flask。Flask 看到的来源 IP 是 NPM 机器的内网 IP。

因此本项目不能单纯按 `remote_addr` 判断外网用户，而是采用：

```text
访问 work.bdcatek.com:50010 -> 强制登录
访问 192.168.10.100:8000 -> 内网免登录
```

## 扫码登录的完整链路

### 1. 外网访问触发登录

用户访问：

```text
http://work.bdcatek.com:50010/
```

Flask 判断请求 Host 是：

```text
work.bdcatek.com:50010
```

如果 session 里没有 `dingtalk_user_id`，则重定向到：

```text
/auth/dingtalk/start
```

相关代码在：

```text
app/routes.py
```

核心逻辑：

```python
def _requires_dingtalk_login():
    if not current_app.config.get('DINGTALK_AUTH_ENABLED'):
        return False
    if session.get('dingtalk_user_id'):
        return False
    if _is_public_entry_host():
        return True
    return not _is_internal_ip(_request_client_ip())
```

### 2. 服务端生成扫码登录 URL

服务端生成钉钉扫码登录地址：

```text
https://oapi.dingtalk.com/connect/qrconnect
```

参数包括：

```text
appid=AppKey
response_type=code
scope=snsapi_login
state=随机字符串
redirect_uri=完整回调地址
```

示例：

```text
https://oapi.dingtalk.com/connect/qrconnect?appid=dingxxx&response_type=code&scope=snsapi_login&state=xxx&redirect_uri=http%3A%2F%2Fwork.bdcatek.com%3A50010%2Fauth%2Fdingtalk%2Fcallback
```

`state` 用来防止重放攻击。服务端生成后存入 session，回调时必须一致。

### 3. 钉钉回调网站

用户扫码确认后，钉钉回调：

```text
http://work.bdcatek.com:50010/auth/dingtalk/callback?code=xxx&state=xxx
```

后端检查：

```text
是否有 code
state 是否和 session 中保存的一致
```

通过后，开始换取用户身份。

### 4. code 换 unionId

扫码登录第三方网站使用接口：

```text
POST https://oapi.dingtalk.com/sns/getuserinfo_bycode
```

请求体：

```json
{
  "tmp_auth_code": "钉钉回调给的 code"
}
```

这个接口不能简单用 Basic Auth。它需要在 URL query 中带：

```text
accessKey
timestamp
signature
```

`signature` 的生成方式是：

```text
用 AppSecret 对 timestamp 做 HmacSHA256
再 base64 编码
```

本项目核心代码：

```python
def _sns_signature_params(self):
    timestamp = str(int(time.time() * 1000))
    digest = hmac.new(
        self.config['DINGTALK_CLIENT_SECRET'].encode('utf-8'),
        timestamp.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(digest).decode('utf-8')
    return {
        'accessKey': self.config['DINGTALK_CLIENT_ID'],
        'timestamp': timestamp,
        'signature': signature,
    }
```

成功后返回用户的 `unionId`。

### 5. unionId 换企业内 userId

`unionId` 是钉钉账号维度的身份。发起企业 OA 审批需要企业内 `userId`。

本项目调用：

```text
POST https://oapi.dingtalk.com/topapi/user/getbyunionid
```

请求体：

```json
{
  "unionid": "用户 unionId"
}
```

这里需要注意 token 类型。

老版 `oapi.dingtalk.com/topapi/...` 接口需要老式 token：

```text
GET https://oapi.dingtalk.com/gettoken?appkey=xxx&appsecret=xxx
```

不能把新版：

```text
POST https://api.dingtalk.com/v1.0/oauth2/accessToken
```

拿到的 token 混用到老版 `oapi` 接口上，否则容易出现：

```text
40014 不合法的access_token
```

本项目现在区分了两套 token：

```text
oapi token
用于 user/getbyunionid、topapi/v2/user/get

api.dingtalk.com token
用于新版 OA 审批实例接口
```

### 6. userId 写入 session

拿到 `userId` 后，服务端写入 session：

```python
session['dingtalk_user_id'] = user['user_id']
session['dingtalk_user'] = {
    'user_id': user.get('user_id'),
    'union_id': user.get('union_id'),
    'name': user.get('name'),
    'avatar': user.get('avatar'),
}
```

后续请求只要 session 中存在 `dingtalk_user_id`，就认为用户已登录。

## 和 OA 审批的关系

认证完成后，系统知道“当前用户是谁”。接下来才能发起 OA 审批。

本项目调用新版审批实例接口：

```text
POST https://api.dingtalk.com/v1.0/workflow/processInstances
```

核心参数：

```json
{
  "originatorUserId": "扫码登录得到的 userId",
  "processCode": "差旅报销模板 processCode",
  "deptId": -1,
  "microappAgentId": 4641708513,
  "formComponentValues": [
    {"name": "报销金额", "value": "128.00"},
    {"name": "报销明细", "value": "网约车 xxx ¥128.00"},
    {"name": "备注", "value": "系统自动识别 1 个报销条目，总金额 ¥128.00"}
  ]
}
```

这里的 `originatorUserId` 就来自扫码登录。

`processCode` 来自你们自己的 OA 审批模板。

## processCode 怎么查

有两种方式。

### 后台页面查看

在钉钉 OA 审批后台找到对应模板，例如“差旅报销”，进入编辑或配置页面。部分版本会显示模板 code，或者 URL 中能看到 `PROC-...`。

### 接口查看

本项目提供了辅助接口：

```text
GET /api/dingtalk/approval-templates
```

公网访问：

```text
http://work.bdcatek.com:50010/api/dingtalk/approval-templates
```

这个接口会列出当前登录用户可管理的审批模板。返回结果中可查看 `processCode`。

注意：扫码用户需要对该审批模板有管理权限，否则可能返回空列表或权限错误。

## 字段映射

钉钉审批表单里的字段名必须和接口传入的组件名完全一致。

本项目通过环境变量配置字段映射：

```env
DINGTALK_TRAVEL_FIELD_MAP={"total_amount":"报销金额","details":"报销明细","remark":"备注"}
```

左侧是系统内部汇总字段：

```text
total_amount
报销总金额

details
报销明细文本

remark
备注

taxi_amount
网约车金额

hotel_amount
酒店金额

train_amount
火车票金额

flight_amount
机票金额
```

右侧是钉钉 OA 审批模板组件名。

例如你的模板字段叫：

```text
费用总额
费用明细
申请说明
```

则配置为：

```env
DINGTALK_TRAVEL_FIELD_MAP={"total_amount":"费用总额","details":"费用明细","remark":"申请说明"}
```

## 验证流程

### 1. 验证服务是否启动

本地：

```text
http://127.0.0.1:8000/api/auth/status
```

应看到：

```json
{
  "auth_enabled": true,
  "internal_ip": true
}
```

### 2. 验证公网入口是否触发登录

访问：

```text
http://work.bdcatek.com:50010/
```

未登录时应跳转到：

```text
/auth/dingtalk/start
```

然后跳到钉钉扫码页面。

### 3. 验证扫码登录

扫码确认后应回到：

```text
/auth/dingtalk/callback
```

成功后回到首页。

再访问：

```text
http://work.bdcatek.com:50010/api/auth/status
```

应看到：

```json
{
  "logged_in": true,
  "user": {
    "user_id": "..."
  }
}
```

### 4. 验证模板 processCode

登录后访问：

```text
http://work.bdcatek.com:50010/api/dingtalk/approval-templates
```

找到“差旅报销”模板对应的 `processCode`，填入 `.env`：

```env
DINGTALK_TRAVEL_PROCESS_CODE=PROC-xxxx
```

重启服务。

### 5. 验证发起审批

上传发票或行程单，系统识别出结果后，点击：

```text
发起钉钉审批
```

成功后接口返回：

```json
{
  "success": true,
  "instance_id": "..."
}
```

本地会记录到：

```text
data/dingtalk_approval_instances.json
```

## 常见问题

### 40014 不合法的 access_token

常见原因是 token 类型混用。

老版 `oapi.dingtalk.com/topapi/...` 接口使用：

```text
https://oapi.dingtalk.com/gettoken
```

新版 `api.dingtalk.com/v1.0/...` 接口使用：

```text
https://api.dingtalk.com/v1.0/oauth2/accessToken
```

不能随意混用。

### sns/getuserinfo_bycode 一直失败

检查是否按文档生成了：

```text
accessKey
timestamp
signature
```

`signature` 不是 AppSecret 原文，也不是 Basic Auth。

### 回调提示无权限访问

检查后台登录回调域名和 `redirect_uri` 的域名是否一致。

后台配置：

```text
work.bdcatek.com
```

代码配置：

```text
http://work.bdcatek.com:50010/auth/dingtalk/callback
```

域名部分必须一致。

### 扫码能登录，但换不到 userId

检查：

```text
扫码用户是否属于当前企业
应用是否有通讯录权限
应用是否已发布
Client ID / Secret 是否来自同一个应用
```

### 查询不到 processCode

`/api/dingtalk/approval-templates` 查询的是当前用户可管理的审批模板。

如果返回空列表，常见原因是扫码用户不是该审批模板管理员。可以换管理员账号扫码，或在 OA 审批后台给当前用户模板管理权限。

## 本项目当前实现位置

认证与钉钉接口封装：

```text
app/services/dingtalk_service.py
```

登录、回调、访问拦截、发起审批接口：

```text
app/routes.py
```

前端“发起钉钉审批”按钮：

```text
app/templates/index.html
```

本地配置：

```text
.env
```

示例配置：

```text
env.example
```

## 总结

第三方网站接入钉钉扫码登录，本质上做了三件事：

```text
1. 让钉钉确认扫码的人是谁
2. 把钉钉账号身份 unionId 转成企业内 userId
3. 把 userId 写入网站自己的登录态
```

完成认证后，网站才能把这个 `userId` 用在企业业务接口里。例如本项目会把它作为 OA 审批的发起人：

```text
originatorUserId = 当前扫码登录用户的 userId
```

因此，扫码登录不是业务流程的终点，而是企业业务流程的身份入口。后续发起审批、查询审批状态、关联本地报销记录，都是建立在这个身份基础之上的。
