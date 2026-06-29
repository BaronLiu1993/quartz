from github import Auth, GithubIntegration
import base64
from service.constants import GITHUB_APP_PRIVATE_KEY_BASE64, GITHUB_APP_ID

def get_installation_token(installation_id: int)-> str:
    private_key = base64.b64decode(GITHUB_APP_PRIVATE_KEY_BASE64).decode("utf-8")
    app_auth = Auth.AppAuth(GITHUB_APP_ID,private_key)
    integration = GithubIntegration(auth= app_auth)
    installation_authorization = integration.get_access_token(installation_id)
    
    return installation_authorization.token

def get_installation_headers(installation_id: int)-> dict[str,str]:
    token = get_installation_token(installation_id)

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "quartz-webhook",
    }