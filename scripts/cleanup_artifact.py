"""Delete only this completed deployment's temporary upload, never news/history."""
import os,requests
repo=os.environ['GH_REPOSITORY'];run=os.environ['GH_RUN_ID']
s=requests.Session();s.headers['Authorization']='Bearer '+os.environ['GH_TOKEN'];s.headers['Accept']='application/vnd.github+json'
r=s.get(f'https://api.github.com/repos/{repo}/actions/runs/{run}/artifacts',timeout=30);r.raise_for_status()
for a in r.json()['artifacts']:
    if a['name']=='github-pages' and a.get('workflow_run',{}).get('id')==int(run):
        r=s.delete(f'https://api.github.com/repos/{repo}/actions/artifacts/{int(a["id"])}',timeout=30);r.raise_for_status();print('Removed temporary deployment artifact')
