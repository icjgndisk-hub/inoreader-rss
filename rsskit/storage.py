import json,os,shutil
from pathlib import Path

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()==data:return False
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path);return True

def load(path):
    path=Path(path)
    if not path.exists():return {'version':2,'items':{}}
    # A corrupt state is a hard error. Never replace it with an empty history.
    state=json.loads(path.read_text('utf-8'))
    if state.get('version')!=2 or not isinstance(state.get('items'),dict):raise ValueError('unsupported/corrupt state: '+str(path))
    return state

def save(path,state):
    raw=(json.dumps(state,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
    if Path(path).exists():
        # Validate the previous version before keeping it as a recovery backup.
        load(path);atomic(str(path)+'.bak',Path(path).read_bytes())
    atomic(path,raw)
