import base64
import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlencode

import requests
from flask import current_app


class DingTalkAuthError(RuntimeError):
    pass


class DingTalkAuthService:
    OAUTH2_AUTH_URL = 'https://login.dingtalk.com/oauth2/auth'
    OAUTH2_USER_TOKEN_URL = 'https://api.dingtalk.com/v1.0/oauth2/userAccessToken'
    OAUTH2_USER_ME_URL = 'https://api.dingtalk.com/v1.0/contact/users/me'
    SNS_AUTH_URL = 'https://oapi.dingtalk.com/connect/qrconnect'
    SNS_USER_INFO_URL = 'https://oapi.dingtalk.com/sns/getuserinfo_bycode'
    OAPI_TOKEN_URL = 'https://oapi.dingtalk.com/gettoken'
    APP_TOKEN_URL = 'https://api.dingtalk.com/v1.0/oauth2/accessToken'
    APPROVAL_CREATE_URL = 'https://api.dingtalk.com/v1.0/workflow/processInstances'
    OAPI_APPROVAL_CREATE_URL = 'https://oapi.dingtalk.com/topapi/processinstance/create'
    APPROVAL_INSTANCE_IDS_URL = 'https://api.dingtalk.com/v1.0/workflow/processes/instanceIds/query'
    APPROVAL_MANAGED_TEMPLATES_URL = 'https://api.dingtalk.com/v1.0/workflow/processes/managements/templates'
    UNIONID_LOOKUP_URL = 'https://oapi.dingtalk.com/topapi/user/getbyunionid'
    USER_DETAIL_URL = 'https://oapi.dingtalk.com/topapi/v2/user/get'

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self._app_access_token = None
        self._app_token_expires_at = 0
        self._oapi_access_token = None
        self._oapi_token_expires_at = 0

    def build_authorize_url(self, state):
        if self.config.get('DINGTALK_AUTH_FLOW') == 'legacy_sns':
            return self.build_legacy_sns_authorize_url(state)

        query = urlencode({
            'redirect_uri': self.config['DINGTALK_REDIRECT_URI'],
            'response_type': 'code',
            'client_id': self.config['DINGTALK_CLIENT_ID'],
            'scope': self.config.get('DINGTALK_SCOPE') or 'openid',
            'state': state,
            'prompt': 'consent',
        })
        return f'{self.OAUTH2_AUTH_URL}?{query}'

    def build_legacy_sns_authorize_url(self, state):
        query = urlencode({
            'redirect_uri': self.config['DINGTALK_REDIRECT_URI'],
            'response_type': 'code',
            'appid': self.config['DINGTALK_CLIENT_ID'],
            'scope': 'snsapi_login',
            'state': state,
        })
        return f'{self.SNS_AUTH_URL}?{query}'

    def exchange_code_for_user(self, code):
        if self.config.get('DINGTALK_AUTH_FLOW') == 'legacy_sns':
            return self.exchange_legacy_sns_code_for_user(code)

        token_data = self._post_json(
            self.OAUTH2_USER_TOKEN_URL,
            {
                'clientId': self.config['DINGTALK_CLIENT_ID'],
                'clientSecret': self.config['DINGTALK_CLIENT_SECRET'],
                'code': code,
                'grantType': 'authorization_code',
            },
        )
        user_access_token = token_data.get('accessToken')
        if not user_access_token:
            raise DingTalkAuthError(f'DingTalk OAuth2 token response missing accessToken: {token_data}')

        user_info = self._get_json(
            self.OAUTH2_USER_ME_URL,
            headers={'x-acs-dingtalk-access-token': user_access_token},
        )
        user_id = user_info.get('userId') or user_info.get('userid')
        union_id = user_info.get('unionId') or user_info.get('unionid')
        if not user_id and union_id:
            user_id = self.get_user_id_by_union_id(union_id)

        if not user_id:
            raise DingTalkAuthError(f'DingTalk OAuth2 user response missing userId: {user_info}')

        return {
            'user_id': user_id,
            'union_id': union_id,
            'name': user_info.get('nick') or user_info.get('name') or user_info.get('mobile') or user_id,
            'avatar': user_info.get('avatarUrl') or user_info.get('avatar'),
            'raw': {'oauth2': user_info},
        }

    def exchange_legacy_sns_code_for_user(self, code):
        sns_data = self._post_json(
            self.SNS_USER_INFO_URL,
            {'tmp_auth_code': code},
            params=self._sns_signature_params(),
        )
        user_info = sns_data.get('user_info') or sns_data.get('userInfo') or {}
        union_id = user_info.get('unionId') or user_info.get('unionid')
        if not union_id:
            raise DingTalkAuthError(f'DingTalk SNS response missing unionId: {sns_data}')

        user_id = self.get_user_id_by_union_id(union_id)
        if not user_id:
            raise DingTalkAuthError(f'DingTalk unionId lookup response missing userId, unionId={union_id}')

        detail = self.get_user_detail(user_id)

        return {
            'user_id': user_id,
            'union_id': union_id,
            'name': detail.get('name') or user_info.get('nick') or user_id,
            'avatar': detail.get('avatar') or user_info.get('avatarUrl') or user_info.get('avatar'),
            'raw': {'sns': user_info, 'detail': detail},
        }

    def get_user_id_by_union_id(self, union_id):
        data = self._post_json(
            f'{self.UNIONID_LOOKUP_URL}?access_token={self.get_oapi_access_token()}',
            {'unionid': union_id},
        )
        result = data.get('result') or {}
        return result.get('userid') or result.get('userId')

    def get_user_detail(self, user_id):
        data = self._post_json(
            f'{self.USER_DETAIL_URL}?access_token={self.get_oapi_access_token()}',
            {'userid': user_id, 'language': 'zh_CN'},
        )
        return data.get('result') or {}

    def create_approval_instance(
        self,
        originator_user_id,
        process_code,
        dept_id,
        agent_id,
        form_values,
        target_select_actioners=None,
    ):
        payload = {
            'originatorUserId': originator_user_id,
            'processCode': process_code,
            'deptId': dept_id,
            'microappAgentId': agent_id,
            'formComponentValues': form_values,
            'RequestId': uuid.uuid4().hex,
        }
        if target_select_actioners:
            payload['targetSelectActioners'] = target_select_actioners
        current_app.logger.info(
            "DingTalk approval create payload: %s",
            json.dumps(payload, ensure_ascii=False),
        )
        data = self._post_json(
            self.APPROVAL_CREATE_URL,
            payload,
            headers={'x-acs-dingtalk-access-token': self.get_app_access_token()},
        )
        instance_id = data.get('instanceId') or data.get('processInstanceId')
        if not instance_id:
            raise DingTalkAuthError(f'DingTalk approval response missing instanceId: {data}')
        return instance_id, data

    def create_approval_instance_oapi_direct(
        self,
        originator_user_id,
        process_code,
        dept_id,
        agent_id,
        form_values,
        approvers_v2=None,
        cc_list=None,
        cc_position='FINISH',
    ):
        payload = {
            'originator_user_id': originator_user_id,
            'process_code': process_code,
            'dept_id': dept_id,
            'agent_id': agent_id,
            'form_component_values': form_values,
        }
        if approvers_v2:
            payload['approvers_v2'] = approvers_v2
        if cc_list:
            payload['cc_list'] = ','.join(cc_list)
            payload['cc_position'] = cc_position

        current_app.logger.info(
            "DingTalk oapi approval create payload: %s",
            json.dumps(payload, ensure_ascii=False),
        )
        data = self._post_json(
            f'{self.OAPI_APPROVAL_CREATE_URL}?access_token={self.get_oapi_access_token()}',
            payload,
        )
        instance_id = data.get('process_instance_id') or data.get('processInstanceId')
        if not instance_id:
            raise DingTalkAuthError(f'DingTalk oapi approval response missing process_instance_id: {data}')
        return instance_id, data

    def forecast_approval_process(self, originator_user_id, process_code, dept_id, form_values):
        payload = {
            'userId': originator_user_id,
            'processCode': process_code,
            'deptId': dept_id,
            'formComponentValues': form_values,
            'RequestId': uuid.uuid4().hex,
        }
        return self._post_json(
            'https://api.dingtalk.com/v1.0/workflow/processes/forecast',
            payload,
            headers={'x-acs-dingtalk-access-token': self.get_app_access_token()},
        )

    def list_manageable_approval_templates(self, user_id):
        data = self._get_json(
            self.APPROVAL_MANAGED_TEMPLATES_URL,
            headers={'x-acs-dingtalk-access-token': self.get_app_access_token()},
            params={'userId': user_id},
        )
        return data.get('result') or []

    def query_approval_instance_ids(self, process_code, start_time_ms, end_time_ms=None, user_ids=None, statuses=None, max_pages=50):
        instance_ids = []
        next_token = None
        pages = 0
        while pages < max_pages:
            payload = {
                'processCode': process_code,
                'startTime': start_time_ms,
                'maxResults': 20,
                'nextToken': next_token or 0,
            }
            if end_time_ms:
                payload['endTime'] = end_time_ms
            if user_ids:
                payload['userIds'] = user_ids
            if statuses:
                payload['statuses'] = statuses

            data = self._post_json(
                self.APPROVAL_INSTANCE_IDS_URL,
                payload,
                headers={'x-acs-dingtalk-access-token': self.get_app_access_token()},
            )
            result = data.get('result') or {}
            instance_ids.extend(result.get('list') or [])
            next_token = result.get('nextToken')
            pages += 1
            if not next_token:
                break

        return instance_ids

    def get_approval_instance(self, process_instance_id):
        data = self._get_json(
            self.APPROVAL_CREATE_URL,
            headers={'x-acs-dingtalk-access-token': self.get_app_access_token()},
            params={'processInstanceId': process_instance_id},
        )
        return data.get('result') or data

    def find_approval_instance_by_business_id(self, business_id, process_code, start_time_ms, end_time_ms=None, user_ids=None, statuses=None):
        instance_ids = self.query_approval_instance_ids(
            process_code=process_code,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            user_ids=user_ids,
            statuses=statuses,
        )
        for instance_id in instance_ids:
            detail = self.get_approval_instance(instance_id)
            if str(detail.get('businessId') or '') == str(business_id):
                return detail, instance_ids
        return None, instance_ids

    def get_app_access_token(self):
        if self._app_access_token and time.time() < self._app_token_expires_at - 300:
            return self._app_access_token

        data = self._post_json(
            self.APP_TOKEN_URL,
            {
                'appKey': self.config['DINGTALK_CLIENT_ID'],
                'appSecret': self.config['DINGTALK_CLIENT_SECRET'],
            },
        )
        token = data.get('accessToken')
        if not token:
            raise DingTalkAuthError(f'DingTalk app token response missing accessToken: {data}')

        self._app_access_token = token
        self._app_token_expires_at = time.time() + int(data.get('expireIn', 7200))
        return token

    def get_oapi_access_token(self):
        if self._oapi_access_token and time.time() < self._oapi_token_expires_at - 300:
            return self._oapi_access_token

        data = self._get_json(
            self.OAPI_TOKEN_URL,
            params={
                'appkey': self.config['DINGTALK_CLIENT_ID'],
                'appsecret': self.config['DINGTALK_CLIENT_SECRET'],
            },
        )
        token = data.get('access_token')
        if not token:
            raise DingTalkAuthError(f'DingTalk oapi token response missing access_token: {data}')

        self._oapi_access_token = token
        self._oapi_token_expires_at = time.time() + int(data.get('expires_in', 7200))
        return token

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

    def _get_json(self, url, headers=None, params=None):
        response = requests.get(url, headers=headers or {}, params=params or {}, timeout=15)
        return self._parse_response(response)

    def _post_json(self, url, payload, auth=None, headers=None, params=None):
        response = requests.post(
            url,
            json=payload,
            auth=auth,
            headers=headers or {},
            params=params or {},
            timeout=15,
        )
        return self._parse_response(response)

    def _parse_response(self, response):
        try:
            data = response.json()
        except ValueError as exc:
            raise DingTalkAuthError(f'DingTalk returned non-JSON response: {response.text[:300]}') from exc

        if response.status_code >= 400:
            raise DingTalkAuthError(f'DingTalk HTTP {response.status_code}: {data}')

        if data.get('errcode') not in (None, 0):
            raise DingTalkAuthError(f'DingTalk API error: {data}')
        return data
