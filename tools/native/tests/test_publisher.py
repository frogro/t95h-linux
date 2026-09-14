import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('publisher',Path(__file__).resolve().parents[1]/'publisher.py')
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)

class PublisherTests(unittest.TestCase):
    def response(self,status,body,headers=''):
        return subprocess.CompletedProcess([],0 if status==200 else 1,f'HTTP/2.0 {status} Test\n{headers}\n{json.dumps(body)}','')
    @patch.object(pub.time,'sleep')
    @patch.object(pub.subprocess,'run')
    def test_retry_after(self,run,sleep):
        run.side_effect=[self.response(403,{'message':'secondary rate limit'},'Retry-After: 120\n'),self.response(200,{'id':1})]
        self.assertEqual(pub.GitHub('o/r').api('repos/o/r'),{'id':1});sleep.assert_called_once_with(121)
    def test_primary_and_backoff(self):
        self.assertEqual(pub.retry_delay({'x-ratelimit-remaining':'0','x-ratelimit-reset':'400'},0,now=100),301)
        self.assertEqual(pub.retry_delay({},3),480)
    @patch.object(pub.time,'sleep')
    @patch.object(pub.subprocess,'run')
    def test_permission_denial_not_retried(self,run,sleep):
        run.return_value=self.response(403,{'message':'Resource not accessible by integration'})
        with self.assertRaises(RuntimeError):pub.GitHub('o/r').api('repos/o/r')
        self.assertEqual(run.call_count,1);sleep.assert_not_called()
    @patch.object(pub.subprocess,'run')
    def test_ambiguous_upload_not_repeated(self,run):
        run.return_value=self.response(502,{'message':'server error'})
        with self.assertRaises(RuntimeError):pub.GitHub('o/r').api('https://uploads.github.com/test','POST',file=Path('asset'))
        self.assertEqual(run.call_count,1)
    def test_resume_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.apk';a.write_bytes(b'one')
            b=Path(tmp)/'b.apk';b.write_bytes(b'two')
            def asset(p):return dict(name=p.name,size=p.stat().st_size,digest=pub.digest(p),state='uploaded')
            client=pub.GitHub('o/r')
            release=dict(id=1,draft=True,upload_url='https://uploads.github.com/test{?name,label}')
            with patch.object(client,'api',side_effect=[release,asset(b),None]) as api,patch.object(client,'assets',side_effect=[{'a.apk':asset(a)},{'a.apk':asset(a),'b.apk':asset(b)}]):
                client.publish('tag',[a,b],'sha','title','notes')
                self.assertEqual(api.call_count,3)
                self.assertEqual(api.call_args_list[1].kwargs['file'],b)
                self.assertEqual(api.call_args_list[-1].args[1],'PATCH')
    def test_mismatch_and_public_incomplete_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.apk';a.write_bytes(b'one')
            for draft,assets in [(True,{'a.apk':dict(name='a.apk',size=3,state='uploaded',digest='sha256:wrong')}),(False,{})]:
                client=pub.GitHub('o/r')
                with patch.object(client,'api',return_value=dict(id=1,draft=draft)) as api,patch.object(client,'assets',return_value=assets):
                    with self.assertRaises(RuntimeError):client.publish('tag',[a],'sha','title','notes')
                    self.assertEqual(api.call_count,1)
    def test_pagination(self):
        client=pub.GitHub('o/r')
        with patch.object(client,'api',side_effect=[[{'name':str(i)} for i in range(100)],[{'name':'last'}]]) as api:
            self.assertEqual(len(client.assets(1)),101);self.assertIn('page=2',api.call_args.args[0])
    @patch.object(pub.time,'monotonic',side_effect=[100,101,101])
    @patch.object(pub.time,'sleep')
    @patch.object(pub.subprocess,'run')
    def test_writes_are_paced(self,run,sleep,clock):
        run.return_value=self.response(200,{'id':1})
        client=pub.GitHub('o/r')
        client.api('repos/o/r/releases','POST',{})
        client.api('repos/o/r/releases/1','PATCH',{})
        sleep.assert_called_once_with(7)
