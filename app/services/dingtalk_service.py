import time
from urllib.parse import urlencode

import requests


class DingTalkAuthError(RuntimeError):
    pass


class DingTalkAuthService:
    AUTH_URL = 'https://oapi.dingtalk.com/connect/qrconnect'
    SNS_USER_INFO_URL = 'https://oapi.dingtalk.com/sns/getuserinfo_bycode'
    APP_TOKEN_URL = 'https://api.dingtalk.com/v1.0/oauth2/accessToken'
    APPROVAL_CREATE_URL = 'https://api.dingtalk.com/v1.0/workflow/processInstances'
    UNIONID_LOOKUP_URL = 'https://oapi.dingtalk.com/topapi/user/getbyunionid'
    USER_DETAIL_URL = 'https://oapi.dingtalk.com/topapi/v2/user/get'

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self._app_access_token = None
        self._app_token_expires_at = 0

    def build_authorize_url(self, state):
        query = urlencode({
            'redirect_uri': self.config['DINGTALK_REDIRECT_URI'],
            'response_type': 'code',
            'appid': self.config['DINGTALK_CLIENT_ID'],
            'scope': self.config.get('DINGTALK_SCOPE') or 'snsapi_login',
            'state': state,
        })
        return f'{self.AUTH_URL}?{query}'

    def exchange_code_for_user(self, code):
        sns_data = self._post_json(
            self.SNS_USER_INFO_URL,
            {'tmp_auth_code': code},
            auth=(self.config['DINGTALK_CLIENT_ID'], self.config['DINGTALK_CLIENT_SECRET']),
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
            f'{self.UNIONID_LOOKUP_URL}?access_token={self.get_app_access_token()}',
            {'unionid': union_id},
        )
        result = data.get('result') or {}
        return result.get('userid') or result.get('userId')

    def get_user_detail(self, user_id):
        data = self._post_json(
            f'{self.USER_DETAIL_URL}?access_token={self.get_app_access_token()}',
            {'userid': user_id, 'language': 'zh_CN'},
        )
        return data.get('result') or {}

    def create_approval_instance(self, originator_user_id, process_code, dept_id, agent_id, form_values):
        payload = {
            'originatorUserId': originator_user_id,
            'processCode': process_code,
            'deptId': dept_id,
            'microappAgentId': agent_id,
            'formComponentValues': form_values,
        }
        data = self._post_json(
            self.APPROVAL_CREATE_URL,
            payload,
            headers={'x-acs-dingtalk-access-token': self.get_app_access_token()},
        )
        instance_id = data.get('instanceId') or data.get('processInstanceId')
        if not instance_id:
            raise DingTalkAuthError(f'DingTalk approval response missing instanceId: {data}')
        return instance_id, data

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

    def _get_json(self, url, headers=None):
        response = requests.get(url, headers=headers or {}, timeout=15)
        return self._parse_response(response)

    def _post_json(self, url, payload, auth=None, headers=None):
        response = requests.post(url, json=payload, auth=auth, headers=headers or {}, timeout=15)
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
