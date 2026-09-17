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
        with self.assertRaises(RuntimeError):pub.GitHub('o/r').api('https://uploads.github.com/test','POST',file=Path(__file__))
        self.assertEqual(run.call_count,1)
    def test_resume_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.apk';a.write_bytes(b'one')
            b=Path(tmp)/'b.apk';b.write_bytes(b'two')
            def asset(p):return dict(name=p.name,size=p.stat().st_size,digest=pub.digest(p),state='uploaded')
            client=pub.GitHub('o/r')
            release=dict(id=1,draft=True,upload_url='https://uploads.github.com/test{?name,label}')
            with patch.object(client,'transfer',return_value=asset(b)) as transfer, patch.object(client,'api',side_effect=[release,None]) as api,patch.object(client,'assets',side_effect=[{'a.apk':asset(a)},{'a.apk':asset(a),'b.apk':asset(b)}]):
                client.publish('tag',[a,b],'sha','title','notes')
                self.assertEqual(api.call_count,2)
                self.assertEqual(transfer.call_args.args[-1],b)
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

    @patch.object(pub.time, 'sleep')
    def test_upload_reconciles_server_failure(self, sleep):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'image.gz'; path.write_bytes(b'image')
            asset = dict(name=path.name, size=5, state='uploaded', digest=pub.digest(path))
            release = dict(id=1, upload_url='https://uploads.github.com/test{?name}')
            for existing, calls in [(None, 2), (asset, 1)]:
                client = pub.GitHub('o/r')
                with patch.object(client, 'transfer', side_effect=[pub.GitHubError(500, 'server'), asset]) as api, patch.object(client, 'assets', return_value={} if existing is None else {path.name: existing}):
                    client.upload('tag', release, path)
                    self.assertEqual(api.call_count, calls)
            client = pub.GitHub('o/r')
            with patch.object(client, 'transfer', side_effect=pub.GitHubError(500, 'server')) as api, patch.object(client, 'assets', return_value={path.name: dict(asset, digest='wrong')}):
                with self.assertRaises(RuntimeError): client.upload('tag', release, path)
                self.assertEqual(api.call_count, 1)

    @patch.object(pub.time, 'sleep')
    def test_failed_empty_upload_is_cleaned_before_retry(self, sleep):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'image.gz'; path.write_bytes(b'image')
            asset = dict(name=path.name, size=5, state='uploaded', digest=pub.digest(path))
            client = pub.GitHub('o/r')
            release = dict(id=1, draft=True, upload_url='https://uploads.github.com/test')
            with patch.object(client, 'transfer', side_effect=[pub.GitHubError(500, 'server'), asset]), patch.object(client, 'api', return_value=None) as api, patch.object(client, 'assets', return_value={path.name: dict(id=9, state='starter', size=5)}):
                client.upload('tag', release, path)
                self.assertEqual(api.call_args_list[0].args, ('repos/o/r/releases/assets/9', 'DELETE'))

    def test_resume_draft_missing_from_tag_endpoint(self):
        client = pub.GitHub('o/r')
        draft = dict(id=1, tag_name='tag', draft=True)
        with patch.object(client, 'api', side_effect=[None, [draft], None]) as api, patch.object(client, 'assets', return_value={}):
            client.publish('tag', [], 'main', 'title', 'notes')
            self.assertEqual(api.call_args_list[-1].args[1], 'PATCH')
