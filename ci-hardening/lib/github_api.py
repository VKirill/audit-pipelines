"""Wrapper around `gh` CLI for safe read-only GitHub API access."""
import json, subprocess, shutil


def gh_available():
    return shutil.which('gh') is not None


def gh_authenticated():
    if not gh_available(): return False
    try:
        r = subprocess.run(['gh', 'auth', 'status'], capture_output=True, timeout=5)
        return r.returncode == 0
    except: return False


def gh_api(endpoint, method='GET'):
    """Run `gh api <endpoint>` and return parsed JSON or None."""
    if method != 'GET':
        return None  # safety: only GET
    if not gh_authenticated():
        return None
    try:
        r = subprocess.run(['gh', 'api', endpoint], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout) if r.stdout.strip() else None
    except: return None


def detect_repo(project_root):
    """Get owner/repo from git remote origin."""
    try:
        r = subprocess.run(['git', '-C', str(project_root), 'remote', 'get-url', 'origin'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0: return None, None
        url = r.stdout.strip()
        import re
        m = re.search(r'github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$', url)
        if m: return m.group(1), m.group(2)
    except: pass
    return None, None


def get_branch_protection(owner, repo, branch='main'):
    return gh_api(f'repos/{owner}/{repo}/branches/{branch}/protection')


def get_security_features(owner, repo):
    """Returns dict of enabled security features."""
    repo_data = gh_api(f'repos/{owner}/{repo}')
    if not repo_data: return {}
    return {
        'dependabot_alerts': bool(repo_data.get('security_and_analysis', {}).get('dependabot_security_updates', {}).get('status') == 'enabled'),
        'secret_scanning': bool(repo_data.get('security_and_analysis', {}).get('secret_scanning', {}).get('status') == 'enabled'),
        'secret_scanning_push_protection': bool(repo_data.get('security_and_analysis', {}).get('secret_scanning_push_protection', {}).get('status') == 'enabled'),
        'visibility': repo_data.get('visibility', 'unknown'),
        'default_branch': repo_data.get('default_branch', 'main'),
    }


def list_secrets(owner, repo):
    """Returns list of secret names (without values)."""
    data = gh_api(f'repos/{owner}/{repo}/actions/secrets')
    if not data: return []
    return [s['name'] for s in data.get('secrets', [])]


def resolve_action_sha(action_owner, action_repo, ref):
    """Resolve action@<ref> to commit SHA via gh api."""
    # First try as tag
    data = gh_api(f'repos/{action_owner}/{action_repo}/git/refs/tags/{ref}')
    if data and data.get('object'):
        if data['object']['type'] == 'commit':
            return data['object']['sha']
        if data['object']['type'] == 'tag':
            tag_data = gh_api(f"repos/{action_owner}/{action_repo}/git/tags/{data['object']['sha']}")
            if tag_data: return tag_data['object']['sha']
    # Try as branch
    data = gh_api(f'repos/{action_owner}/{action_repo}/git/refs/heads/{ref}')
    if data and data.get('object'):
        return data['object']['sha']
    return None
