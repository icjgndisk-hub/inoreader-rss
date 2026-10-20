from __future__ import annotations
import logging,time
from urllib.parse import urlsplit,urljoin
import requests
from protego import Protego
LOG=logging.getLogger('rss.http')

class FetchError(RuntimeError): pass
class Client:
    def __init__(self,config):
        self.config=config;self.session=requests.Session();self.session.headers.update({'User-Agent':config['user_agent'],'Accept-Language':'ja,en;q=0.5'})
        self.robots={};self.last={};self.requests=0
        self.deadline=time.monotonic()+config.get('run_budget_seconds',600)
    def _wait(self,host,delay=None):
        delay=max(self.config['request_delay'],delay or 0)
        time.sleep(max(0,self.last.get(host,0)+delay-time.monotonic()));self.last[host]=time.monotonic()
    def _request(self,url,check=True):
        if time.monotonic()>self.deadline: raise FetchError('run-time-budget-exceeded; deferred to next run')
        parsed=urlsplit(url)
        if parsed.scheme not in ('https','http') or not parsed.hostname: raise FetchError('invalid-url')
        delay=0
        if check:
            origin=f'{parsed.scheme}://{parsed.netloc}'
            if origin not in self.robots:
                try:
                    r=self._request(origin+'/robots.txt',False)
                    body=r.content;r.close()
                    if len(body)>512000: raise FetchError('robots-too-large')
                    if 'text/html' in r.headers.get('Content-Type',''): raise FetchError('robots-returned-html')
                    self.robots[origin]=Protego.parse(body.decode('utf-8','replace'))
                except requests.HTTPError as e:
                    # RFC 9309 2.3.1.3: robots.txt 4xx means unavailable, not Disallow.
                    # A 403 on the actual image/article still fails normally, without any bypass.
                    if 400<=e.response.status_code<500 and e.response.status_code!=429:
                        self.robots[origin]=Protego.parse('')
                    else: raise FetchError('robots-unavailable: '+str(e)) from e
            robot=self.robots[origin]
            if not robot.can_fetch(url,self.config['user_agent']): raise FetchError('robots-disallowed: '+url)
            delay=robot.crawl_delay(self.config['user_agent']) or 0
        for attempt in range(self.config['retries']):
            if time.monotonic()>self.deadline: raise FetchError('run-time-budget-exceeded; deferred to next run')
            self._wait(parsed.netloc,delay)
            try:
                r=self.session.get(url,timeout=(8,self.config['request_timeout']),stream=True,allow_redirects=False);self.requests+=1
                if r.is_redirect:
                    target=urljoin(url,r.headers['Location']);r.close()
                    if target==url: raise FetchError('redirect-loop')
                    # Redirection is checked as a fresh URL, without credentials.
                    return self._redirect(target,check)
                if r.status_code==429 or r.status_code in (500,502,503,504):
                    if attempt+1<self.config['retries']:
                        retry=r.headers.get('Retry-After','');r.close()
                        try: wait=float(retry)
                        except ValueError: wait=2**(attempt+1)
                        # Long cooldowns are deferred to the next scheduled execution.
                        if wait>30: raise FetchError('retry-deferred: '+url)
                        time.sleep(max(wait,1));continue
                r.raise_for_status();return r
            except (requests.Timeout,requests.ConnectionError):
                if attempt+1==self.config['retries']: raise
                time.sleep(2**attempt)
        raise FetchError('retries-exhausted')
    def _redirect(self,url,check):
        self._redirect_depth=getattr(self,'_redirect_depth',0)+1
        try:
            if self._redirect_depth>5: raise FetchError('too-many-redirects')
            return self._request(url,check)
        finally: self._redirect_depth-=1
    def stream(self,url): return self._request(url)
    def get(self,url):
        with self._request(url) as r:
            parts=[];size=0
            for b in r.iter_content(65536):
                size+=len(b)
                if size>12*1024*1024: raise FetchError('response-too-large')
                parts.append(b)
            return b''.join(parts)
