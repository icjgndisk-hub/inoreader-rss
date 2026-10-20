import json,os
from pathlib import Path
p=Path('reports/latest-run.json')
if not p.exists():raise SystemExit('No run report')
d=json.loads(p.read_text());out=['| Site | State | Feed | Images | Verified | Pending |','|---|---|---:|---:|---:|---:|']
for k,r in d['sites'].items():out.append(f'| {k} | {r.get("status")} | {r.get("feed_items",0)} | {r.get("images_in_feed",0)} | {r.get("verified_images_in_feed",0)} | {r.get("pending_metadata",0)} |')
report='\n'.join(out)+'\n';print(report)
if os.getenv('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(report)
